-- Epic 009 - Phase 3: Food Formulas & Auto-Suggestion
-- Migration 022: Food Formulas and Usage Tracking

-- Enable necessary extensions (if not already enabled)
-- Note: pgvector should already be enabled from migration 021

-- ============================================================================
-- TABLES
-- ============================================================================

-- Food formulas table (persistent recipes/patterns)
CREATE TABLE IF NOT EXISTS food_formulas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,

    -- Formula identification
    name VARCHAR(200) NOT NULL,                 -- "Morning Protein Shake", "Usual Breakfast"
    keywords TEXT[] DEFAULT '{}',               -- ["protein shake", "shake", "morning shake"]
    description TEXT,                           -- User-provided or AI-generated description

    -- Formula content (same structure as food_entries)
    foods JSONB NOT NULL,                       -- [{name, quantity, calories, macros}]
    total_calories INTEGER NOT NULL,
    total_macros JSONB NOT NULL,               -- {protein, carbs, fat}

    -- Visual reference (link to image embedding from Phase 1)
    reference_photo_path VARCHAR(500),
    reference_embedding_id UUID REFERENCES food_image_references(id) ON DELETE SET NULL,

    -- Pattern metadata
    created_from_entry_id UUID REFERENCES food_entries(id) ON DELETE SET NULL,
    is_auto_detected BOOLEAN DEFAULT false,    -- true if detected by pattern learning
    confidence_score FLOAT,                    -- 0.0 to 1.0 for auto-detected formulas

    -- Usage tracking
    times_used INTEGER DEFAULT 1,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE(user_id, name),
    CHECK (confidence_score IS NULL OR (confidence_score >= 0.0 AND confidence_score <= 1.0)),
    CHECK (total_calories >= 0),
    CHECK (times_used >= 0)
);

-- Formula usage log (track when and how formulas are used)
CREATE TABLE IF NOT EXISTS formula_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    formula_id UUID NOT NULL REFERENCES food_formulas(id) ON DELETE CASCADE,
    food_entry_id UUID NOT NULL REFERENCES food_entries(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,

    -- How was it matched?
    match_method VARCHAR(50) NOT NULL,         -- "keyword", "visual", "combined", "manual"
    match_confidence FLOAT,                    -- 0.0 to 1.0

    -- Variations tracking
    is_exact_match BOOLEAN DEFAULT true,
    variations JSONB,                          -- Track any deviations from formula

    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CHECK (match_method IN ('keyword', 'visual', 'combined', 'manual')),
    CHECK (match_confidence IS NULL OR (match_confidence >= 0.0 AND match_confidence <= 1.0))
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Food formulas indexes
CREATE INDEX IF NOT EXISTS idx_food_formulas_user
    ON food_formulas(user_id, last_used_at DESC);

CREATE INDEX IF NOT EXISTS idx_food_formulas_keywords
    ON food_formulas USING GIN(keywords);

CREATE INDEX IF NOT EXISTS idx_food_formulas_auto_detected
    ON food_formulas(user_id, is_auto_detected)
    WHERE is_auto_detected = true;

CREATE INDEX IF NOT EXISTS idx_food_formulas_times_used
    ON food_formulas(user_id, times_used DESC);

-- Formula usage log indexes
CREATE INDEX IF NOT EXISTS idx_formula_usage_log_formula
    ON formula_usage_log(formula_id, used_at DESC);

CREATE INDEX IF NOT EXISTS idx_formula_usage_log_user
    ON formula_usage_log(user_id, used_at DESC);

CREATE INDEX IF NOT EXISTS idx_formula_usage_log_food_entry
    ON formula_usage_log(food_entry_id);

CREATE INDEX IF NOT EXISTS idx_formula_usage_log_match_method
    ON formula_usage_log(user_id, match_method);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Update timestamp trigger for food_formulas
CREATE TRIGGER update_food_formulas_updated_at
    BEFORE UPDATE ON food_formulas
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function: Search formulas by keyword
CREATE OR REPLACE FUNCTION search_formulas_by_keyword(
    p_user_id TEXT,
    p_keyword TEXT,
    p_limit INTEGER DEFAULT 5
)
RETURNS TABLE (
    formula_id UUID,
    name VARCHAR(200),
    keywords TEXT[],
    foods JSONB,
    total_calories INTEGER,
    total_macros JSONB,
    times_used INTEGER,
    match_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ff.id,
        ff.name,
        ff.keywords,
        ff.foods,
        ff.total_calories,
        ff.total_macros,
        ff.times_used,
        -- Keyword matching score
        (
            CASE
                -- Exact match in keywords array (case-insensitive)
                WHEN LOWER(p_keyword) = ANY(SELECT LOWER(unnest(ff.keywords))) THEN 1.0
                -- Exact match in formula name
                WHEN LOWER(ff.name) = LOWER(p_keyword) THEN 1.0
                -- Partial match in formula name
                WHEN LOWER(ff.name) LIKE '%' || LOWER(p_keyword) || '%' THEN 0.8
                -- Partial match in keywords
                WHEN EXISTS (
                    SELECT 1 FROM unnest(ff.keywords) k
                    WHERE LOWER(k) LIKE '%' || LOWER(p_keyword) || '%'
                ) THEN 0.6
                -- Fallback for any other match
                ELSE 0.3
            END
        )::FLOAT as match_score
    FROM food_formulas ff
    WHERE ff.user_id = p_user_id
    AND (
        -- Match in keywords array
        LOWER(p_keyword) = ANY(SELECT LOWER(unnest(ff.keywords)))
        -- Match in name
        OR LOWER(ff.name) LIKE '%' || LOWER(p_keyword) || '%'
        -- Match in any keyword (partial)
        OR EXISTS (
            SELECT 1 FROM unnest(ff.keywords) k
            WHERE LOWER(k) LIKE '%' || LOWER(p_keyword) || '%'
        )
    )
    ORDER BY match_score DESC, ff.times_used DESC, ff.last_used_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function: Get formula usage statistics
CREATE OR REPLACE FUNCTION get_formula_usage_stats(
    p_formula_id UUID
)
RETURNS TABLE (
    total_uses BIGINT,
    keyword_matches BIGINT,
    visual_matches BIGINT,
    combined_matches BIGINT,
    manual_uses BIGINT,
    avg_match_confidence FLOAT,
    last_used TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT as total_uses,
        COUNT(*) FILTER (WHERE match_method = 'keyword')::BIGINT as keyword_matches,
        COUNT(*) FILTER (WHERE match_method = 'visual')::BIGINT as visual_matches,
        COUNT(*) FILTER (WHERE match_method = 'combined')::BIGINT as combined_matches,
        COUNT(*) FILTER (WHERE match_method = 'manual')::BIGINT as manual_uses,
        AVG(match_confidence)::FLOAT as avg_match_confidence,
        MAX(used_at) as last_used
    FROM formula_usage_log
    WHERE formula_id = p_formula_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Update formula usage counters
CREATE OR REPLACE FUNCTION update_formula_usage_counters()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the formula's usage statistics
    UPDATE food_formulas
    SET
        times_used = times_used + 1,
        last_used_at = NEW.used_at
    WHERE id = NEW.formula_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update formula usage counters
CREATE TRIGGER trigger_update_formula_usage_counters
    AFTER INSERT ON formula_usage_log
    FOR EACH ROW
    EXECUTE FUNCTION update_formula_usage_counters();

-- ============================================================================
-- COMMENTS (Documentation)
-- ============================================================================

COMMENT ON TABLE food_formulas IS
'Stores user-defined and auto-detected food formulas (recurring meals). Part of Epic 009 - Phase 3.';

COMMENT ON COLUMN food_formulas.keywords IS
'Array of search keywords for matching user input (e.g., ["protein shake", "shake"])';

COMMENT ON COLUMN food_formulas.is_auto_detected IS
'True if formula was automatically detected from pattern learning, false if user-created';

COMMENT ON COLUMN food_formulas.confidence_score IS
'Confidence score (0.0-1.0) for auto-detected formulas based on occurrence frequency and consistency';

COMMENT ON TABLE formula_usage_log IS
'Tracks every time a formula is used, including match method and confidence. Used for analytics and pattern refinement.';

COMMENT ON COLUMN formula_usage_log.match_method IS
'How the formula was matched: keyword (text), visual (image), combined (both), or manual (user-selected)';

COMMENT ON COLUMN formula_usage_log.variations IS
'JSONB field tracking any deviations from the original formula (e.g., different portion sizes)';

COMMENT ON FUNCTION search_formulas_by_keyword IS
'Search formulas by keyword with fuzzy matching and confidence scoring. Returns top matches sorted by relevance.';

COMMENT ON FUNCTION get_formula_usage_stats IS
'Get detailed usage statistics for a formula including match methods and average confidence.';
