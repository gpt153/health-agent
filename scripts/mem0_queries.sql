-- Mem0 Semantic Memory Database Queries
-- These queries help you explore what's stored in the Mem0 system

-- 1. View all memories for a specific user (most recent first)
SELECT
    payload->>'user_id' as user_id,
    payload->>'data' as memory,
    payload->>'source' as source,
    payload->>'created_at' as created_at
FROM mem0
WHERE payload->>'user_id' = '7376426503'  -- Replace with your user ID
ORDER BY (payload->>'created_at')::timestamp DESC
LIMIT 20;

-- 2. Count memories per user
SELECT
    payload->>'user_id' as user_id,
    COUNT(*) as memory_count
FROM mem0
GROUP BY payload->>'user_id'
ORDER BY memory_count DESC;

-- 3. Search for memories containing specific keywords (case-insensitive)
SELECT
    payload->>'user_id' as user_id,
    payload->>'data' as memory,
    payload->>'created_at' as created_at
FROM mem0
WHERE payload->>'data' ILIKE '%training%'  -- Replace with your search term
ORDER BY (payload->>'created_at')::timestamp DESC
LIMIT 20;

-- 4. View memories by source
SELECT
    payload->>'source' as source,
    COUNT(*) as count
FROM mem0
GROUP BY payload->>'source'
ORDER BY count DESC;

-- 5. View all memories from a specific date
SELECT
    payload->>'user_id' as user_id,
    payload->>'data' as memory,
    payload->>'created_at' as created_at
FROM mem0
WHERE (payload->>'created_at')::timestamp::date = '2025-12-17'  -- Replace with your date
ORDER BY (payload->>'created_at')::timestamp DESC;

-- 6. Get memory statistics
SELECT
    COUNT(*) as total_memories,
    COUNT(DISTINCT payload->>'user_id') as unique_users,
    MIN((payload->>'created_at')::timestamp) as oldest_memory,
    MAX((payload->>'created_at')::timestamp) as newest_memory
FROM mem0;

-- 7. View memories with metadata
SELECT
    payload->>'user_id' as user_id,
    payload->>'data' as memory,
    payload->>'metadata' as metadata,
    payload->>'created_at' as created_at
FROM mem0
WHERE payload->>'metadata' IS NOT NULL
ORDER BY (payload->>'created_at')::timestamp DESC
LIMIT 10;

-- 8. Search across multiple keywords (OR condition)
SELECT
    payload->>'user_id' as user_id,
    payload->>'data' as memory,
    payload->>'created_at' as created_at
FROM mem0
WHERE payload->>'data' ILIKE '%training%'
   OR payload->>'data' ILIKE '%workout%'
   OR payload->>'data' ILIKE '%gym%'
ORDER BY (payload->>'created_at')::timestamp DESC
LIMIT 20;

-- 9. Get recent memories (last 24 hours)
SELECT
    payload->>'user_id' as user_id,
    payload->>'data' as memory,
    payload->>'created_at' as created_at
FROM mem0
WHERE (payload->>'created_at')::timestamp > NOW() - INTERVAL '24 hours'
ORDER BY (payload->>'created_at')::timestamp DESC;

-- 10. View full payload structure (useful for debugging)
SELECT
    id,
    payload
FROM mem0
LIMIT 5;
