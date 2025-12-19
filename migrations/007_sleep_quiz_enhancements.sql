-- Migration 007: Sleep Quiz Enhancements
-- Adds multi-language support, auto-scheduling, and pattern learning

-- User-specific sleep quiz settings
CREATE TABLE IF NOT EXISTS sleep_quiz_settings (
    user_id VARCHAR(255) PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
    enabled BOOLEAN DEFAULT true,
    preferred_time TIME DEFAULT '07:00:00',
    timezone VARCHAR(100) DEFAULT 'UTC',
    language_code VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Track quiz submission patterns for learning
CREATE TABLE IF NOT EXISTS sleep_quiz_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    scheduled_time TIMESTAMP NOT NULL,
    submitted_at TIMESTAMP NOT NULL,
    response_delay_minutes INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_sleep_quiz_settings_enabled ON sleep_quiz_settings(user_id, enabled);
CREATE INDEX IF NOT EXISTS idx_sleep_quiz_submissions_user_time ON sleep_quiz_submissions(user_id, submitted_at DESC);

-- Update trigger for settings
CREATE TRIGGER update_sleep_quiz_settings_updated_at
BEFORE UPDATE ON sleep_quiz_settings
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
