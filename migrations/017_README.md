# Migration 017: Performance Indexes

**Priority:** MEDIUM-HIGH
**Phase:** 1 - Quick Wins
**Estimated Time:** 30 minutes
**Impact:** Improved query performance for high-traffic patterns

## Overview

This migration adds 4 critical composite indexes that were identified as missing during the codebase performance review. These indexes optimize common query patterns for:

1. Food tracking (date range queries)
2. Gamification analytics (XP tracking)
3. Chat history pagination
4. Habit tracking (trend analysis)

## Missing Indexes Added

### 1. `idx_food_entries_user_timestamp`
- **Table:** `food_entries`
- **Columns:** `user_id, timestamp DESC`
- **Use Case:** Pagination and daily summaries
- **Query Pattern:**
  ```sql
  SELECT * FROM food_entries
  WHERE user_id = ?
  ORDER BY timestamp DESC
  LIMIT 20
  ```

### 2. `idx_xp_transactions_user_source`
- **Table:** `xp_transactions`
- **Columns:** `user_id, source_type`
- **Use Case:** Gamification analytics, leaderboards
- **Query Pattern:**
  ```sql
  SELECT * FROM xp_transactions
  WHERE user_id = ?
  AND source_type = ?
  ```

### 3. `idx_conversation_user_created`
- **Table:** `conversation_history`
- **Columns:** `user_id, created_at DESC`
- **Use Case:** Chat history retrieval
- **Query Pattern:**
  ```sql
  SELECT * FROM conversation_history
  WHERE user_id = ?
  ORDER BY created_at DESC
  LIMIT 50
  ```

### 4. `idx_tracking_user_category_time`
- **Table:** `tracking_entries`
- **Columns:** `user_id, category_id, timestamp DESC`
- **Use Case:** Progress tracking, trend analysis
- **Query Pattern:**
  ```sql
  SELECT * FROM tracking_entries
  WHERE user_id = ?
  AND category_id = ?
  ORDER BY timestamp DESC
  ```

## How to Apply

### Method 1: Direct psql (Development)
```bash
# From the migrations directory
cd migrations
psql -d health_agent -f 017_performance_indexes.sql
```

### Method 2: Production Migration Script
```bash
# From the migrations directory
cd migrations
./run_prod_migrations.sh
```

This will run ALL pending migrations including 017.

### Method 3: Manual Connection (Production)
```bash
# Connect to production database (adjust port as needed)
PGPASSWORD=postgres psql -h localhost -p 5436 -U postgres -d health_agent -f migrations/017_performance_indexes.sql
```

## Verification

After applying the migration, verify the indexes were created:

```bash
# Run the verification script
psql -d health_agent -f migrations/verify_017_indexes.sql
```

### What to Look For

1. **All 4 indexes exist:**
   - idx_food_entries_user_timestamp
   - idx_xp_transactions_user_source
   - idx_conversation_user_created
   - idx_tracking_user_category_time

2. **Query plans use indexes:**
   - Look for "Index Scan using idx_..."
   - Should NOT see "Seq Scan" for these queries

3. **Index sizes are reasonable:**
   - Indexes should be smaller than the table itself
   - Typical size: a few KB to a few MB depending on data

## Expected Performance Improvement

- **Food queries:** 10-100x faster for date range pagination
- **Gamification queries:** 5-50x faster for analytics
- **Chat history:** 10-100x faster for pagination
- **Tracking queries:** 10-100x faster for trend analysis

Actual improvement depends on:
- Current data volume
- Query frequency
- PostgreSQL configuration
- Hardware resources

## Rollback

If you need to rollback this migration:

```sql
-- Remove all 4 indexes
DROP INDEX IF EXISTS idx_food_entries_user_timestamp;
DROP INDEX IF EXISTS idx_xp_transactions_user_source;
DROP INDEX IF EXISTS idx_conversation_user_created;
DROP INDEX IF EXISTS idx_tracking_user_category_time;
```

Or use the rollback script (if created):
```bash
psql -d health_agent -f migrations/rollbacks/017_rollback.sql
```

## Safety

This migration is **SAFE** to run on production:

✅ Uses `CREATE INDEX IF NOT EXISTS` (idempotent)
✅ No data changes
✅ No schema changes to existing columns
✅ Indexes are created asynchronously (non-blocking in PostgreSQL 11+)
✅ Can be rolled back without data loss

## Dependencies

None. This migration can be run independently.

## Related

- Issue #59: Phase 1.3 - Add missing database indexes
- CODEBASE_REVIEW.md - Issue #5 (Performance Analysis)
- Phase 1 - Quick Wins initiative
