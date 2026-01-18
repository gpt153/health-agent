-- Recognized Plates & Calibration (Epic 009 - Phase 2)
-- Plate/container recognition and size calibration for portion estimation

-- ================================================================
-- Table: recognized_plates
-- Purpose: Store recognized plates/containers with CLIP embeddings for matching
-- ================================================================
CREATE TABLE IF NOT EXISTS recognized_plates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,

    -- Plate identification
    plate_name VARCHAR(200),  -- Auto-generated or user-provided (e.g., "Large white dinner plate")
    embedding vector(512) NOT NULL,  -- CLIP embedding of plate for visual matching

    -- Physical characteristics
    estimated_diameter_cm FLOAT,  -- Estimated diameter in centimeters (for plates/bowls)
    estimated_capacity_ml FLOAT,   -- Estimated capacity in milliliters (for bowls/cups)
    plate_type VARCHAR(50),         -- "plate", "bowl", "cup", "container"
    color VARCHAR(100),              -- Dominant color (e.g., "white", "blue", "ceramic pattern")
    shape VARCHAR(50),               -- "round", "square", "oval", "rectangular"

    -- Usage tracking
    times_recognized INTEGER DEFAULT 1,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Calibration status
    is_calibrated BOOLEAN DEFAULT FALSE,
    calibration_confidence FLOAT,  -- 0.0 to 1.0 (null if not calibrated)
    calibration_method VARCHAR(50), -- "reference_portion", "user_input", "auto_inferred"

    -- Metadata
    model_version VARCHAR(100) DEFAULT 'clip-vit-base-patch32',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
);

-- ================================================================
-- HNSW Index for Fast Plate Matching
-- Using same parameters as food_image_references for consistency
-- ================================================================
CREATE INDEX IF NOT EXISTS idx_recognized_plates_embedding_hnsw
ON recognized_plates
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Standard B-tree indexes
CREATE INDEX IF NOT EXISTS idx_recognized_plates_user
ON recognized_plates(user_id);

CREATE INDEX IF NOT EXISTS idx_recognized_plates_type
ON recognized_plates(plate_type);

CREATE INDEX IF NOT EXISTS idx_recognized_plates_calibrated
ON recognized_plates(is_calibrated);

-- Composite index for common queries (user's most-used plates)
CREATE INDEX IF NOT EXISTS idx_recognized_plates_user_times
ON recognized_plates(user_id, times_recognized DESC);

CREATE INDEX IF NOT EXISTS idx_recognized_plates_user_calibrated
ON recognized_plates(user_id, is_calibrated);

-- ================================================================
-- Table: food_entry_plates
-- Purpose: Link food entries to recognized plates (many-to-many)
-- ================================================================
CREATE TABLE IF NOT EXISTS food_entry_plates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    food_entry_id UUID NOT NULL REFERENCES food_entries(id) ON DELETE CASCADE,
    recognized_plate_id UUID NOT NULL REFERENCES recognized_plates(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,

    -- Detection metadata
    confidence_score FLOAT NOT NULL,  -- Similarity score (0.0 to 1.0)
    detection_method VARCHAR(50) DEFAULT 'auto_detected',  -- "auto_detected", "user_confirmed", "manual_link"

    -- Spatial information (optional, for future enhancements)
    plate_region JSONB,  -- Bounding box or segmentation mask: {"x", "y", "width", "height"}

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_food_entry_plate UNIQUE(food_entry_id, recognized_plate_id),
    CONSTRAINT fk_food_entry FOREIGN KEY (food_entry_id) REFERENCES food_entries(id) ON DELETE CASCADE,
    CONSTRAINT fk_recognized_plate FOREIGN KEY (recognized_plate_id) REFERENCES recognized_plates(id) ON DELETE CASCADE,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
);

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_food_entry_plates_entry
ON food_entry_plates(food_entry_id);

CREATE INDEX IF NOT EXISTS idx_food_entry_plates_plate
ON food_entry_plates(recognized_plate_id);

CREATE INDEX IF NOT EXISTS idx_food_entry_plates_user
ON food_entry_plates(user_id);

CREATE INDEX IF NOT EXISTS idx_food_entry_plates_confidence
ON food_entry_plates(confidence_score DESC);

-- ================================================================
-- Function: find_similar_plates
-- Purpose: Find visually similar plates using cosine similarity
-- ================================================================
CREATE OR REPLACE FUNCTION find_similar_plates(
    p_user_id TEXT,
    p_embedding vector(512),
    p_limit INTEGER DEFAULT 5,
    p_distance_threshold FLOAT DEFAULT 0.15  -- More strict than food matching (0.85 similarity)
) RETURNS TABLE (
    plate_id UUID,
    plate_name VARCHAR(200),
    plate_type VARCHAR(50),
    similarity_score FLOAT,
    times_recognized INTEGER,
    is_calibrated BOOLEAN,
    estimated_diameter_cm FLOAT,
    estimated_capacity_ml FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        rp.id AS plate_id,
        rp.plate_name,
        rp.plate_type,
        1 - (rp.embedding <=> p_embedding) AS similarity_score,
        rp.times_recognized,
        rp.is_calibrated,
        rp.estimated_diameter_cm,
        rp.estimated_capacity_ml
    FROM recognized_plates rp
    WHERE rp.user_id = p_user_id
      AND (1 - (rp.embedding <=> p_embedding)) >= (1 - p_distance_threshold)
    ORDER BY rp.embedding <=> p_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- Function: update_plate_usage
-- Purpose: Update plate usage statistics when recognized
-- ================================================================
CREATE OR REPLACE FUNCTION update_plate_usage(
    p_plate_id UUID
) RETURNS VOID AS $$
BEGIN
    UPDATE recognized_plates
    SET times_recognized = times_recognized + 1,
        last_seen_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_plate_id;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- Function: get_plate_calibration_data
-- Purpose: Get historical portion data for a plate to assist calibration
-- ================================================================
CREATE OR REPLACE FUNCTION get_plate_calibration_data(
    p_user_id TEXT,
    p_plate_id UUID,
    p_limit INTEGER DEFAULT 20
) RETURNS TABLE (
    food_entry_id UUID,
    timestamp TIMESTAMP,
    foods JSONB,
    total_calories INTEGER,
    confidence_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        fe.id AS food_entry_id,
        fe.timestamp,
        fe.foods,
        fe.total_calories,
        fep.confidence_score
    FROM food_entries fe
    INNER JOIN food_entry_plates fep ON fe.id = fep.food_entry_id
    WHERE fep.recognized_plate_id = p_plate_id
      AND fep.user_id = p_user_id
    ORDER BY fe.timestamp DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- Function: get_user_plate_statistics
-- Purpose: Get summary statistics for a user's recognized plates
-- ================================================================
CREATE OR REPLACE FUNCTION get_user_plate_statistics(
    p_user_id TEXT
) RETURNS TABLE (
    total_plates INTEGER,
    calibrated_plates INTEGER,
    total_recognitions INTEGER,
    most_used_plate_id UUID,
    most_used_plate_name VARCHAR(200),
    most_used_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::INTEGER AS total_plates,
        COUNT(*) FILTER (WHERE is_calibrated = TRUE)::INTEGER AS calibrated_plates,
        COALESCE(SUM(times_recognized), 0)::INTEGER AS total_recognitions,
        (SELECT id FROM recognized_plates WHERE user_id = p_user_id ORDER BY times_recognized DESC LIMIT 1) AS most_used_plate_id,
        (SELECT plate_name FROM recognized_plates WHERE user_id = p_user_id ORDER BY times_recognized DESC LIMIT 1) AS most_used_plate_name,
        (SELECT times_recognized FROM recognized_plates WHERE user_id = p_user_id ORDER BY times_recognized DESC LIMIT 1)::INTEGER AS most_used_count
    FROM recognized_plates
    WHERE user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- Trigger: update_recognized_plates_updated_at
-- Purpose: Auto-update updated_at timestamp on row changes
-- ================================================================
CREATE OR REPLACE FUNCTION update_recognized_plates_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_recognized_plates_timestamp
BEFORE UPDATE ON recognized_plates
FOR EACH ROW
EXECUTE FUNCTION update_recognized_plates_timestamp();

-- ================================================================
-- Comments for documentation
-- ================================================================
COMMENT ON TABLE recognized_plates IS
'Stores recognized plates/containers with CLIP embeddings for visual matching and portion size calibration';

COMMENT ON COLUMN recognized_plates.embedding IS
'512-dimensional CLIP embedding from clip-vit-base-patch32 model for plate matching';

COMMENT ON COLUMN recognized_plates.estimated_diameter_cm IS
'Estimated diameter in centimeters (for plates and round bowls)';

COMMENT ON COLUMN recognized_plates.estimated_capacity_ml IS
'Estimated total capacity in milliliters (for bowls, cups, containers)';

COMMENT ON COLUMN recognized_plates.is_calibrated IS
'Whether the plate has been calibrated with accurate size measurements';

COMMENT ON COLUMN recognized_plates.calibration_method IS
'How the plate was calibrated: reference_portion (from known food weights), user_input (manual entry), or auto_inferred (from patterns)';

COMMENT ON INDEX idx_recognized_plates_embedding_hnsw IS
'HNSW index for fast approximate nearest neighbor search using cosine distance';

COMMENT ON TABLE food_entry_plates IS
'Links food entries to recognized plates for portion estimation and pattern tracking';

COMMENT ON FUNCTION find_similar_plates IS
'Finds visually similar plates for a user using cosine similarity.
Returns matches with similarity score >= (1 - distance_threshold).
Default threshold 0.15 means 85% similarity required (stricter than food matching).';

COMMENT ON FUNCTION update_plate_usage IS
'Updates plate usage statistics (times_recognized, last_seen_at) when a plate is detected in a new food entry.';

COMMENT ON FUNCTION get_plate_calibration_data IS
'Returns historical food entries linked to a specific plate to assist with calibration analysis.
Useful for inferring plate size from portion patterns.';

COMMENT ON FUNCTION get_user_plate_statistics IS
'Returns summary statistics for all of a user''s recognized plates including total count, calibration status, and most frequently used plate.';
