-- ========================================
-- Migration 011: Timezone Awareness
-- Convert all TIMESTAMP columns to TIMESTAMPTZ
-- ========================================

-- Food entries
ALTER TABLE food_entries
    ALTER COLUMN timestamp TYPE TIMESTAMPTZ USING timestamp AT TIME ZONE 'UTC';

-- Reminders
ALTER TABLE reminders
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';

-- Tracking entries
ALTER TABLE tracking_entries
    ALTER COLUMN timestamp TYPE TIMESTAMPTZ USING timestamp AT TIME ZONE 'UTC';

-- Tracking categories
ALTER TABLE tracking_categories
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';

-- Users
ALTER TABLE users
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
    ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC';

-- Conversation history (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'conversation_history') THEN
        ALTER TABLE conversation_history
            ALTER COLUMN timestamp TYPE TIMESTAMPTZ USING timestamp AT TIME ZONE 'UTC';
    END IF;
END $$;

-- Food entry audit (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'food_entry_audit') THEN
        ALTER TABLE food_entry_audit
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';
    END IF;
END $$;

-- Sleep entries (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sleep_entries') THEN
        ALTER TABLE sleep_entries
            ALTER COLUMN logged_at TYPE TIMESTAMPTZ USING logged_at AT TIME ZONE 'UTC';
    END IF;
END $$;

-- Sleep quiz settings (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sleep_quiz_settings') THEN
        ALTER TABLE sleep_quiz_settings
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC';
    END IF;
END $$;

-- Sleep quiz submissions (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sleep_quiz_submissions') THEN
        ALTER TABLE sleep_quiz_submissions
            ALTER COLUMN scheduled_time TYPE TIMESTAMPTZ USING scheduled_time AT TIME ZONE 'UTC',
            ALTER COLUMN submitted_at TYPE TIMESTAMPTZ USING submitted_at AT TIME ZONE 'UTC';
    END IF;
END $$;

-- Reminder completions (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'reminder_completions') THEN
        ALTER TABLE reminder_completions
            ALTER COLUMN scheduled_time TYPE TIMESTAMPTZ USING scheduled_time AT TIME ZONE 'UTC',
            ALTER COLUMN completed_at TYPE TIMESTAMPTZ USING completed_at AT TIME ZONE 'UTC';
    END IF;
END $$;

-- Reminder skips (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'reminder_skips') THEN
        ALTER TABLE reminder_skips
            ALTER COLUMN scheduled_time TYPE TIMESTAMPTZ USING scheduled_time AT TIME ZONE 'UTC',
            ALTER COLUMN skipped_at TYPE TIMESTAMPTZ USING skipped_at AT TIME ZONE 'UTC';
    END IF;
END $$;

-- User achievements (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_achievements') THEN
        ALTER TABLE user_achievements
            ALTER COLUMN unlocked_at TYPE TIMESTAMPTZ USING unlocked_at AT TIME ZONE 'UTC';
    END IF;
END $$;

-- Achievements (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'achievements') THEN
        ALTER TABLE achievements
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';
    END IF;
END $$;

-- XP transactions (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'xp_transactions') THEN
        ALTER TABLE xp_transactions
            ALTER COLUMN awarded_at TYPE TIMESTAMPTZ USING awarded_at AT TIME ZONE 'UTC';
    END IF;
END $$;

-- User XP (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_xp') THEN
        ALTER TABLE user_xp
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC';
    END IF;
END $$;

-- User streaks (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_streaks') THEN
        ALTER TABLE user_streaks
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC';
    END IF;
END $$;

-- Dynamic tools (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'dynamic_tools') THEN
        ALTER TABLE dynamic_tools
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC',
            ALTER COLUMN last_used_at TYPE TIMESTAMPTZ USING last_used_at AT TIME ZONE 'UTC';
    END IF;
END $$;

-- Invite codes (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'invite_codes') THEN
        ALTER TABLE invite_codes
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN expires_at TYPE TIMESTAMPTZ USING expires_at AT TIME ZONE 'UTC';
    END IF;
END $$;

-- Onboarding state (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_onboarding_state') THEN
        ALTER TABLE user_onboarding_state
            ALTER COLUMN started_at TYPE TIMESTAMPTZ USING started_at AT TIME ZONE 'UTC',
            ALTER COLUMN completed_at TYPE TIMESTAMPTZ USING completed_at AT TIME ZONE 'UTC',
            ALTER COLUMN last_interaction_at TYPE TIMESTAMPTZ USING last_interaction_at AT TIME ZONE 'UTC';
    END IF;
END $$;

-- Feature discovery log (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'feature_discovery_log') THEN
        ALTER TABLE feature_discovery_log
            ALTER COLUMN discovered_at TYPE TIMESTAMPTZ USING discovered_at AT TIME ZONE 'UTC',
            ALTER COLUMN first_used_at TYPE TIMESTAMPTZ USING first_used_at AT TIME ZONE 'UTC',
            ALTER COLUMN last_used_at TYPE TIMESTAMPTZ USING last_used_at AT TIME ZONE 'UTC';
    END IF;
END $$;

-- Add comment explaining timezone policy
COMMENT ON DATABASE health_agent IS
'All TIMESTAMPTZ columns store UTC internally.
Convert to user timezone only at display/input boundaries.
User timezone stored in user_profiles.timezone (IANA format).';

-- Verification query
DO $$
DECLARE
    non_tz_columns TEXT;
BEGIN
    SELECT string_agg(table_name || '.' || column_name, ', ')
    INTO non_tz_columns
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND data_type = 'timestamp without time zone'
      AND column_name LIKE '%time%' OR column_name LIKE '%date%' OR column_name = 'timestamp'
    LIMIT 10;

    IF non_tz_columns IS NOT NULL THEN
        RAISE WARNING 'Found non-timezone-aware timestamp columns: %', non_tz_columns;
    ELSE
        RAISE NOTICE 'All timestamp columns are now timezone-aware (TIMESTAMPTZ)';
    END IF;
END $$;
