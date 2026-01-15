-- Verification script for Migration 017
-- Run this AFTER applying 017_performance_indexes.sql

\echo '================================================'
\echo 'Migration 017 Index Verification'
\echo '================================================'
\echo ''

-- 1. Verify all 4 indexes exist
\echo '1. Checking if indexes were created...'
\echo ''

SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname IN (
    'idx_food_entries_user_timestamp',
    'idx_xp_transactions_user_source',
    'idx_conversation_user_created',
    'idx_tracking_user_category_time'
)
ORDER BY tablename, indexname;

\echo ''
\echo '2. Index sizes (helps identify if indexes are being used):'
\echo ''

SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE indexrelname IN (
    'idx_food_entries_user_timestamp',
    'idx_xp_transactions_user_source',
    'idx_conversation_user_created',
    'idx_tracking_user_category_time'
)
ORDER BY tablename, indexrelname;

\echo ''
\echo '3. Query plan for food_entries (should use idx_food_entries_user_timestamp):'
\echo ''

-- Test food_entries index
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM food_entries
WHERE user_id = (SELECT user_id FROM food_entries LIMIT 1)
ORDER BY timestamp DESC
LIMIT 20;

\echo ''
\echo '4. Query plan for xp_transactions (should use idx_xp_transactions_user_source):'
\echo ''

-- Test xp_transactions index
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM xp_transactions
WHERE user_id = (SELECT user_id FROM xp_transactions LIMIT 1)
  AND source_type = 'manual'
LIMIT 20;

\echo ''
\echo '5. Query plan for conversation_history (should use idx_conversation_user_created):'
\echo ''

-- Test conversation_history index
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM conversation_history
WHERE user_id = (SELECT user_id FROM conversation_history LIMIT 1)
ORDER BY created_at DESC
LIMIT 20;

\echo ''
\echo '6. Query plan for tracking_entries (should use idx_tracking_user_category_time):'
\echo ''

-- Test tracking_entries index
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM tracking_entries
WHERE user_id = (SELECT user_id FROM tracking_entries LIMIT 1)
  AND category_id = (SELECT category_id FROM tracking_entries LIMIT 1)
ORDER BY timestamp DESC
LIMIT 20;

\echo ''
\echo '================================================'
\echo 'Verification Complete!'
\echo '================================================'
\echo ''
\echo 'Look for "Index Scan using idx_..." in the query plans above.'
\echo 'If you see "Seq Scan" instead, the index may not be optimal for your data.'
\echo ''
