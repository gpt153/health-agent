-- Rollback script for Migration 017: Performance Indexes
-- WARNING: Only run this if you need to remove the indexes

-- Remove food entries index
DROP INDEX IF EXISTS idx_food_entries_user_timestamp;

-- Remove gamification index
DROP INDEX IF EXISTS idx_xp_transactions_user_source;

-- Remove conversation history index
DROP INDEX IF EXISTS idx_conversation_user_created;

-- Remove tracking entries index
DROP INDEX IF EXISTS idx_tracking_user_category_time;

-- Verify rollback
DO $$
BEGIN
    RAISE NOTICE 'Migration 017 rollback completed';
    RAISE NOTICE 'Removed 4 composite indexes';
    RAISE NOTICE 'WARNING: Query performance may be degraded';
END $$;
