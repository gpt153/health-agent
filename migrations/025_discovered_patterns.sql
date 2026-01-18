-- ================================================================
-- Epic 009 - Phase 6: Pattern Detection Engine
-- Migration 025: discovered_patterns table
-- ================================================================
-- Purpose: Store automatically discovered health patterns with
--          statistical significance, confidence scoring, and evidence tracking
-- ================================================================

-- ================================================================
-- Table: discovered_patterns
-- Purpose: Store discovered health patterns from unified event timeline
-- ================================================================
CREATE TABLE IF NOT EXISTS discovered_patterns (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    pattern_type VARCHAR(50) NOT NULL,
    pattern_rule JSONB NOT NULL,
    confidence DECIMAL(3,2) NOT NULL CHECK (confidence >= 0.00 AND confidence <= 1.00),
    occurrences INTEGER DEFAULT 0 CHECK (occurrences >= 0),
    impact_score DECIMAL(4,2) CHECK (impact_score >= 0.00 AND impact_score <= 100.00),
    evidence JSONB,
    actionable_insight TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- Constraint: Validate pattern_type
    CONSTRAINT valid_pattern_type CHECK (
        pattern_type IN (
            'temporal_correlation',
            'multifactor_pattern',
            'behavioral_sequence',
            'cyclical_pattern',
            'semantic_cluster'
        )
    )
);

-- ================================================================
-- Performance Indexes
-- ================================================================

-- Primary user query index (get all patterns for user, sorted by confidence)
-- Enables: "Show me my top patterns"
-- Expected usage: Primary pattern retrieval query
CREATE INDEX idx_patterns_user_confidence
ON discovered_patterns(user_id, confidence DESC);

-- Impact-based sorting index
-- Enables: "Show me patterns with highest impact"
-- Expected usage: Prioritizing actionable patterns
CREATE INDEX idx_patterns_user_impact
ON discovered_patterns(user_id, impact_score DESC);

-- JSONB pattern rule queries (GIN index)
-- Enables: "Find all patterns involving pasta" or "Find all meal-related patterns"
-- Expected usage: Pattern exploration and deduplication
CREATE INDEX idx_patterns_rule
ON discovered_patterns USING GIN (pattern_rule);

-- Pattern deduplication index (prevent duplicate patterns)
-- Enables: Fast duplicate checking when creating new patterns
-- Expected usage: Pattern creation pipeline
CREATE UNIQUE INDEX idx_patterns_unique_rule
ON discovered_patterns(user_id, pattern_type, md5(pattern_rule::text));

-- Pattern type filtering index
-- Enables: "Get all temporal_correlation patterns for user"
-- Expected usage: Pattern type analysis
CREATE INDEX idx_patterns_user_type
ON discovered_patterns(user_id, pattern_type);

-- Evidence-based queries (GIN index for JSONB evidence)
-- Enables: "Find patterns with strong evidence" or evidence-based filtering
-- Expected usage: Pattern quality analysis
CREATE INDEX idx_patterns_evidence
ON discovered_patterns USING GIN (evidence);

-- ================================================================
-- Table Comments (Documentation)
-- ================================================================
COMMENT ON TABLE discovered_patterns IS 'Automatically discovered health patterns with statistical significance. Patterns are mined nightly from unified health_events timeline.';
COMMENT ON COLUMN discovered_patterns.pattern_type IS 'Type of pattern: temporal_correlation, multifactor_pattern, behavioral_sequence, cyclical_pattern, semantic_cluster';
COMMENT ON COLUMN discovered_patterns.pattern_rule IS 'JSONB pattern definition including trigger, outcome, conditions, and statistical metadata (p-value, correlation strength)';
COMMENT ON COLUMN discovered_patterns.confidence IS 'Pattern confidence score (0.00-1.00). Patterns below 0.50 are archived. Updated via Bayesian inference.';
COMMENT ON COLUMN discovered_patterns.occurrences IS 'Number of times pattern has been observed in historical data';
COMMENT ON COLUMN discovered_patterns.impact_score IS 'Pattern impact score (0.00-100.00) based on severity, frequency, confidence, and actionability';
COMMENT ON COLUMN discovered_patterns.evidence IS 'JSONB evidence tracking: positive/negative/neutral occurrences with timestamps and context';
COMMENT ON COLUMN discovered_patterns.actionable_insight IS 'Human-readable insight generated from pattern (e.g., "Avoid pasta for lunch on high-energy days")';

-- ================================================================
-- Example Pattern Rules (for reference)
-- ================================================================

-- Example 1: Temporal Correlation Pattern
-- {
--   "type": "temporal_correlation",
--   "trigger": {
--     "event_type": "meal",
--     "metadata.meal_type": "lunch",
--     "metadata.foods_contain": "pasta"
--   },
--   "outcome": {
--     "event_type": "symptom",
--     "metadata.symptom": "tiredness",
--     "metadata.severity": ">=6"
--   },
--   "time_window": {
--     "min_hours": 2,
--     "max_hours": 4
--   },
--   "statistics": {
--     "correlation_strength": 0.78,
--     "p_value": 0.003,
--     "sample_size": 18
--   }
-- }

-- Example 2: Multi-Factor Pattern
-- {
--   "type": "multifactor_pattern",
--   "factors": [
--     {"event_type": "sleep", "metadata.sleep_quality_rating": "<6"},
--     {"event_type": "meal", "metadata.foods_contain": "pasta"},
--     {"event_type": "stress", "metadata.stress_level": ">=7"}
--   ],
--   "outcome": {
--     "event_type": "symptom",
--     "metadata.symptom": "energy_crash"
--   },
--   "statistics": {
--     "chi_square": 12.45,
--     "p_value": 0.002,
--     "effect_size": 0.62
--   }
-- }

-- Example 3: Behavioral Sequence Pattern
-- {
--   "type": "behavioral_sequence",
--   "sequence": [
--     {"event_type": "exercise", "metadata.duration": ">=30"},
--     {"event_type": "sleep", "metadata.sleep_quality_rating": ">=8"},
--     {"event_type": "mood", "metadata.mood": "energized"}
--   ],
--   "time_window": {
--     "max_hours_between_events": 16
--   },
--   "statistics": {
--     "sequence_support": 0.72,
--     "p_value": 0.015
--   }
-- }

-- Example 4: Cyclical Pattern
-- {
--   "type": "cyclical_pattern",
--   "cycle": "weekly",
--   "pattern": {
--     "day_of_week": "Tuesday",
--     "time_range": "14:00-16:00",
--     "event": {
--       "event_type": "symptom",
--       "metadata.symptom": "sugar_craving"
--     }
--   },
--   "statistics": {
--     "recurrence_rate": 0.85,
--     "p_value": 0.008
--   }
-- }

-- Example 5: Semantic Cluster
-- {
--   "type": "semantic_cluster",
--   "cluster_centroid": "high_carb_foods_cause_tiredness",
--   "members": [
--     "pasta → tiredness",
--     "rice → tiredness",
--     "bread → tiredness"
--   ],
--   "statistics": {
--     "cluster_coherence": 0.82,
--     "avg_p_value": 0.012
--   }
-- }

-- ================================================================
-- Example Evidence JSONB Structure
-- ================================================================

-- {
--   "positive_count": 18,
--   "negative_count": 3,
--   "neutral_count": 1,
--   "last_positive": "2026-01-15T14:30:00Z",
--   "last_negative": "2026-01-10T13:00:00Z",
--   "confidence_history": [
--     {"timestamp": "2026-01-01T03:00:00Z", "confidence": 0.65},
--     {"timestamp": "2026-01-08T03:00:00Z", "confidence": 0.72},
--     {"timestamp": "2026-01-15T03:00:00Z", "confidence": 0.78}
--   ],
--   "recent_evidence": [
--     {
--       "timestamp": "2026-01-15T14:30:00Z",
--       "type": "positive",
--       "context": "Pasta lunch at 12:00 → Tiredness at 14:30 (matched pattern)"
--     },
--     {
--       "timestamp": "2026-01-16T14:00:00Z",
--       "type": "negative",
--       "context": "Pasta lunch at 12:00 → No tiredness observed"
--     }
--   ]
-- }
