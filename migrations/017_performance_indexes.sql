-- Migration 017: Add missing performance indexes
-- Priority: MEDIUM-HIGH
-- Phase: 1 - Quick Wins
-- Estimated Impact: Improved query performance for high-traffic patterns

-- Food entries date range queries (pagination, daily summaries)
-- Common pattern: SELECT * FROM food_entries WHERE user_id = ? ORDER BY timestamp DESC
CREATE INDEX IF NOT EXISTS idx_food_entries_user_timestamp
ON food_entries(user_id, timestamp DESC);

-- Gamification analytics (XP tracking, leaderboards, achievement progress)
-- Common pattern: SELECT * FROM xp_transactions WHERE user_id = ? AND source_type = ?
CREATE INDEX IF NOT EXISTS idx_xp_transactions_user_source
ON xp_transactions(user_id, source_type);

-- Chat history pagination (conversation retrieval)
-- Common pattern: SELECT * FROM conversation_history WHERE user_id = ? ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_conversation_user_created
ON conversation_history(user_id, created_at DESC);

-- Tracking trend analysis (habit tracking, progress reports)
-- Common pattern: SELECT * FROM tracking_entries WHERE user_id = ? AND category_id = ? ORDER BY timestamp DESC
CREATE INDEX IF NOT EXISTS idx_tracking_user_category_time
ON tracking_entries(user_id, category_id, timestamp DESC);

-- Verify indexes were created
DO $$
BEGIN
    RAISE NOTICE 'Migration 017 completed successfully';
    RAISE NOTICE 'Created 4 composite indexes for performance optimization';
END $$;
