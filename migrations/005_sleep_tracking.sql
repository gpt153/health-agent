-- Sleep tracking table
CREATE TABLE IF NOT EXISTS sleep_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bedtime TIME NOT NULL,
    sleep_latency_minutes INTEGER NOT NULL,
    wake_time TIME NOT NULL,
    total_sleep_hours FLOAT NOT NULL,
    night_wakings INTEGER NOT NULL,
    sleep_quality_rating INTEGER NOT NULL CHECK (sleep_quality_rating >= 1 AND sleep_quality_rating <= 10),
    disruptions JSONB DEFAULT '[]'::jsonb,
    phone_usage BOOLEAN NOT NULL,
    phone_duration_minutes INTEGER,
    alertness_rating INTEGER NOT NULL CHECK (alertness_rating >= 1 AND alertness_rating <= 10)
);

-- Index for efficient user queries sorted by date
CREATE INDEX IF NOT EXISTS idx_sleep_entries_user_logged ON sleep_entries(user_id, logged_at DESC);

-- Index for JSONB disruptions field (GIN index for JSON queries)
CREATE INDEX IF NOT EXISTS idx_sleep_entries_disruptions ON sleep_entries USING GIN(disruptions);
