# Memory Architecture

## Overview

The health agent uses a three-tier memory architecture to store and retrieve different types of information efficiently and reliably.

## Layer Responsibilities

### PostgreSQL (Primary Structured Data)

**Purpose**: Single source of truth for queryable, structured data

**Contains**:
- Food entries (with corrections via `food_entry_audit`)
- Reminders & completions
- XP, streaks, achievements (gamification)
- Tracking categories & entries
- Sleep data & quiz submissions
- User profiles (demographics)
- Conversation history
- Onboarding state

**Access Pattern**: Query via `src/db/queries.py` functions

**Storage Rule**: All timestamps stored in UTC

**Why PostgreSQL?**
- ACID compliance ensures data consistency
- Queryable for analytics and reports
- Audit trails for data corrections
- Reliable persistence across restarts

### Markdown Files (`./data/{user_id}/`)

**Purpose**: Human-readable, user-inspectable configuration

**Contains**:
- `profile.md`: Demographics (height, weight, age, goals)
- `preferences.md`: Communication style, coaching preferences

**Access Pattern**: Load via `MemoryFileManager`, inject into system prompt

**Update Pattern**: Via agent tools (`update_profile`, `save_preference`)

**Why Markdown?**
- User can inspect and edit directly
- Simple, structured format
- Loaded into system prompt for context
- No database queries needed for static preferences

**What's NOT Here**:
- ❌ `patterns.md` - REMOVED (redundant with Mem0)
- ❌ `food_history.md` - REMOVED (redundant with PostgreSQL)
- ❌ `visual_patterns.md` - REMOVED (should be in database for queryability)

### Mem0 + pgvector (Semantic Memory) [OPTIONAL]

**Purpose**: Semantic search for unstructured patterns

**Contains**:
- Embeddings of conversation messages
- Auto-extracted facts from user interactions
- Long-term context beyond 20-message window

**Access Pattern**: Semantic search queries

**Use Cases**:
- "Find when user last mentioned sleep issues"
- Detecting implicit preferences not in profile
- Long-term pattern recognition
- Answering questions about past conversations

**Why Mem0?**
- Semantic search capabilities
- Automatic fact extraction
- Long-term memory beyond conversation window
- 26% accuracy improvement for memory recall (research-backed)

**What NOT to Store**:
- ❌ Structured data already in PostgreSQL
- ❌ Current session facts (use tools to query database)
- ❌ PII without proper controls

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interaction                        │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                      Agent (LLM)                             │
│  • Loads profile/preferences from markdown                   │
│  • Queries database for facts (via tools)                   │
│  • Optionally searches Mem0 for patterns                    │
└─────────────────────────────────────────────────────────────┘
                             ↓
        ┌───────────────────┼───────────────────┐
        ↓                   ↓                   ↓
┌──────────────┐  ┌─────────────────┐  ┌──────────────┐
│  PostgreSQL  │  │ Markdown Files  │  │    Mem0      │
│              │  │                 │  │              │
│ • Food       │  │ • profile.md    │  │ • Patterns   │
│ • Reminders  │  │ • preferences.  │  │ • Insights   │
│ • XP/Streaks │  │   md            │  │ • History    │
│ • Sleep      │  │                 │  │              │
└──────────────┘  └─────────────────┘  └──────────────┘
```

## Agent Behavior Rules

### MANDATORY: Database-First Queries

**RULE 1**: NEVER trust conversation history for factual data
- Conversation history is for CONTEXT ONLY
- User may have cleared messages (`/clear`)
- Messages don't persist across sessions

**RULE 2**: ALWAYS query database before stating facts

✅ CORRECT Examples:
- User: "How many calories today?"
  → Call `get_daily_food_summary()` → State result from database

- User: "What's my streak?"
  → Call `get_streak_summary()` → State result from database

❌ WRONG Examples:
- "Based on our earlier conversation, you had 1,234 calories"
  → HALLUCINATION - conversation may be cleared
- "You mentioned your streak is 14 days"
  → HALLUCINATION - trust database, not conversation

### Where Each Type of Data Lives

| Data Type | Storage | Access Method |
|-----------|---------|---------------|
| Food entries | PostgreSQL | `get_daily_food_summary()` |
| Food corrections | PostgreSQL (`food_entry_audit`) | `get_food_entries_by_date()` |
| Reminders | PostgreSQL | `get_reminders()` |
| XP/Levels | PostgreSQL (`user_xp`) | `get_user_xp_data()` |
| Streaks | PostgreSQL (`user_streaks`) | `get_user_streak()` |
| Achievements | PostgreSQL (`user_achievements`) | `get_user_achievements()` |
| Sleep data | PostgreSQL | `get_sleep_entries()` |
| User demographics | Markdown (`profile.md`) | Loaded in system prompt |
| Communication preferences | Markdown (`preferences.md`) | Loaded in system prompt |
| Behavioral patterns | Mem0 (optional) | Semantic search |
| Past conversation context | Mem0 (optional) | Semantic search |

## Migration Notes

### Changes from Previous Architecture

**Removed Files**:
- `patterns.md` → Use Mem0 for unstructured patterns
- `food_history.md` → Use PostgreSQL `food_entries` table
- `visual_patterns.md` → Should be in database table (future enhancement)

**Why These Were Removed**:
1. **Redundancy**: Same data in multiple places led to inconsistency
2. **Queryability**: Markdown files can't be efficiently searched or filtered
3. **Audit trails**: Database provides proper audit logging
4. **Persistence**: Database ensures data survives restarts and `/clear` commands

## Best Practices

### For Developers

1. **Adding New Data Types**:
   - Structured, queryable data → PostgreSQL
   - User configuration → Markdown files (if user-inspectable)
   - Unstructured patterns → Mem0

2. **Querying Data**:
   - Use database queries, not conversation history
   - Store timestamps in UTC, convert for display
   - Use parameterized queries (never string formatting)

3. **Testing Persistence**:
   - Test data survives bot restart
   - Test data survives `/clear` command
   - Test corrections persist in audit tables

### For Agent Development

1. **Always Call Tools**:
   - Before stating any fact, call a database tool
   - Never assume data from conversation history
   - Use system prompt for static preferences only

2. **Validate Responses**:
   - Response validator detects data claims without tool calls
   - Warns about potential hallucinations
   - Helps maintain data integrity

## Future Enhancements

1. **Visual Patterns Database**: Move visual_patterns from markdown to queryable PostgreSQL table
2. **Mem0 Privacy Controls**: PII redaction before embedding
3. **Memory Compression**: Archive old audit records after 90 days
4. **Automated Hallucination Detection**: Use LLM to validate factual accuracy

## References

- [AI Agent Architecture Guide 2025](https://www.lindy.ai/blog/ai-agent-architecture)
- [Memory for AI Agents - Persistent Adaptive Systems](https://medium.com/@20011002nimeth/memory-for-ai-agents-designing-persistent-adaptive-memory-systems-0fb3d25adab2)
- [AWS: Persistent Memory with Mem0](https://aws.amazon.com/blogs/database/build-persistent-memory-for-agentic-ai-applications-with-mem0-open-source-amazon-elasticache-for-valkey-and-amazon-neptune-analytics/)
- PostgreSQL Documentation: [JSONB Functions](https://www.postgresql.org/docs/current/functions-json.html)
