-- Migration 014: Fix Default Timezone to Europe/Stockholm
-- Changes all UTC defaults to Europe/Stockholm for Swedish users

-- 1. Update table defaults
ALTER TABLE user_profiles
    ALTER COLUMN timezone SET DEFAULT 'Europe/Stockholm';

ALTER TABLE sleep_quiz_settings
    ALTER COLUMN timezone SET DEFAULT 'Europe/Stockholm';

-- 2. Update the initialize_user_profile function to use Stockholm
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
        'Europe/Stockholm'  -- Changed from UTC
    )
    ON CONFLICT (telegram_id) DO NOTHING;
END;
$$ LANGUAGE plpgsql;

-- 3. Update existing UTC timezones to Stockholm (for all users)
UPDATE user_profiles
SET timezone = 'Europe/Stockholm',
    updated_at = CURRENT_TIMESTAMP
WHERE timezone = 'UTC';

UPDATE sleep_quiz_settings
SET timezone = 'Europe/Stockholm',
    updated_at = CURRENT_TIMESTAMP
WHERE timezone = 'UTC';

-- Verification
SELECT 'user_profiles updated:' as message, COUNT(*) as count
FROM user_profiles WHERE timezone = 'Europe/Stockholm'
UNION ALL
SELECT 'sleep_quiz_settings updated:' as message, COUNT(*) as count
FROM sleep_quiz_settings WHERE timezone = 'Europe/Stockholm';

COMMENT ON COLUMN user_profiles.timezone IS 'IANA timezone (default: Europe/Stockholm for Swedish users)';
COMMENT ON COLUMN sleep_quiz_settings.timezone IS 'IANA timezone (default: Europe/Stockholm for Swedish users)';
