# Mem0 Memory Management

Tools to view, search, and manage your Mem0 semantic memories.

## Quick View Script (Recommended)

Simple shell script for viewing memories:

### List Your Memories
```bash
./scripts/mem0_view.sh 7376426503 list 20
```

### Search Memories
```bash
./scripts/mem0_view.sh 7376426503 search 'training'
./scripts/mem0_view.sh 7376426503 search 'injection'
```

### Count Total Memories
```bash
./scripts/mem0_view.sh 7376426503 count
```

### Delete a Memory
```bash
# First, list to find the ID
./scripts/mem0_view.sh 7376426503 list

# Then delete by ID
./scripts/mem0_view.sh 7376426503 delete 'fccac209-...'
```

## Direct Database Access

You can also query directly:

```bash
# View all memories
PGPASSWORD=postgres psql -h localhost -p 5434 -U postgres -d health_agent -c "
  SELECT payload->>'data' as memory 
  FROM mem0 
  WHERE payload->>'user_id' = '7376426503'
  ORDER BY id DESC 
  LIMIT 20;
"

# Search for specific content
PGPASSWORD=postgres psql -h localhost -p 5434 -U postgres -d health_agent -c "
  SELECT payload->>'data' as memory 
  FROM mem0 
  WHERE payload->>'user_id' = '7376426503'
    AND payload->>'data' ILIKE '%sleep%'
  LIMIT 10;
"

# Delete all memories for a user (CAREFUL!)
PGPASSWORD=postgres psql -h localhost -p 5434 -U postgres -d health_agent -c "
  DELETE FROM mem0 WHERE payload->>'user_id' = '7376426503';
"
```

## What Mem0 Stores

Mem0 automatically extracts and stores:
- Facts about you (training schedule, sleep times, etc.)
- Preferences and habits
- Questions you've asked
- Important information from conversations

These memories are used for semantic search to provide context-aware responses.

## When to Edit Memories

- **Outdated information**: Goal changed from 85kg to 80kg
- **Incorrect facts**: Bot misunderstood something
- **Privacy**: Remove sensitive information
- **Duplicates**: Multiple similar memories

## Best Practices

1. **Don't delete too much** - More context = better responses
2. **Keep facts current** - Update when goals/routines change
3. **Remove mistakes** - If bot stored wrong information
4. **Check periodically** - Review what's stored monthly
