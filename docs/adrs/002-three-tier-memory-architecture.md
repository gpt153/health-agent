# ADR-002: Three-Tier Memory Architecture

**Status**: Accepted

**Date**: 2024-11-15

**Deciders**: Health Agent Development Team

---

## Context

A health coaching AI needs to remember information across conversations to provide personalized, context-aware guidance. The memory system must handle different types of data with varying requirements:

1. **Structured data** - Queryable information (food entries, reminders, XP, streaks)
2. **Configuration data** - User preferences, profile information, habits
3. **Semantic memory** - Long-term conversation context beyond the 20-message window

Each data type has different access patterns, consistency requirements, and query needs.

## Decision

We implement a **three-tier memory architecture**:

1. **PostgreSQL** - Structured, transactional data (food entries, gamification, reminders)
2. **Markdown files** - Human-readable configuration (profile.md, preferences.md)
3. **Mem0 + pgvector** - Semantic memory with vector search for long-term context

## Rationale

### Tier 1: PostgreSQL for Structured Data

**Use cases**: Food entries, reminders, gamification (XP, streaks, achievements), conversation history, user habits

**Why PostgreSQL?**
- ✅ **ACID guarantees** - Food entry corrections need transactional consistency
- ✅ **Complex queries** - "Show me all food entries from last week with >500 calories"
- ✅ **Relationships** - Foreign keys between users, food entries, audit logs
- ✅ **Indexes** - Fast queries on timestamps, user IDs, nutrients
- ✅ **JSON support** - JSONB columns for flexible food composition data
- ✅ **Triggers** - Automatic updated_at timestamps, streak calculations
- ✅ **Vector extension** - pgvector for semantic search (Mem0 integration)

**Schema examples**:
```sql
CREATE TABLE food_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    foods JSONB NOT NULL,  -- Flexible food data
    calories INTEGER NOT NULL,
    protein NUMERIC(6,2),
    photo_path TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_xp (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    tier TEXT DEFAULT 'Beginner'
);
```

### Tier 2: Markdown Files for Configuration

**Use cases**: User profile (demographics), preferences (communication style, reminders), dynamic tools

**Why Markdown?**
- ✅ **Human-readable** - Users can inspect and edit their own data
- ✅ **Version control friendly** - Diffs are meaningful
- ✅ **Simple structure** - Key-value pairs, no complex schema
- ✅ **Agent-friendly** - LLMs can read/write markdown naturally
- ✅ **Portability** - Easy data export for users
- ✅ **Low latency** - File reads faster than DB queries for small config data

**File structure**:
```
production/data/{user_id}/
├── profile.md          # Age, height, weight, goals
├── preferences.md      # Communication style, reminder settings
└── tools/
    ├── track_water.md  # Custom tool: water intake tracking
    └── track_mood.md   # Custom tool: mood tracking
```

**Example profile.md**:
```markdown
# User Profile

## Demographics
- Age: 32
- Height: 175cm
- Weight: 78kg
- Gender: Male

## Health Goals
- Target weight: 73kg
- Daily calorie goal: 2000
- Protein target: 150g

## Activity Level
- Exercise: 3-4 times per week
- Job: Desk job (sedentary)
```

### Tier 3: Mem0 + pgvector for Semantic Memory

**Use cases**: Long-term conversation context, extracted user habits, semantic search over past interactions

**Why Mem0 + pgvector?**
- ✅ **Semantic search** - Find relevant past conversations by meaning, not keywords
- ✅ **Automatic extraction** - Mem0 identifies important information to remember
- ✅ **Beyond 20-message window** - Recall context from weeks ago
- ✅ **Single database** - Uses PostgreSQL with pgvector extension (no separate vector DB)
- ✅ **Embedding management** - Mem0 handles OpenAI embeddings automatically
- ✅ **Graceful degradation** - Optional feature, system works without it

**How it works**:
1. After each conversation turn, Mem0 analyzes the exchange
2. Important facts extracted (e.g., "User is vegetarian", "User dislikes tracking water")
3. Embeddings generated using OpenAI's embedding model
4. Stored in PostgreSQL with pgvector extension
5. Future conversations search memories by semantic similarity
6. Relevant memories injected into agent context

**Performance impact**:
- Research shows 26% improvement in memory recall over conversation-only context
- Adds ~500ms latency per message (embedding + search)
- Requires OpenAI API key (additional cost)

## Alternatives Considered

### Alternative 1: Single PostgreSQL Database for Everything

**Rejected because**:
- ❌ Profile/preferences in DB tables is overkill (simple key-value data)
- ❌ Schema migrations needed for every preference change
- ❌ Less transparent to users (can't easily inspect their data)
- ❌ Semantic search requires vector extension anyway (same DB complexity)

**Considered pros**:
- ✅ Single source of truth
- ✅ ACID guarantees for all data
- ✅ Easier backup/restore

### Alternative 2: All Configuration in Markdown

**Rejected because**:
- ❌ Food entries in markdown are not queryable ("show me calories from last week")
- ❌ No ACID guarantees (concurrent writes could corrupt files)
- ❌ No relationships (can't link food entries to gamification events)
- ❌ Performance degrades with large datasets (scanning files)

**Considered pros**:
- ✅ Simple implementation
- ✅ Human-readable everything
- ✅ Easy data portability

### Alternative 3: Mem0-Only for All Memory

**Rejected because**:
- ❌ Vector search is probabilistic, not deterministic (unreliable for transactional data)
- ❌ No ACID guarantees (can't guarantee streak calculations are correct)
- ❌ Semantic search doesn't replace structured queries
- ❌ Higher API costs (embedding generation for all data)

**Considered pros**:
- ✅ Unified memory interface
- ✅ Powerful semantic search

### Alternative 4: Separate Vector Database (Pinecone, Weaviate)

**Rejected because**:
- ❌ Additional infrastructure complexity
- ❌ Two databases to maintain, backup, monitor
- ❌ Higher operational costs
- ❌ pgvector in PostgreSQL is sufficient for our scale

**Considered pros**:
- ✅ Purpose-built for vector search
- ✅ Better performance at massive scale (millions of vectors)
- ✅ Advanced features (hybrid search, filtering)

## Implementation Details

### Data Routing Logic

```python
# Decision tree for data placement
def save_data(data_type: str, data: Any):
    if data_type in ["food_entry", "reminder", "xp", "streak", "achievement"]:
        # Tier 1: PostgreSQL (structured, queryable)
        await db_manager.save_to_postgres(data)

    elif data_type in ["profile", "preferences", "dynamic_tool"]:
        # Tier 2: Markdown files (configuration)
        await memory_file_manager.save_to_markdown(data)

    elif data_type == "conversation_turn":
        # Tier 3: Mem0 for semantic memory
        await mem0_manager.add_memory(data)
        # Also save to PostgreSQL for conversation history
        await db_manager.save_conversation_history(data)
```

### Memory Retrieval

```python
async def get_agent_context(user_id: str, current_message: str) -> dict:
    """Gather all memory tiers for agent context."""

    # Tier 1: Recent structured data
    recent_foods = await db_manager.get_recent_food_entries(user_id, days=7)
    current_xp = await db_manager.get_user_xp(user_id)
    active_reminders = await db_manager.get_active_reminders(user_id)

    # Tier 2: Configuration files
    profile = await memory_file_manager.read_profile(user_id)
    preferences = await memory_file_manager.read_preferences(user_id)

    # Tier 3: Semantic memory (optional)
    relevant_memories = []
    if mem0_enabled:
        relevant_memories = await mem0_manager.search_memories(
            user_id=user_id,
            query=current_message,
            limit=5
        )

    return {
        "recent_foods": recent_foods,
        "xp": current_xp,
        "reminders": active_reminders,
        "profile": profile,
        "preferences": preferences,
        "semantic_memories": relevant_memories
    }
```

### Database Schema for Semantic Memory

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Mem0 uses this table (managed by Mem0 library)
CREATE TABLE memories (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    memory_text TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI embedding dimension
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Index for fast vector similarity search
CREATE INDEX memories_embedding_idx ON memories
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

## Consequences

### Positive

✅ **Optimal for each data type** - Structured data in DB, config in files, semantics in vectors
✅ **Clear separation of concerns** - Easy to understand what goes where
✅ **Performance** - Fast queries for structured data, fast reads for config, semantic search when needed
✅ **Scalability** - PostgreSQL handles millions of food entries, markdown scales to thousands of users
✅ **Transparency** - Users can read their profile.md and preferences.md
✅ **Flexibility** - Can disable Mem0 without breaking core functionality
✅ **Data portability** - Easy to export markdown files for users

### Negative

⚠️ **Complexity** - Three systems to maintain instead of one
⚠️ **Consistency** - Need to keep tiers in sync (e.g., conversation history in both PostgreSQL and Mem0)
⚠️ **Backup complexity** - Three backup strategies needed
⚠️ **Learning curve** - Developers need to understand tier selection logic
⚠️ **Debugging** - Harder to trace data across three systems

### Migration Notes

**Evolution from previous design**:
- **Removed**: `patterns.md` (user habits now in PostgreSQL `user_habits` table)
- **Removed**: `food_history.md` (food entries now in PostgreSQL `food_entries` table)
- **Reason**: These were structured, queryable data that belonged in Tier 1

**Migration path**:
```python
# Migrate patterns.md → PostgreSQL user_habits table
async def migrate_patterns_to_db(user_id: str):
    patterns_md = read_file(f"data/{user_id}/patterns.md")
    habits = parse_patterns_markdown(patterns_md)
    for habit in habits:
        await db_manager.save_user_habit(user_id, habit)
    archive_file(f"data/{user_id}/patterns.md")
```

## Performance Characteristics

| Operation | Tier 1 (PostgreSQL) | Tier 2 (Markdown) | Tier 3 (Mem0) |
|-----------|---------------------|-------------------|---------------|
| Read latency | 5-20ms | 1-5ms | 200-500ms |
| Write latency | 10-30ms | 2-10ms | 300-700ms |
| Query complexity | High (SQL) | Low (grep) | Medium (vector) |
| Scalability | Millions of rows | Thousands of files | Millions of vectors |
| Consistency | ACID | File locks | Eventual |

## Related Decisions

- **ADR-001**: PydanticAI's RunContext provides dependency injection for all three memory tiers
- **ADR-005**: PostgreSQL + pgvector chosen over separate vector database
- See **MEMORY_ARCHITECTURE.md** for detailed memory system documentation

## References

- [Mem0 Documentation](https://docs.mem0.ai/)
- [pgvector Extension](https://github.com/pgvector/pgvector)
- [PostgreSQL JSONB Documentation](https://www.postgresql.org/docs/current/datatype-json.html)
- Health Agent Implementation: `/src/memory/`, `/src/db/`

## Revision History

- 2024-09-20: Initial memory system with markdown files only
- 2024-10-15: PostgreSQL added for food entries and gamification
- 2024-11-15: Mem0 + pgvector added for semantic memory
- 2024-12-01: Removed patterns.md and food_history.md (migrated to PostgreSQL)
- 2025-01-18: Documentation created for Phase 3.7
