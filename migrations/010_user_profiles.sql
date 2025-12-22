-- ========================================
-- Migration 010: User Profiles Table
-- Consolidate user data from markdown files into PostgreSQL
-- ========================================

-- Create user_profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
    telegram_id VARCHAR(255) PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
    profile_data JSONB NOT NULL DEFAULT '{}',
    timezone VARCHAR(100) NOT NULL DEFAULT 'UTC',  -- IANA timezone
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- Ensure timezone is valid
    CONSTRAINT valid_timezone CHECK (timezone ~ '^[A-Za-z_]+/[A-Za-z_]+$|^UTC$')
);

-- Index for fast JSON queries
CREATE INDEX IF NOT EXISTS idx_user_profiles_data ON user_profiles USING GIN(profile_data);

-- Index for timezone queries
CREATE INDEX IF NOT EXISTS idx_user_profiles_timezone ON user_profiles(timezone);

-- Update trigger
CREATE TRIGGER update_user_profiles_updated_at
BEFORE UPDATE ON user_profiles
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Default profile structure comment
COMMENT ON COLUMN user_profiles.profile_data IS
'JSON structure: {
    "name": string,
    "age": number,
    "height_cm": number,
    "current_weight_kg": number,
    "target_weight_kg": number,
    "goal_type": "lose_weight|gain_muscle|maintain|improve_sleep",
    "allergies": [string],
    "dietary_preferences": [string],
    "health_conditions": [string],
    "medications": [string],
    "preferred_language": "en|sv",
    "coaching_style": "supportive|analytical|tough_love",
    "communication_preferences": {
        "brevity": "brief|medium|detailed",
        "tone": "friendly|formal|casual",
        "use_humor": boolean,
        "proactive_checkins": boolean,
        "daily_summary": boolean
    }
}';

-- Create indexes for commonly accessed data in JSONB
CREATE INDEX IF NOT EXISTS idx_profile_allergies
ON user_profiles USING GIN ((profile_data->'allergies'));

CREATE INDEX IF NOT EXISTS idx_profile_dietary_preferences
ON user_profiles USING GIN ((profile_data->'dietary_preferences'));

-- Helper function to initialize default profile
CREATE OR REPLACE FUNCTION initialize_user_profile(p_telegram_id VARCHAR)
RETURNS VOID AS $$
BEGIN
    INSERT INTO user_profiles (telegram_id, profile_data, timezone)
    VALUES (
        p_telegram_id,
        '{
            "communication_preferences": {
                "brevity": "medium",
                "tone": "friendly",
                "use_humor": true,
                "proactive_checkins": false,
                "daily_summary": false
            }
        }'::jsonb,
        'UTC'
    )
    ON CONFLICT (telegram_id) DO NOTHING;
END;
$$ LANGUAGE plpgsql;

-- Automatically create profile when user is created
CREATE OR REPLACE FUNCTION auto_create_user_profile()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM initialize_user_profile(NEW.telegram_id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_create_profile
AFTER INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION auto_create_user_profile();

-- Create profiles for existing users
INSERT INTO user_profiles (telegram_id, profile_data, timezone)
SELECT
    telegram_id,
    '{}'::jsonb,
    'UTC'
FROM users
ON CONFLICT (telegram_id) DO NOTHING;

COMMENT ON TABLE user_profiles IS 'Centralized user profile data, replacing markdown files';
