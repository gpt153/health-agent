-- User onboarding state tracking
CREATE TABLE IF NOT EXISTS user_onboarding_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) UNIQUE NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    onboarding_path VARCHAR(20),             -- 'quick', 'full', 'chat', NULL (not started)
    current_step VARCHAR(50) NOT NULL DEFAULT 'welcome',
    step_data JSONB DEFAULT '{}',            -- Stores partial inputs during flow
    completed_steps TEXT[] DEFAULT '{}',     -- Array of completed step names
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    last_interaction_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Feature discovery and usage tracking
CREATE TABLE IF NOT EXISTS feature_discovery_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    feature_name VARCHAR(100) NOT NULL,
    discovery_method VARCHAR(50),            -- 'onboarding', 'contextual', 'help_command'
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    first_used_at TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_onboarding_user_step
    ON user_onboarding_state(user_id, current_step)
    WHERE completed_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_onboarding_last_interaction
    ON user_onboarding_state(last_interaction_at DESC)
    WHERE completed_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_feature_discovery_user_feature
    ON feature_discovery_log(user_id, feature_name);

CREATE INDEX IF NOT EXISTS idx_feature_discovery_unused
    ON feature_discovery_log(user_id)
    WHERE first_used_at IS NULL;

-- Comments for documentation
COMMENT ON TABLE user_onboarding_state IS 'Tracks user progress through onboarding paths';
COMMENT ON TABLE feature_discovery_log IS 'Tracks when users discover and use features';
COMMENT ON COLUMN user_onboarding_state.step_data IS 'Stores partial inputs (name, goals, etc) during multi-step flows';
COMMENT ON COLUMN feature_discovery_log.discovery_method IS 'How the user learned about this feature';
