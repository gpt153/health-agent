# Epic 009 - Phase 1 Deployment Checklist

## Pre-Deployment Verification

### 1. Database Prerequisites
- [ ] PostgreSQL server running
- [ ] Database accessible from application
- [ ] `pgvector` extension available

```bash
# Verify pgvector is available
psql -d your_database -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 2. Environment Configuration
- [ ] `OPENAI_API_KEY` set in `.env` file
- [ ] `DATABASE_URL` configured correctly
- [ ] All existing environment variables present

```bash
# Verify environment
grep -E "OPENAI_API_KEY|DATABASE_URL" .env
```

### 3. Dependencies
- [ ] All Python packages installed

```bash
# Install/update dependencies
pip install -r requirements.txt

# Or with uv
uv pip install -r requirements.txt
```

## Deployment Steps

### Step 1: Apply Database Migration

```bash
# Run migration script
./run_migrations.sh

# Or manually
psql -d your_database -f migrations/021_food_image_references.sql
```

**Expected Output:**
```
CREATE EXTENSION
CREATE TABLE (food_image_references)
CREATE TABLE (image_analysis_cache)
CREATE INDEX (idx_food_image_embeddings_hnsw)
CREATE FUNCTION (find_similar_food_images)
CREATE FUNCTION (update_cache_hit)
```

### Step 2: Verify Migration

```bash
# Check pgvector extension
psql -d your_database -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# Check tables exist
psql -d your_database -c "\dt food_image_references image_analysis_cache"

# Check HNSW index exists
psql -d your_database -c "SELECT indexname FROM pg_indexes WHERE tablename = 'food_image_references' AND indexname = 'idx_food_image_embeddings_hnsw';"

# Check functions exist
psql -d your_database -c "\df find_similar_food_images update_cache_hit"
```

**Expected:**
- ✅ pgvector extension installed
- ✅ Both tables exist
- ✅ HNSW index created
- ✅ Both functions defined

### Step 3: Run Tests

```bash
# Unit tests (fast, no API required)
pytest tests/unit/test_image_embedding.py -v

# Integration tests (requires database)
pytest tests/integration/test_visual_food_search.py -v

# All new tests
pytest tests/unit/test_image_embedding.py tests/integration/test_visual_food_search.py -v
```

**Expected:**
- ✅ All unit tests pass (25 tests)
- ✅ All integration tests pass (15 tests)

### Step 4: Verify Code Compilation

```bash
# Check Python syntax
python3 -m py_compile src/services/image_embedding.py
python3 -m py_compile src/services/visual_food_search.py
python3 -m py_compile src/bot.py

# Check for placeholders
grep -r "TODO\|FIXME\|PLACEHOLDER" src/services/
# Should return empty
```

### Step 5: Test Embedding Service (Optional)

```bash
# Quick smoke test (requires OpenAI API key)
python3 << 'EOF'
import asyncio
from src.services.image_embedding import get_embedding_service

async def test():
    service = get_embedding_service()
    print("✅ Embedding service initialized")

asyncio.run(test())
EOF
```

### Step 6: Restart Application

```bash
# Stop current bot
./stop_bot.sh

# Start with new code
./start_bot.sh

# Monitor logs for startup
tail -f bot.log | grep -E "VISUAL_SEARCH|ImageEmbedding"
```

**Look for:**
- No errors during service initialization
- Successful database connection
- First photo upload triggers embedding generation

## Post-Deployment Verification

### 1. Monitor First Photo Upload

Send a test food photo and check logs:

```bash
tail -f bot.log | grep -E "VISUAL_SEARCH|embedding"
```

**Expected log entries:**
```
[INFO] Saved food entry {uuid} for user {user_id}
[INFO] [VISUAL_SEARCH] Queued embedding generation for entry {uuid}
[INFO] Generating CLIP embedding for {photo_path}
[INFO] Generated embedding for {photo_path}: 512 dimensions
[INFO] Stored embedding for food entry {uuid}
```

### 2. Verify Database Storage

```sql
-- Check embeddings are being stored
SELECT COUNT(*) FROM food_image_references;

-- Should see entries for uploaded photos
SELECT user_id, food_entry_id, created_at
FROM food_image_references
ORDER BY created_at DESC
LIMIT 5;
```

### 3. Test Similarity Search

```sql
-- Generate a test query
SELECT * FROM find_similar_food_images(
    'your_user_id'::TEXT,
    (SELECT embedding FROM food_image_references LIMIT 1),
    5::INTEGER,
    0.3::FLOAT
);

-- Should return similar foods
```

## Performance Verification

### 1. Check Query Performance

```sql
-- Explain query plan
EXPLAIN (ANALYZE, BUFFERS)
SELECT food_entry_id, embedding <=> '[0.1,0.2,...]'::vector as distance
FROM food_image_references
WHERE user_id = 'test_user'
ORDER BY embedding <=> '[0.1,0.2,...]'::vector
LIMIT 5;
```

**Look for:**
- ✅ HNSW index is used
- ✅ Query time <100ms

### 2. Monitor Cache Hit Rate

```sql
-- Check cache statistics
SELECT
    photo_path,
    cache_hits,
    analysis_timestamp,
    last_accessed
FROM image_analysis_cache
ORDER BY cache_hits DESC
LIMIT 10;
```

## Rollback Plan

If deployment fails:

### Step 1: Stop Application
```bash
./stop_bot.sh
```

### Step 2: Rollback Migration
```bash
# Drop new tables
psql -d your_database << 'EOF'
DROP TABLE IF EXISTS food_image_references CASCADE;
DROP TABLE IF EXISTS image_analysis_cache CASCADE;
DROP FUNCTION IF EXISTS find_similar_food_images CASCADE;
DROP FUNCTION IF EXISTS update_cache_hit CASCADE;
DROP EXTENSION IF EXISTS vector CASCADE;
EOF
```

### Step 3: Restore Previous Code
```bash
git checkout main -- src/bot.py src/db/queries/food.py
rm -rf src/services/
```

### Step 4: Restart Application
```bash
./start_bot.sh
```

## Monitoring

### Key Metrics to Watch

1. **Embedding Generation Rate**
   - Monitor OpenAI API usage
   - Watch for rate limits or errors

2. **Database Performance**
   - Query response times
   - HNSW index usage
   - Cache hit rate

3. **Error Rates**
   - Embedding generation failures
   - Search query failures
   - Database connection issues

### Log Patterns to Monitor

```bash
# Success patterns
grep "VISUAL_SEARCH.*Queued embedding" bot.log
grep "Stored embedding for food entry" bot.log

# Error patterns
grep "ERROR.*VISUAL_SEARCH" bot.log
grep "Failed to.*embedding" bot.log

# Performance
grep -E "embedding.*\d+\.\d+s" bot.log
grep -E "search.*\d+ms" bot.log
```

## Troubleshooting

### Issue: pgvector Extension Not Found

**Error:** `ERROR: extension "vector" does not exist`

**Solution:**
```bash
# Install pgvector
sudo apt-get install postgresql-15-pgvector
# Or compile from source
```

### Issue: HNSW Index Not Used

**Error:** Slow queries, sequential scan in EXPLAIN plan

**Solution:**
```sql
-- Rebuild index
DROP INDEX idx_food_image_embeddings_hnsw;
CREATE INDEX idx_food_image_embeddings_hnsw
ON food_image_references
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Update statistics
ANALYZE food_image_references;
```

### Issue: Embedding Generation Fails

**Error:** `OpenAI API error: ...`

**Solution:**
1. Verify `OPENAI_API_KEY` is set
2. Check API quota/limits
3. Verify network connectivity
4. Check OpenAI API status

### Issue: High Latency

**Symptom:** Searches taking >100ms

**Solutions:**
```sql
-- Check index health
SELECT * FROM pg_stat_user_indexes
WHERE indexrelname = 'idx_food_image_embeddings_hnsw';

-- Rebuild statistics
ANALYZE food_image_references;

-- Consider increasing HNSW parameters for larger datasets
ALTER INDEX idx_food_image_embeddings_hnsw
SET (ef_search = 100);
```

## Success Criteria

Deployment is successful when:

- ✅ Migration applied without errors
- ✅ All tests pass
- ✅ First photo upload generates embedding
- ✅ Embeddings stored in database
- ✅ Similarity search returns results
- ✅ Query performance <100ms
- ✅ No errors in application logs
- ✅ Cache hit rate increases over time

---

**Ready for Production** ✅

Follow this checklist step-by-step for a smooth deployment.
