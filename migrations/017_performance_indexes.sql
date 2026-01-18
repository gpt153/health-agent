-- Migration 017: Performance Indexes
-- Phase 3 of Performance Optimization (Issue #82)
--
-- Adds optimized indexes for high-traffic queries:
-- 1. Covering index for conversation history retrieval
-- 2. Food entries date range index
-- 3. Reminders scheduling index
-- 4. Active users lookup index
--
-- Expected improvements:
-- - Conversation history: 50-80% faster
-- - Food queries: 40-60% faster
-- - Reminder scheduling: 30-50% faster

-- ==========================================
-- 1. Conversation History Covering Index
-- ==========================================
-- Current query (from queries.py):
--   SELECT role, content, message_type, metadata, timestamp
--   FROM conversation_history
--   WHERE user_id = %s
--   ORDER BY timestamp DESC
--   LIMIT 20
--
-- This covering index includes ALL columns needed by the query,
-- avoiding expensive heap lookups (index-only scan).

CREATE INDEX IF NOT EXISTS idx_conversation_history_user_timestamp_covering
ON conversation_history(user_id, timestamp DESC)
INCLUDE (role, content, message_type, metadata);

COMMENT ON INDEX idx_conversation_history_user_timestamp_covering IS
'Covering index for conversation history retrieval. Includes all columns needed by the query to enable index-only scans.';


-- ==========================================
-- 2. Food Entries Date Range Index
-- ==========================================
-- Common query patterns:
-- - Get food entries for a specific date
-- - Get food entries for last 7/30 days
-- - Calculate daily totals
--
-- Partial index: Only indexes recent entries (last 30 days)
-- to keep index size smaller and updates faster.

CREATE INDEX IF NOT EXISTS idx_food_entries_user_date_range
ON food_entries(user_id, timestamp DESC)
WHERE timestamp > (CURRENT_TIMESTAMP - INTERVAL '30 days');

COMMENT ON INDEX idx_food_entries_user_date_range IS
'Partial index for recent food entries (last 30 days). Optimizes date-range queries and daily totals.';


-- ==========================================
-- 3. Reminders Scheduling Index
-- ==========================================
-- Query pattern (reminder scheduling):
--   SELECT * FROM reminders
--   WHERE user_id = %s
--     AND active = true
--     AND next_execution_time <= NOW()
--   ORDER BY next_execution_time

CREATE INDEX IF NOT EXISTS idx_reminders_next_execution
ON reminders(user_id, next_execution_time)
WHERE active = true;

COMMENT ON INDEX idx_reminders_next_execution IS
'Partial index for active reminders. Optimizes reminder scheduling queries.';


-- ==========================================
-- 4. Active Users Lookup Index
-- ==========================================
-- Query pattern:
--   SELECT * FROM users WHERE telegram_id = %s
--
-- Add partial index for active subscription users only
-- (most queries are for active users).

CREATE INDEX IF NOT EXISTS idx_users_telegram_id_active
ON users(telegram_id)
WHERE subscription_status = 'active';

COMMENT ON INDEX idx_users_telegram_id_active IS
'Partial index for active subscription users. Optimizes user lookup queries.';


-- ==========================================
-- 5. Gamification XP Queries
-- ==========================================
-- Query pattern (leaderboard, user XP):
--   SELECT user_id, total_xp, current_level
--   FROM user_gamification
--   ORDER BY total_xp DESC
--   LIMIT 10

CREATE INDEX IF NOT EXISTS idx_user_gamification_xp_desc
ON user_gamification(total_xp DESC)
INCLUDE (current_level, current_streak);

COMMENT ON INDEX idx_user_gamification_xp_desc IS
'Covering index for XP leaderboard queries. Enables fast ORDER BY total_xp DESC.';


-- ==========================================
-- 6. Food Entries by Type (for analytics)
-- ==========================================
-- Query pattern (analytics):
--   SELECT food_name, SUM(calories), AVG(protein)
--   FROM food_entries
--   WHERE user_id = %s
--   GROUP BY food_name

CREATE INDEX IF NOT EXISTS idx_food_entries_user_name
ON food_entries(user_id, food_name);

COMMENT ON INDEX idx_food_entries_user_name IS
'Compound index for food analytics queries. Optimizes GROUP BY food_name.';


-- ==========================================
-- Index Statistics & Verification
-- ==========================================
-- Query to check index usage after deployment:
--
-- SELECT
--     schemaname,
--     tablename,
--     indexname,
--     idx_scan,
--     idx_tup_read,
--     idx_tup_fetch
-- FROM pg_stat_user_indexes
-- WHERE schemaname = 'public'
--   AND indexname LIKE 'idx_%'
-- ORDER BY idx_scan DESC;
--
-- Query to check index size:
--
-- SELECT
--     tablename,
--     indexname,
--     pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
-- FROM pg_stat_user_indexes
-- WHERE schemaname = 'public'
--   AND indexname LIKE 'idx_%'
-- ORDER BY pg_relation_size(indexrelid) DESC;


-- ==========================================
-- Rollback Instructions
-- ==========================================
-- To rollback this migration:
-- See rollbacks/017_performance_indexes_rollback.sql
--
-- DROP INDEX IF EXISTS idx_conversation_history_user_timestamp_covering;
-- DROP INDEX IF EXISTS idx_food_entries_user_date_range;
-- DROP INDEX IF EXISTS idx_reminders_next_execution;
-- DROP INDEX IF EXISTS idx_users_telegram_id_active;
-- DROP INDEX IF EXISTS idx_user_gamification_xp_desc;
-- DROP INDEX IF EXISTS idx_food_entries_user_name;
