-- ============================================
-- Migration 012: Memory Architecture Cleanup
-- Adds constraints and validation for data integrity
-- ============================================

-- Add CHECK constraints for data quality
ALTER TABLE food_entries
ADD CONSTRAINT IF NOT EXISTS food_entries_calories_range CHECK (total_calories >= 0 AND total_calories <= 10000);

ALTER TABLE user_xp
ADD CONSTRAINT IF NOT EXISTS user_xp_positive CHECK (total_xp >= 0 AND current_level >= 1);

ALTER TABLE user_streaks
ADD CONSTRAINT IF NOT EXISTS user_streaks_positive CHECK (current_streak >= 0 AND best_streak >= 0);

-- Add NOT NULL constraints for critical fields (only if they don't exist)
DO $$
BEGIN
    -- Check and add NOT NULL for food_entries.user_id
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'food_entries'
        AND column_name = 'user_id'
        AND is_nullable = 'YES'
    ) THEN
        ALTER TABLE food_entries ALTER COLUMN user_id SET NOT NULL;
    END IF;

    -- Check and add NOT NULL for food_entries.timestamp
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'food_entries'
        AND column_name = 'timestamp'
        AND is_nullable = 'YES'
    ) THEN
        ALTER TABLE food_entries ALTER COLUMN timestamp SET NOT NULL;
    END IF;

    -- Check and add NOT NULL for user_xp.user_id
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_xp'
        AND column_name = 'user_id'
        AND is_nullable = 'YES'
    ) THEN
        ALTER TABLE user_xp ALTER COLUMN user_id SET NOT NULL;
    END IF;

    -- Check and add NOT NULL for user_xp.total_xp
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_xp'
        AND column_name = 'total_xp'
        AND is_nullable = 'YES'
    ) THEN
        ALTER TABLE user_xp ALTER COLUMN total_xp SET NOT NULL;
    END IF;
END $$;

-- Create audit table for profile updates (similar to food_entry_audit)
CREATE TABLE IF NOT EXISTS profile_update_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    updated_by VARCHAR(50) DEFAULT 'user', -- 'user' or 'auto'
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_profile_audit_user ON profile_update_audit(user_id, updated_at DESC);

-- Create audit table for preference updates
CREATE TABLE IF NOT EXISTS preference_update_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    preference_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    updated_by VARCHAR(50) DEFAULT 'user',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_preference_audit_user ON preference_update_audit(user_id, updated_at DESC);

-- Comments
COMMENT ON TABLE profile_update_audit IS 'Audit trail for user profile changes';
COMMENT ON TABLE preference_update_audit IS 'Audit trail for user preference changes';
COMMENT ON CONSTRAINT food_entries_calories_range ON food_entries IS 'Ensure calories are within reasonable range (0-10000)';
COMMENT ON CONSTRAINT user_xp_positive ON user_xp IS 'Ensure XP and level are never negative';
COMMENT ON CONSTRAINT user_streaks_positive ON user_streaks IS 'Ensure streak counts are never negative';
