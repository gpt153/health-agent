# ADR-005: PostgreSQL + pgvector for Semantic Search

**Status**: Accepted

**Date**: 2024-11-15

**Deciders**: Health Agent Development Team

---

## Context

The Health Agent needs **semantic memory** to recall relevant context from past conversations beyond the typical 20-message sliding window. Use cases include:

- Remembering user preferences mentioned weeks ago ("I'm vegetarian")
- Recalling past health goals and progress
- Understanding context from previous coaching discussions
- Surfacing relevant past conversations during new interactions

Traditional conversation history (chronological) is limited:
- Only stores recent messages (to fit in LLM context window)
- No semantic search (can't find "what did I say about exercise?")
- Misses important facts from weeks ago

**Research shows**: Semantic memory improves LLM recall by 26% and reduces hallucination in conversational AI.

## Decision

Use **PostgreSQL with the pgvector extension** for semantic memory via the **Mem0** library, rather than a separate vector database.

Architecture:
- **PostgreSQL** - Already used for structured data (food entries, gamification)
- **pgvector extension** - Adds vector similarity search to PostgreSQL
- **Mem0 library** - Manages embedding generation, memory extraction, and retrieval
- **OpenAI embeddings** - text-embedding-3-small model for vector generation

## Rationale

### Why PostgreSQL + pgvector?

1. **Single Database for Everything**
   - Structured data (food entries, XP) already in PostgreSQL
   - Adding pgvector extension enables vector search in same DB
   - No separate database to deploy, backup, monitor
   - Simpler operations and infrastructure

2. **ACID Guarantees for Memories**
   - Memories stored transactionally alongside structured data
   - Consistent backups (one database)
   - Foreign keys between users and their memories
   - Rollback capability for memory operations

3. **Cost-Effective**
   - No additional database service fees (Pinecone, Weaviate are paid services)
   - Uses existing PostgreSQL instance
   - pgvector is open-source and free

4. **Good Performance at Our Scale**
   - Handles millions of vectors efficiently with IVFFlat indexes
   - Sub-second similarity search for our use case (<100K memories)
   - Hybrid queries (vector search + SQL filters) in single query

5. **Mem0 Integration**
   - Mem0 library abstracts complexity (embedding, extraction, retrieval)
   - Handles OpenAI embedding generation automatically
   - Provides clean Python API for memory operations
   - Supports PostgreSQL + pgvector out of the box

### How Semantic Memory Works

**1. Memory Extraction** (after each conversation turn):
```python
# Mem0 analyzes conversation and extracts important facts
await mem0_manager.add_memory(
    user_id="user123",
    messages=[
        {"role": "user", "content": "I'm training for a marathon"},
        {"role": "assistant", "content": "Great! You'll need high carb intake..."}
    ]
)
```

Mem0 internally:
- Identifies important facts ("user is training for marathon")
- Generates embedding using OpenAI's text-embedding-3-small
- Stores in PostgreSQL with pgvector

**2. Memory Retrieval** (during new conversations):
```python
# Search for relevant memories semantically
memories = await mem0_manager.search_memories(
    user_id="user123",
    query="What should I eat before my run?",
    limit=5
)
# Returns: ["User is training for a marathon", "User prefers morning workouts", ...]
```

Mem0 internally:
- Generates embedding for query
- Performs cosine similarity search in pgvector
- Returns top K most relevant memories

**3. Context Injection** (into agent):
```python
# Add semantic memories to agent context
agent_context = f"""
Relevant memories from past conversations:
{format_memories(memories)}

Current conversation:
User: {current_message}
"""

result = await agent.run_sync(agent_context, deps=...)
```

### Database Schema

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Mem0 manages this table
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    memory_text TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI text-embedding-3-small dimension
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB  -- Additional context (source conversation, confidence, etc.)
);

-- IVFFlat index for fast cosine similarity search
CREATE INDEX memories_embedding_idx ON memories
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Index for user-specific queries
CREATE INDEX memories_user_id_idx ON memories(user_id);
```

**Similarity search query**:
```sql
-- Find top 5 memories most similar to query embedding
SELECT memory_text, created_at, metadata
FROM memories
WHERE user_id = $1
ORDER BY embedding <=> $2  -- Cosine distance operator
LIMIT 5;
```

## Alternatives Considered

### Alternative 1: Pinecone (Dedicated Vector Database)

**Rejected because**:
- ❌ Additional service to deploy and monitor
- ❌ Paid service (starts at $70/month for production)
- ❌ Two databases to backup separately (PostgreSQL + Pinecone)
- ❌ Network latency between PostgreSQL and Pinecone
- ❌ Overkill for our scale (<100K vectors initially)

**Considered pros**:
- ✅ Purpose-built for vector search (better performance at massive scale)
- ✅ Advanced features (namespaces, metadata filtering, hybrid search)
- ✅ Managed service (less operational burden)

### Alternative 2: Weaviate (Open-Source Vector Database)

**Rejected because**:
- ❌ Separate database to deploy (Docker, Kubernetes)
- ❌ More complex operations (two databases)
- ❌ Learning curve for team (new database)
- ❌ Backup and consistency challenges (two systems)

**Considered pros**:
- ✅ Open-source (no vendor lock-in)
- ✅ Rich query language (GraphQL)
- ✅ Built-in ML model support

### Alternative 3: Redis with Vector Search

**Rejected because**:
- ❌ In-memory primarily (data durability concerns)
- ❌ Less mature vector search compared to pgvector
- ❌ Would still need PostgreSQL for structured data
- ❌ Higher memory costs (storing vectors in RAM)

**Considered pros**:
- ✅ Fast (in-memory)
- ✅ Already familiar technology
- ✅ Could serve dual purpose (cache + vector search)

### Alternative 4: Elasticsearch with Vector Search

**Rejected because**:
- ❌ Heavy framework (JVM, large resource footprint)
- ❌ Complex setup and operations
- ❌ Overkill for semantic memory (we don't need full-text search features)
- ❌ Higher infrastructure costs

**Considered pros**:
- ✅ Mature ecosystem
- ✅ Full-text search + vector search
- ✅ Advanced analytics capabilities

### Alternative 5: Qdrant (Vector-First Database)

**Rejected because**:
- ❌ Another database to deploy and manage
- ❌ Less mature than PostgreSQL (newer project)
- ❌ Team unfamiliar with technology
- ❌ Two-database complexity

**Considered pros**:
- ✅ Rust-based (fast and memory-efficient)
- ✅ Open-source
- ✅ Good performance benchmarks

## Implementation Details

### Mem0 Configuration

```python
# src/memory/mem0_manager.py
from mem0 import Memory

# Initialize Mem0 with PostgreSQL + pgvector
mem0_config = {
    "vector_store": {
        "provider": "pgvector",
        "config": {
            "dbname": "health_agent",
            "user": "postgres",
            "password": os.getenv("DB_PASSWORD"),
            "host": "localhost",
            "port": 5432
        }
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-3-small",
            "embedding_dims": 1536
        }
    }
}

memory = Memory.from_config(mem0_config)
```

### Adding Memories

```python
async def add_conversation_memory(user_id: str, messages: list[dict]):
    """Extract and store memories from conversation."""
    await memory.add(
        messages=messages,
        user_id=user_id,
        metadata={"source": "telegram", "timestamp": datetime.now().isoformat()}
    )
```

### Searching Memories

```python
async def search_memories(user_id: str, query: str, limit: int = 5) -> list[str]:
    """Search semantic memories relevant to query."""
    results = await memory.search(
        query=query,
        user_id=user_id,
        limit=limit
    )
    return [result["memory"] for result in results]
```

### Integration with Agent

```python
async def get_agent_context_with_memories(
    user_id: str,
    current_message: str,
    conversation_history: list[dict]
) -> str:
    """Build agent context with semantic memories."""

    # Search for relevant memories
    relevant_memories = await search_memories(user_id, current_message, limit=5)

    # Format context
    context = f"""
    ## Long-term Memories (from past conversations)
    {chr(10).join(f"- {mem}" for mem in relevant_memories)}

    ## Recent Conversation
    {format_conversation_history(conversation_history)}

    ## Current Message
    User: {current_message}
    """

    return context
```

## Consequences

### Positive

✅ **Single Database** - PostgreSQL handles structured data + vector search
✅ **Simplified Operations** - One database to backup, monitor, scale
✅ **Cost-Effective** - No additional database service fees
✅ **ACID Guarantees** - Transactional consistency for memories
✅ **Good Performance** - Sub-second search for our scale (<100K vectors)
✅ **Mem0 Abstraction** - Clean API hides complexity
✅ **Improved Recall** - 26% better memory recall (research-backed)
✅ **Graceful Degradation** - Optional feature (system works without it)

### Negative

⚠️ **Performance Ceiling** - pgvector slower than specialized vector DBs at massive scale (millions of vectors)
⚠️ **OpenAI Dependency** - Requires OpenAI API key for embeddings
⚠️ **Additional Latency** - ~500ms for embedding + search per message
⚠️ **API Costs** - Embedding generation costs (~$0.0001 per message)
⚠️ **Index Maintenance** - IVFFlat indexes need occasional rebuilding as data grows

### Performance Characteristics

| Operation | Latency | Cost |
|-----------|---------|------|
| Add memory | ~300ms | ~$0.0001 (embedding) |
| Search memories | ~200ms | ~$0.0001 (query embedding) |
| Total per message | ~500ms | ~$0.0002 |

**Scalability**:
- <100K vectors: Excellent performance
- 100K-1M vectors: Good performance (may need index tuning)
- >1M vectors: Consider dedicated vector DB (Pinecone, Weaviate)

### When to Reconsider

**Migrate to dedicated vector DB if**:
- Memory count exceeds 1 million per user
- Search latency exceeds 1 second
- Hybrid search features needed (metadata filtering + vector search)
- Team grows and vector DB expertise is available

## Monitoring and Observability

### Metrics to Track

```python
# Memory system metrics
METRICS = {
    "memory_add_latency_ms": Histogram(...),
    "memory_search_latency_ms": Histogram(...),
    "memory_count_per_user": Gauge(...),
    "embedding_api_errors": Counter(...),
    "search_result_count": Histogram(...)
}
```

### Health Checks

```python
async def check_memory_system_health() -> bool:
    """Verify memory system is working."""
    try:
        # Test embedding generation
        await memory.add(messages=[{"role": "user", "content": "test"}], user_id="health_check")

        # Test search
        results = await memory.search(query="test", user_id="health_check")

        # Cleanup
        await memory.delete_all(user_id="health_check")

        return True
    except Exception as e:
        logger.error(f"Memory system health check failed: {e}")
        return False
```

## Configuration Flags

**Enable/disable semantic memory**:
```python
# .env
ENABLE_MEM0=true  # Set to false to disable semantic memory
```

**Graceful degradation**:
```python
if os.getenv("ENABLE_MEM0", "false").lower() == "true":
    memories = await search_memories(user_id, query)
else:
    memories = []  # System works without semantic memory
```

## Related Decisions

- **ADR-002**: Three-tier memory architecture - Mem0 is Tier 3 (semantic memory)
- **ADR-001**: PydanticAI agents integrate with Mem0 via RunContext
- See **MEMORY_ARCHITECTURE.md** for comprehensive memory system documentation

## References

- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [Mem0 Documentation](https://docs.mem0.ai/)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- Health Agent Implementation: `/src/memory/mem0_manager.py`

## Revision History

- 2024-11-01: Initial research on semantic memory solutions
- 2024-11-15: Decision to use PostgreSQL + pgvector with Mem0
- 2024-11-20: Mem0 integration implemented
- 2025-01-05: Performance tuning and index optimization
- 2025-01-18: Documentation created for Phase 3.7
