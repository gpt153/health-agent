-- Migration: Add notification preferences for pattern discoveries
-- Epic 009 - Phase 7: Integration & Agent Tools
-- Enables users to control when and how they receive pattern notifications

-- Add notification_preferences column to user_profiles
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS notification_preferences JSONB DEFAULT '{
    "pattern_notifications": true,
    "pattern_min_impact": 60,
    "notification_frequency": "daily",
    "quiet_hours": {
        "enabled": false,
        "start": "22:00",
        "end": "08:00"
    },
    "max_daily_notifications": 3,
    "last_notification_sent": null
}'::jsonb;

-- Create index for notification queries
CREATE INDEX IF NOT EXISTS idx_user_profiles_notification_prefs
ON user_profiles USING GIN (notification_preferences);

-- Function to check if user should receive pattern notification
CREATE OR REPLACE FUNCTION should_send_pattern_notification(
    p_user_id TEXT,
    p_pattern_impact NUMERIC
) RETURNS BOOLEAN AS $$
DECLARE
    v_prefs JSONB;
    v_notifications_enabled BOOLEAN;
    v_min_impact NUMERIC;
    v_last_notification TIMESTAMP;
    v_frequency TEXT;
    v_max_daily INTEGER;
    v_notifications_today INTEGER;
    v_quiet_hours JSONB;
    v_current_time TIME;
    v_quiet_start TIME;
    v_quiet_end TIME;
BEGIN
    -- Get user preferences
    SELECT notification_preferences
    INTO v_prefs
    FROM user_profiles
    WHERE telegram_id = p_user_id;

    IF v_prefs IS NULL THEN
        -- Default to enabled
        RETURN TRUE;
    END IF;

    -- Check if notifications are enabled
    v_notifications_enabled := COALESCE((v_prefs->>'pattern_notifications')::boolean, true);
    IF NOT v_notifications_enabled THEN
        RETURN FALSE;
    END IF;

    -- Check minimum impact threshold
    v_min_impact := COALESCE((v_prefs->>'pattern_min_impact')::numeric, 60);
    IF p_pattern_impact < v_min_impact THEN
        RETURN FALSE;
    END IF;

    -- Check frequency limit
    v_frequency := COALESCE(v_prefs->>'notification_frequency', 'daily');
    v_last_notification := (v_prefs->>'last_notification_sent')::timestamp;

    IF v_last_notification IS NOT NULL THEN
        CASE v_frequency
            WHEN 'hourly' THEN
                IF v_last_notification > NOW() - INTERVAL '1 hour' THEN
                    RETURN FALSE;
                END IF;
            WHEN 'daily' THEN
                IF v_last_notification::date = CURRENT_DATE THEN
                    -- Check daily limit
                    v_max_daily := COALESCE((v_prefs->>'max_daily_notifications')::int, 3);
                    v_notifications_today := COALESCE(
                        (v_prefs->>'notifications_sent_today')::int, 0
                    );
                    IF v_notifications_today >= v_max_daily THEN
                        RETURN FALSE;
                    END IF;
                END IF;
            WHEN 'weekly' THEN
                IF v_last_notification > NOW() - INTERVAL '7 days' THEN
                    RETURN FALSE;
                END IF;
        END CASE;
    END IF;

    -- Check quiet hours
    v_quiet_hours := v_prefs->'quiet_hours';
    IF COALESCE((v_quiet_hours->>'enabled')::boolean, false) THEN
        v_current_time := CURRENT_TIME;
        v_quiet_start := (v_quiet_hours->>'start')::time;
        v_quiet_end := (v_quiet_hours->>'end')::time;

        -- Handle quiet hours that span midnight
        IF v_quiet_start > v_quiet_end THEN
            IF v_current_time >= v_quiet_start OR v_current_time < v_quiet_end THEN
                RETURN FALSE;
            END IF;
        ELSE
            IF v_current_time >= v_quiet_start AND v_current_time < v_quiet_end THEN
                RETURN FALSE;
            END IF;
        END IF;
    END IF;

    -- All checks passed
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Function to record that notification was sent
CREATE OR REPLACE FUNCTION record_pattern_notification_sent(
    p_user_id TEXT,
    p_pattern_id INTEGER
) RETURNS VOID AS $$
DECLARE
    v_prefs JSONB;
    v_notifications_today INTEGER;
    v_last_sent DATE;
BEGIN
    -- Get current preferences
    SELECT notification_preferences
    INTO v_prefs
    FROM user_profiles
    WHERE telegram_id = p_user_id;

    IF v_prefs IS NULL THEN
        v_prefs := '{}'::jsonb;
    END IF;

    -- Update last notification timestamp
    v_prefs := jsonb_set(v_prefs, '{last_notification_sent}', to_jsonb(NOW()::text));

    -- Update daily counter
    v_last_sent := (v_prefs->>'last_notification_sent')::date;
    IF v_last_sent = CURRENT_DATE THEN
        v_notifications_today := COALESCE((v_prefs->>'notifications_sent_today')::int, 0) + 1;
    ELSE
        v_notifications_today := 1;
    END IF;
    v_prefs := jsonb_set(v_prefs, '{notifications_sent_today}', to_jsonb(v_notifications_today));

    -- Add to notification history
    IF v_prefs->'notification_history' IS NULL THEN
        v_prefs := jsonb_set(v_prefs, '{notification_history}', '[]'::jsonb);
    END IF;

    v_prefs := jsonb_set(
        v_prefs,
        '{notification_history}',
        (v_prefs->'notification_history') || jsonb_build_object(
            'timestamp', NOW(),
            'pattern_id', p_pattern_id
        )
    );

    -- Keep only last 30 notifications in history
    IF jsonb_array_length(v_prefs->'notification_history') > 30 THEN
        v_prefs := jsonb_set(
            v_prefs,
            '{notification_history}',
            (v_prefs->'notification_history') - 0  -- Remove oldest
        );
    END IF;

    -- Update preferences
    UPDATE user_profiles
    SET notification_preferences = v_prefs
    WHERE telegram_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get notification summary for user
CREATE OR REPLACE FUNCTION get_notification_summary(p_user_id TEXT)
RETURNS TABLE (
    notifications_enabled BOOLEAN,
    min_impact INTEGER,
    frequency TEXT,
    notifications_sent_today INTEGER,
    max_daily INTEGER,
    last_notification TIMESTAMP,
    quiet_hours_enabled BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE((notification_preferences->>'pattern_notifications')::boolean, true),
        COALESCE((notification_preferences->>'pattern_min_impact')::int, 60),
        COALESCE(notification_preferences->>'notification_frequency', 'daily')::TEXT,
        COALESCE((notification_preferences->>'notifications_sent_today')::int, 0),
        COALESCE((notification_preferences->>'max_daily_notifications')::int, 3),
        (notification_preferences->>'last_notification_sent')::timestamp,
        COALESCE((notification_preferences->'quiet_hours'->>'enabled')::boolean, false)
    FROM user_profiles
    WHERE telegram_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Function to reset daily notification counter (called by daily cron job)
CREATE OR REPLACE FUNCTION reset_daily_notification_counters() RETURNS INTEGER AS $$
DECLARE
    v_updated_count INTEGER;
BEGIN
    UPDATE user_profiles
    SET notification_preferences = jsonb_set(
        notification_preferences,
        '{notifications_sent_today}',
        '0'::jsonb
    )
    WHERE (notification_preferences->>'last_notification_sent')::date < CURRENT_DATE;

    GET DIAGNOSTICS v_updated_count = ROW_COUNT;

    RAISE NOTICE 'Reset daily notification counters for % users', v_updated_count;

    RETURN v_updated_count;
END;
$$ LANGUAGE plpgsql;

-- Add comments
COMMENT ON COLUMN user_profiles.notification_preferences IS 'JSONB storing pattern notification preferences';
COMMENT ON FUNCTION should_send_pattern_notification IS 'Checks if user should receive a pattern notification based on preferences';
COMMENT ON FUNCTION record_pattern_notification_sent IS 'Records that a pattern notification was sent to user';
COMMENT ON FUNCTION get_notification_summary IS 'Returns notification settings summary for a user';
COMMENT ON FUNCTION reset_daily_notification_counters IS 'Resets daily notification counters (run daily via cron)';
