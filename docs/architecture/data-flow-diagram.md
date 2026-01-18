# Data Flow Diagram

This document illustrates how data moves through the Health Agent system, from user input to storage and retrieval.

---

## High-Level Data Flow

```mermaid
flowchart TD
    USER[User Input<br/>Telegram / API]

    subgraph INPUT["Data Input Processing"]
        PARSE[Message Parsing]
        EXTRACT[Context Extraction]
        VALIDATE[Validation]
    end

    subgraph PROCESSING["Agent Processing"]
        AGENT[PydanticAI Agent<br/>Natural Language Understanding]
        TOOLS[Tool Execution]
        SERVICES[Service Layer<br/>Vision, Gamification, etc.]
    end

    subgraph STORAGE["Data Storage (Three Tiers)"]
        direction TB
        TIER1[Tier 1: PostgreSQL<br/>Structured Data]
        TIER2[Tier 2: Markdown<br/>Configuration]
        TIER3[Tier 3: Mem0<br/>Semantic Memory]
    end

    subgraph RETRIEVAL["Data Retrieval"]
        QUERY[Query Processing]
        AGGREGATE[Data Aggregation]
        FORMAT[Response Formatting]
    end

    OUTPUT[Response Output<br/>Telegram / API]

    USER --> INPUT
    INPUT --> PROCESSING
    PROCESSING --> STORAGE
    STORAGE --> RETRIEVAL
    RETRIEVAL --> OUTPUT
    OUTPUT --> USER

    PROCESSING -.Context Lookup.-> RETRIEVAL

    style TIER1 fill:#e8f5e9,stroke:#1b5e20
    style TIER2 fill:#fff3e0,stroke:#e65100
    style TIER3 fill:#f3e5f5,stroke:#4a148c
```

---

## Detailed Data Flows by Category

### 1. Food Entry Data Flow

```mermaid
flowchart LR
    PHOTO[Food Photo]
    TEXT[Text Description]

    subgraph VISION["Vision AI Processing"]
        MULTI[Multi-Agent<br/>Consensus]
        USDA[USDA<br/>Verification]
    end

    subgraph STRUCTURED["Structured Data"]
        FE[food_entries<br/>table]
        AUDIT[food_entry_audit<br/>table]
    end

    subgraph GAMIF["Gamification"]
        XP[user_xp<br/>update]
        STREAK[user_streaks<br/>update]
    end

    PHOTO --> MULTI
    TEXT --> MULTI
    MULTI --> USDA
    USDA --> FE
    FE --> AUDIT
    FE --> GAMIF
    GAMIF --> XP
    GAMIF --> STREAK

    style FE fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
```

**Flow Steps**:
1. User sends photo or text
2. Vision AI (multi-agent consensus) analyzes food
3. USDA verifies nutrition data
4. Food entry saved to `food_entries` table
5. Audit log created in `food_entry_audit`
6. Gamification triggers (XP award, streak update)

**Data Storage**:
- **PostgreSQL**: `food_entries`, `food_entry_audit`
- **File System**: Photo files in `production/photos/{user_id}/`
- **Mem0**: Memory of food preferences extracted

---

### 2. Memory Tier Routing Logic

```mermaid
flowchart TD
    DATA[Data to Store]

    DECISION{Data Type?}

    STRUCTURED[Structured /<br/>Queryable Data]
    CONFIG[Configuration /<br/>Preferences]
    SEMANTIC[Conversation<br/>Context]

    TIER1[(PostgreSQL<br/>Tier 1)]
    TIER2[Markdown Files<br/>Tier 2]
    TIER3[(Mem0 + pgvector<br/>Tier 3)]

    DATA --> DECISION

    DECISION -->|Food entries<br/>Reminders<br/>Gamification| STRUCTURED
    DECISION -->|Profile<br/>Preferences<br/>Tools| CONFIG
    DECISION -->|Conversations<br/>Extracted facts| SEMANTIC

    STRUCTURED --> TIER1
    CONFIG --> TIER2
    SEMANTIC --> TIER3

    TIER1 -.Examples.-> EXAMPLES1[food_entries<br/>user_xp<br/>reminders]
    TIER2 -.Examples.-> EXAMPLES2[profile.md<br/>preferences.md<br/>tools/]
    TIER3 -.Examples.-> EXAMPLES3[memories table<br/>with embeddings]

    style TIER1 fill:#e8f5e9,stroke:#1b5e20,stroke-width:3px
    style TIER2 fill:#fff3e0,stroke:#e65100,stroke-width:3px
    style TIER3 fill:#f3e5f5,stroke:#4a148c,stroke-width:3px
```

**Decision Criteria**:
- **Tier 1 (PostgreSQL)**: Requires SQL queries, relationships, ACID guarantees
- **Tier 2 (Markdown)**: Human-readable config, rarely changes, key-value data
- **Tier 3 (Mem0)**: Semantic search needed, long-term context, extracted insights

---

### 3. Conversation History vs Semantic Memory

```mermaid
flowchart TB
    MSG[User Message]

    subgraph SHORTTERM["Short-Term Memory"]
        HISTORY[Conversation History<br/>Last 20 messages]
        WINDOW[Sliding Window]
    end

    subgraph LONGTERM["Long-Term Memory"]
        EXTRACT[Fact Extraction]
        EMBED[Embedding Generation]
        VECTOR[Vector Storage]
    end

    CONTEXT[Agent Context]

    MSG --> HISTORY
    HISTORY --> WINDOW

    MSG --> EXTRACT
    EXTRACT --> EMBED
    EMBED --> VECTOR

    WINDOW --> CONTEXT
    VECTOR -.Semantic Search.-> CONTEXT

    HISTORY -.PostgreSQL.-> DB1[(conversation_history)]
    VECTOR -.pgvector.-> DB2[(memories)]

    style SHORTTERM fill:#fff3e0,stroke:#e65100
    style LONGTERM fill:#f3e5f5,stroke:#4a148c
```

**Comparison**:

| Aspect | Conversation History | Semantic Memory |
|--------|---------------------|-----------------|
| Storage | PostgreSQL (`conversation_history`) | PostgreSQL with pgvector (`memories`) |
| Retrieval | Chronological (last N messages) | Semantic similarity search |
| Purpose | Recent context | Long-term insights |
| Lifespan | Rolling window (20 messages) | Persistent (deleted manually) |
| Size | ~5KB per conversation | ~10KB per memory |

---

### 4. Gamification Data Flow

```mermaid
flowchart LR
    subgraph TRIGGERS["Activity Triggers"]
        FOOD[Food Logged]
        REMINDER[Reminder<br/>Completed]
        STREAK[Streak<br/>Maintained]
    end

    subgraph CALC["XP Calculation"]
        BASE[Base XP<br/>by Activity]
        BONUS[Streak Bonus<br/>Quality Bonus]
        TOTAL[Total XP]
    end

    subgraph UPDATE["Database Updates"]
        UX[user_xp<br/>xp, level, tier]
        US[user_streaks<br/>current, best]
        UA[user_achievements<br/>unlocked]
    end

    TRIGGERS --> CALC
    CALC --> UPDATE

    UPDATE -.Check Achievements.-> ACHIEVE[Achievement<br/>System]
    ACHIEVE -.Unlock.-> UA

    style UX fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
```

**XP Calculation**:
```
total_xp = base_xp + streak_bonus + quality_bonus

base_xp:
- Food log (text): 50 XP
- Food log (photo): 75 XP
- Reminder completion: 25 XP
- Challenge completion: 100-500 XP

streak_bonus: min(current_streak × 5, 100)
quality_bonus: 0-50 (based on data completeness)
```

---

### 5. Query Aggregation Flow

When a user asks "What did I eat this week?", data is aggregated from multiple sources:

```mermaid
flowchart TD
    QUERY[User Query:<br/>"What did I eat this week?"]

    subgraph SOURCES["Data Sources"]
        DB_FOOD[(food_entries<br/>PostgreSQL)]
        DB_HABITS[(user_habits<br/>PostgreSQL)]
        MEM[Semantic Memories<br/>Mem0]
    end

    subgraph AGGREGATE["Aggregation"]
        SQL[SQL Query<br/>GROUP BY date]
        ANALYZE[Pattern Analysis]
        ENRICH[Enrich with<br/>Semantic Context]
    end

    subgraph FORMAT["Formatting"]
        SUMMARY[Daily Summaries]
        INSIGHTS[Insights<br/>"You ate more protein this week"]
        MARKDOWN[Markdown Table]
    end

    RESPONSE[Agent Response]

    QUERY --> DB_FOOD
    QUERY --> DB_HABITS
    QUERY --> MEM

    DB_FOOD --> SQL
    DB_HABITS --> ANALYZE
    MEM --> ENRICH

    SQL --> SUMMARY
    ANALYZE --> INSIGHTS
    ENRICH --> INSIGHTS

    SUMMARY --> MARKDOWN
    INSIGHTS --> MARKDOWN
    MARKDOWN --> RESPONSE
```

**Example Response**:
```
Here's what you ate this week:

Monday: 1,850 cal (95g protein, 180g carbs, 60g fat)
- Breakfast: Oatmeal with berries
- Lunch: Grilled chicken salad
- Dinner: Salmon with quinoa

Tuesday: 2,100 cal (110g protein, 200g carbs, 70g fat)
...

📊 Weekly totals: 13,500 cal, 680g protein
💡 Insight: You averaged 97g protein/day (above your 90g goal!)
```

---

### 6. Photo Storage and Retrieval

```mermaid
flowchart LR
    UPLOAD[Telegram Photo<br/>Upload]

    subgraph STORAGE["Storage"]
        DOWNLOAD[Download from<br/>Telegram Servers]
        SAVE[Save to Local<br/>File System]
        PATH[Generate Path:<br/>production/photos/<br/>{user_id}/{timestamp}.jpg]
    end

    subgraph DATABASE["Database Link"]
        FE_TABLE[food_entries.photo_path]
    end

    subgraph RETRIEVAL["Retrieval"]
        QUERY_DB[Query food_entry<br/>with photo_path]
        SERVE[Serve from<br/>File System]
    end

    UPLOAD --> DOWNLOAD
    DOWNLOAD --> SAVE
    SAVE --> PATH
    PATH --> FE_TABLE

    FE_TABLE --> QUERY_DB
    QUERY_DB --> SERVE

    style PATH fill:#fff3e0,stroke:#e65100,stroke-width:2px
```

**Storage Structure**:
```
production/
└── photos/
    └── {user_id}/
        ├── 2025-01-18_12-30-45_abc123.jpg
        ├── 2025-01-18_18-15-22_def456.jpg
        └── ...
```

**Cleanup Policy**:
- Photos older than 30 days archived to cold storage
- Archived photos compressed (JPEG quality 80 → 60)
- User can request photo deletion anytime

---

## Data Volume and Growth

### Current Production Metrics (Single User)

| Data Type | Count | Size | Growth Rate |
|-----------|-------|------|-------------|
| Food entries | ~500/month | 50KB/entry | ~25MB/month |
| Photos | ~300/month | 2MB/photo | ~600MB/month |
| Conversations | ~1000 messages/month | 1KB/message | ~1MB/month |
| Memories (Mem0) | ~100/month | 10KB/memory | ~1MB/month |
| **Total** | - | ~650MB/month | - |

### Projected Scaling (100 Users)

| Metric | Current (1 user) | Projected (100 users) |
|--------|------------------|----------------------|
| Database size | 100MB | 10GB |
| Photo storage | 10GB/year | 1TB/year |
| Daily food entries | 15-20 | 1,500-2,000 |
| Database queries/sec | <1 | 50-100 |

**Scaling strategies**: See `/docs/deployment/scaling.md`

---

## Data Security and Privacy

### Sensitive Data Handling

```mermaid
flowchart TD
    DATA[User Data]

    SENSITIVE{Sensitive?}

    YES_PATH[YES:<br/>Health data, photos,<br/>personal info]
    NO_PATH[NO:<br/>XP, streaks,<br/>public info]

    ENCRYPT[Encryption at Rest<br/>PostgreSQL encryption]
    ACCESS[Access Control<br/>User ID filtering]
    AUDIT[Audit Logging]

    PLAINTEXT[Standard Storage]

    DATA --> SENSITIVE
    SENSITIVE -->|Yes| YES_PATH
    SENSITIVE -->|No| NO_PATH

    YES_PATH --> ENCRYPT
    ENCRYPT --> ACCESS
    ACCESS --> AUDIT

    NO_PATH --> PLAINTEXT

    style YES_PATH fill:#ffebee,stroke:#c62828,stroke-width:2px
    style ENCRYPT fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
```

**Privacy Measures**:
- ✅ Telegram ID whitelist (only authorized users)
- ✅ All database queries filtered by `user_id`
- ✅ Food photos not shared externally
- ✅ Markdown files readable only by user
- ✅ API requires authentication (API key)
- ✅ No data sold to third parties

---

## Related Documentation

- **Component Diagram**: `/docs/architecture/component-diagram.md` - System structure
- **Sequence Diagrams**: `/docs/architecture/sequence-diagrams.md` - Interaction flows
- **Database Schema**: `/docs/api/database-schema.md` - Complete schema reference
- **ADR-002**: Three-tier memory architecture decision
- **MEMORY_ARCHITECTURE.md**: Detailed memory system documentation

## Revision History

- 2025-01-18: Initial data flow diagram created for Phase 3.7 documentation
