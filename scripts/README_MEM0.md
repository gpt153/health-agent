# How to View Mem0 Semantic Memories

Mem0 stores semantic memories in a PostgreSQL database with vector embeddings. Here are all the ways to view and search your memories:

---

## Method 1: Python Script (Recommended)

### View All Memories
```bash
source .venv/bin/activate
python scripts/view_mem0.py 7376426503
```

### Search Memories (Semantic Search)
```bash
python scripts/view_mem0.py 7376426503 --search "training schedule"
python scripts/view_mem0.py 7376426503 --search "nutrition goals"
python scripts/view_mem0.py 7376426503 --search "medications"
```

**Features:**
- ✅ Lists all memories for a user
- ✅ Semantic search with relevance scoring
- ✅ Shows creation timestamps
- ✅ Easy to use

---

## Method 2: Direct SQL Queries

### Connect to Database
```bash
PGPASSWORD=postgres psql -h localhost -p 5434 -U postgres -d health_agent
```

### View Recent Memories
```sql
SELECT
    payload->>'user_id' as user_id,
    payload->>'data' as memory,
    payload->>'created_at' as created_at
FROM mem0
WHERE payload->>'user_id' = '7376426503'
ORDER BY (payload->>'created_at')::timestamp DESC
LIMIT 20;
```

### Search by Keyword
```sql
SELECT
    payload->>'data' as memory,
    payload->>'created_at' as created_at
FROM mem0
WHERE payload->>'user_id' = '7376426503'
  AND payload->>'data' ILIKE '%training%'
ORDER BY (payload->>'created_at')::timestamp DESC;
```

### Count Memories
```sql
SELECT
    payload->>'user_id' as user_id,
    COUNT(*) as memory_count
FROM mem0
GROUP BY payload->>'user_id';
```

### More queries available in:
```bash
cat scripts/mem0_queries.sql
```

---

## Method 3: One-liner SQL from Command Line

### View recent memories
```bash
PGPASSWORD=postgres psql -h localhost -p 5434 -U postgres -d health_agent \
  -c "SELECT payload->>'data' as memory, payload->>'created_at' as created_at FROM mem0 WHERE payload->>'user_id' = '7376426503' ORDER BY (payload->>'created_at')::timestamp DESC LIMIT 10;"
```

### Search for specific topic
```bash
PGPASSWORD=postgres psql -h localhost -p 5434 -U postgres -d health_agent \
  -c "SELECT payload->>'data' as memory FROM mem0 WHERE payload->>'user_id' = '7376426503' AND payload->>'data' ILIKE '%nutrition%';"
```

---

## Method 4: View in Bot Logs

The bot logs show Mem0 activity in real-time:

```bash
# View bot logs
tail -f bot.log

# Or background task logs
tail -f /tmp/claude/tasks/bc01d29.output
```

Look for lines like:
- `mem0.memory.main - INFO - {'id': '23', 'text': '...', 'event': 'ADD'}`
- `mem0.vector_stores.pgvector - INFO - Inserting 1 vectors into collection mem0`

---

## Understanding the Data Structure

### Mem0 Table Schema
```
Column  | Type          | Description
--------|---------------|----------------------------------
id      | uuid          | Unique memory ID
vector  | vector(1536)  | Embedding vector (OpenAI ada-002)
payload | jsonb         | Metadata and memory content
```

### Payload Structure
```json
{
  "data": "Memory text here",
  "user_id": "7376426503",
  "source": "patterns.md",
  "created_at": "2025-12-17T06:55:10.594200-08:00",
  "hash": "abc123...",
  "metadata": {"message_type": "text"}
}
```

---

## Common Use Cases

### 1. Debug what the AI knows about you
```bash
python scripts/view_mem0.py YOUR_USER_ID
```

### 2. Find all memories about a specific topic
```bash
python scripts/view_mem0.py YOUR_USER_ID --search "topic"
```

### 3. Check if information was saved
```sql
SELECT payload->>'data' as memory
FROM mem0
WHERE payload->>'user_id' = 'YOUR_USER_ID'
  AND payload->>'data' ILIKE '%keyword%';
```

### 4. View today's memories
```sql
SELECT payload->>'data' as memory, payload->>'created_at' as created_at
FROM mem0
WHERE payload->>'user_id' = 'YOUR_USER_ID'
  AND (payload->>'created_at')::timestamp::date = CURRENT_DATE
ORDER BY (payload->>'created_at')::timestamp DESC;
```

### 5. Export all memories to file
```bash
PGPASSWORD=postgres psql -h localhost -p 5434 -U postgres -d health_agent \
  -c "SELECT payload->>'data' as memory FROM mem0 WHERE payload->>'user_id' = 'YOUR_USER_ID' ORDER BY (payload->>'created_at')::timestamp DESC;" \
  -o my_memories.txt
```

---

## Troubleshooting

### No memories showing?
- Check user_id is correct
- Verify bot is running and processing messages
- Check database connection: `PGPASSWORD=postgres psql -h localhost -p 5434 -U postgres -d health_agent -c "SELECT COUNT(*) FROM mem0;"`

### Script not working?
- Activate virtual environment: `source .venv/bin/activate`
- Check .env file has OPENAI_API_KEY and DATABASE_URL
- Install dependencies: `pip install psycopg python-dotenv`

### Semantic search returning irrelevant results?
- Try more specific keywords
- Use multiple search terms
- Check if memories exist: view all first, then search

---

## Quick Reference

| Task | Command |
|------|---------|
| View all memories | `python scripts/view_mem0.py USER_ID` |
| Search memories | `python scripts/view_mem0.py USER_ID --search "query"` |
| SQL console | `PGPASSWORD=postgres psql -h localhost -p 5434 -U postgres -d health_agent` |
| Count total | `SELECT COUNT(*) FROM mem0;` |
| View logs | `tail -f bot.log` |

---

## Example Output

```
📚 All Memories for User: 7376426503

1. Calorie goal is 2,200-2,300 kcal
   Created: 2025-12-17T06:55:10.594200-08:00
--------------------------------------------------------------------------------

2. Today is a rest day from training
   Created: 2025-12-17T06:55:10.579017-08:00
--------------------------------------------------------------------------------

3. Has injections BPC-157 250mcg and TB-500 2.5mg at 07:00 today
   Created: 2025-12-17T06:55:10.561593-08:00
--------------------------------------------------------------------------------

✅ Total memories: 63
```
