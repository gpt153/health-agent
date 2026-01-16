-- Migration 018: Enable Sleep Quiz for User 8191393299
-- Creates user record and enables sleep quiz reminder

-- Insert user into users table
INSERT INTO users (telegram_id, subscription_status, subscription_tier, subscription_start_date, activated_at)
VALUES (
    '8191393299',
    'active',
    'premium',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (telegram_id) DO UPDATE SET
    subscription_status = EXCLUDED.subscription_status,
    subscription_tier = EXCLUDED.subscription_tier,
    subscription_start_date = EXCLUDED.subscription_start_date,
    activated_at = EXCLUDED.activated_at;

-- Insert sleep quiz settings
INSERT INTO sleep_quiz_settings (user_id, enabled, preferred_time, timezone, language_code)
VALUES (
    '8191393299',
    true,
    '07:00:00',
    'Europe/Stockholm',
    'en'
)
ON CONFLICT (user_id) DO UPDATE SET
    enabled = EXCLUDED.enabled,
    preferred_time = EXCLUDED.preferred_time,
    timezone = EXCLUDED.timezone,
    language_code = EXCLUDED.language_code,
    updated_at = CURRENT_TIMESTAMP;

-- Verify the changes
SELECT
    u.telegram_id,
    u.subscription_status,
    u.subscription_tier,
    s.enabled AS sleep_quiz_enabled,
    s.preferred_time,
    s.timezone
FROM users u
LEFT JOIN sleep_quiz_settings s ON u.telegram_id = s.user_id
WHERE u.telegram_id = '8191393299';
