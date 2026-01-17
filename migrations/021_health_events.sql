-- Health Events Timeline Foundation
-- Epic 009 - Phase 5: Unified event timeline for pattern detection
-- This migration creates a unified health_events table that consolidates
-- all user health activities into a single temporal timeline

-- ================================================================
-- Table: health_events
-- Purpose: Unified timeline of all health-related events
-- ================================================================
CREATE TABLE IF NOT EXISTS health_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    metadata JSONB NOT NULL,
    source_table VARCHAR(50),     -- Origin table for backfill tracking
    source_id UUID,               -- FK to original record
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraint: Only allow valid event types
    CONSTRAINT valid_event_type CHECK (
        event_type IN (
            'meal',
            'sleep',
            'exercise',
            'symptom',
            'mood',
            'stress',
            'tracker',
            'custom'
        )
    )
);

-- ================================================================
-- Performance Indexes
-- Target: <50ms for 30-day temporal queries
-- ================================================================

-- Primary temporal query index (CRITICAL for performance)
-- Enables: "Get all events for user X in last 30 days"
-- Expected usage: Every pattern detection query
CREATE INDEX idx_health_events_user_time
ON health_events(user_id, timestamp DESC);

-- Event type filtering index
-- Enables: "Get all meals for user X in last 30 days"
-- Expected usage: Type-specific analysis (meal patterns, sleep trends)
CREATE INDEX idx_health_events_user_type_time
ON health_events(user_id, event_type, timestamp DESC);

-- JSONB metadata queries (GIN index with jsonb_path_ops)
-- Enables: "Find all meals with >500 calories"
-- Expected usage: Pattern detection queries on event metadata
CREATE INDEX idx_health_events_metadata
ON health_events USING GIN(metadata jsonb_path_ops);

-- Backfill verification index
-- Enables: Fast duplicate checking during historical migration
-- Expected usage: Migration script only (check if event already migrated)
CREATE INDEX idx_health_events_source
ON health_events(source_table, source_id)
WHERE source_id IS NOT NULL;

-- Pattern detection composite index (INCLUDE clause for covering index)
-- Enables: Ultra-fast pattern queries without table lookups
-- Expected usage: Phase 6 pattern detection engine
CREATE INDEX idx_health_events_pattern_query
ON health_events(user_id, event_type, timestamp DESC)
INCLUDE (metadata);

-- ================================================================
-- Table Comments (Documentation)
-- ================================================================
COMMENT ON TABLE health_events IS 'Unified timeline of all user health events. Enables cross-domain pattern detection (e.g., food-sleep correlations)';
COMMENT ON COLUMN health_events.event_type IS 'Type of health event: meal, sleep, exercise, symptom, mood, stress, tracker, custom';
COMMENT ON COLUMN health_events.timestamp IS 'When the event occurred (user timezone converted to UTC)';
COMMENT ON COLUMN health_events.metadata IS 'Event-specific data in JSONB. Schema varies by event_type (meals have calories, sleep has quality rating, etc.)';
COMMENT ON COLUMN health_events.source_table IS 'Original table name (food_entries, sleep_entries, etc.) for backfill tracking';
COMMENT ON COLUMN health_events.source_id IS 'Original record UUID. Used for idempotent migration (prevent duplicates)';

-- ================================================================
-- Example Metadata Schemas (for reference)
-- ================================================================

-- Meal event metadata:
-- {
--   "meal_type": "lunch",
--   "total_calories": 650,
--   "total_macros": {"protein": 35, "carbs": 75, "fat": 18},
--   "foods": [...],
--   "photo_path": "/path/to/photo.jpg"
-- }

-- Sleep event metadata:
-- {
--   "bedtime": "23:00",
--   "wake_time": "07:30",
--   "total_sleep_hours": 7.5,
--   "sleep_quality_rating": 8,
--   "night_wakings": 1,
--   "disruptions": ["noise", "bathroom"],
--   "alertness_rating": 7
-- }

-- Tracker event metadata:
-- {
--   "category_name": "Blood Pressure",
--   "category_id": "uuid-here",
--   "data": {"systolic": 120, "diastolic": 80, "heart_rate": 72}
-- }
