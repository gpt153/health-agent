# Database Schema Documentation

Complete PostgreSQL database schema for the Health Agent system, including core tables, gamification, memory, and tracking systems.

---

## Database Overview

- **Database**: `health_agent`
- **Engine**: PostgreSQL 14+
- **Extensions**: `pgvector` (vector similarity search for Mem0)
- **Migration System**: Numbered SQL files in `/migrations/`
- **Total Tables**: 20+

---

## Core Tables

### `users`

Primary user account table.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes**:
- Primary key on `id`
- Unique index on `telegram_id`

**Triggers**: `update_updated_at` (auto-update timestamp on modification)

---

### `food_entries`

Food logging data with JSONB for flexible food composition.

```sql
CREATE TABLE food_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    photo_path VARCHAR(500),
    foods JSONB NOT NULL,              -- [{name, quantity, calories, macros}]
    total_calories INTEGER,
    total_macros JSONB,                -- {protein, carbs, fat}
    meal_type VARCHAR(50),             -- breakfast/lunch/dinner/snack
    notes TEXT
);
```

**JSONB Structure**:
```json
{
  "foods": [
    {"name": "chicken breast", "quantity": "200g", "calories": 220, "protein": 46, "carbs": 0, "fat": 2.5}
  ],
  "total_macros": {"protein": 46.0, "carbs": 0, "fat": 2.5}
}
```

**Indexes**:
- `idx_food_entries_user_timestamp` - Fast user queries by date
- `idx_food_entries_foods` - GIN index for JSONB food searches

---

### `food_entry_audit`

Audit log for food entry corrections.

```sql
CREATE TABLE food_entry_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_id UUID NOT NULL REFERENCES food_entries(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id),
    original_data JSONB NOT NULL,
    corrected_data JSONB NOT NULL,
    correction_reason TEXT,
    corrected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose**: Preserve original data when users correct food entries

---

### `conversation_history`

Conversation message history for agent context.

```sql
CREATE TABLE conversation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,         -- "user", "assistant", "system"
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Usage**: Agent loads last 20 messages for conversation context

**Indexes**: `idx_conversation_user_timestamp` - Fast chronological retrieval

---

## Gamification Tables

### `user_xp`

XP, level, and tier tracking.

```sql
CREATE TABLE user_xp (
    user_id VARCHAR(255) PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    tier VARCHAR(50) DEFAULT 'Bronze',     -- Bronze, Silver, Gold, Platinum
    last_xp_award TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Level Formula**: `xp_for_level_N = N² × 100`

**Tiers**:
- Bronze: Levels 1-10
- Silver: Levels 11-25
- Gold: Levels 26-50
- Platinum: Levels 51+

---

### `user_streaks`

Daily activity streaks across different domains.

```sql
CREATE TABLE user_streaks (
    user_id VARCHAR(255) PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
    current_streak INTEGER DEFAULT 0,
    best_streak INTEGER DEFAULT 0,
    last_activity_date DATE,
    -- Domain-specific streaks
    food_logging_streak INTEGER DEFAULT 0,
    reminder_completion_streak INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Streak Calculation**: Activity on consecutive days

**Streak Bonus XP**: `min(current_streak × 5, 100)`

---

### `user_achievements`

Unlocked achievements for milestones.

```sql
CREATE TABLE user_achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    achievement_id VARCHAR(100) NOT NULL,
    achievement_name VARCHAR(200) NOT NULL,
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    progress JSONB,                    -- Optional progress data
    UNIQUE(user_id, achievement_id)
);
```

**Example Achievements**:
- `first_steps` - Log first food entry
- `week_warrior` - 7-day logging streak
- `centurion` - Log 100 food entries
- `level_5` - Reach level 5

---

### `user_challenges`

Active and completed challenges.

```sql
CREATE TABLE user_challenges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    challenge_id VARCHAR(100) NOT NULL,
    challenge_name VARCHAR(200) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',   -- active, completed, failed
    progress JSONB NOT NULL,               -- Challenge-specific progress
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    UNIQUE(user_id, challenge_id, status)
);
```

**Challenge Types**:
- Daily protein intake (30 days)
- Water intake tracking (7 days)
- Consistent logging (14 days)

---

## Reminder Tables

### `reminders`

Scheduled health reminders.

```sql
CREATE TABLE reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    reminder_type VARCHAR(50) NOT NULL,    -- "simple", "tracking_prompt"
    message TEXT NOT NULL,
    schedule JSONB NOT NULL,               -- {type: "daily", time: "09:00", days: [0,1,2,3,4,5,6]}
    active BOOLEAN DEFAULT true,
    job_id VARCHAR(255),                   -- APScheduler job ID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Schedule JSONB Examples**:
```json
{
  "type": "daily",
  "time": "09:00",
  "days": [0, 1, 2, 3, 4, 5, 6]  // All days
}
```

```json
{
  "type": "one_time",
  "datetime": "2025-01-20T15:30:00"
}
```

**Indexes**: `idx_reminders_user_active` - Fast active reminder queries

---

### `reminder_completions`

Log of triggered reminders and user responses.

```sql
CREATE TABLE reminder_completions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reminder_id UUID NOT NULL REFERENCES reminders(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id),
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed BOOLEAN DEFAULT false,
    completed_at TIMESTAMP
);
```

**Usage**: Track reminder effectiveness and gamification triggers

---

## Tracking System Tables

### `tracking_categories`

User-defined tracking categories (water, mood, sleep, etc.).

```sql
CREATE TABLE tracking_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    fields JSONB NOT NULL,                 -- Field definitions with types
    schedule JSONB,                        -- When to prompt for data
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, name)
);
```

**Fields JSONB Example**:
```json
{
  "fields": [
    {"name": "glasses", "type": "number", "required": true, "min": 0, "max": 20},
    {"name": "notes", "type": "text", "required": false}
  ]
}
```

---

### `tracking_entries`

Logged entries for custom tracking categories.

```sql
CREATE TABLE tracking_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES tracking_categories(id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data JSONB NOT NULL,                   -- Actual tracked data
    notes TEXT
);
```

**Data JSONB Example**:
```json
{"glasses": 8, "notes": "Felt hydrated"}
```

---

## Memory Tables

### `user_habits`

Extracted user habits and patterns (from conversations).

```sql
CREATE TABLE user_habits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    habit_type VARCHAR(100) NOT NULL,      -- "dietary", "exercise", "sleep", etc.
    habit_description TEXT NOT NULL,
    confidence NUMERIC(3,2),               -- 0.00 to 1.00
    evidence JSONB,                        -- Supporting data points
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Example**:
```sql
INSERT INTO user_habits (user_id, habit_type, habit_description, confidence)
VALUES ('123456', 'dietary', 'Prefers high-protein breakfast', 0.85);
```

---

### `memories` (Mem0 Semantic Memory)

Semantic memories with vector embeddings for similarity search.

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    memory_text TEXT NOT NULL,
    embedding vector(1536),                -- OpenAI text-embedding-3-small
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB                         -- Source, confidence, etc.
);
```

**Indexes**:
```sql
-- IVFFlat index for fast cosine similarity search
CREATE INDEX memories_embedding_idx ON memories
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX memories_user_id_idx ON memories(user_id);
```

**Usage**: Mem0 library manages this table automatically

**Query Example**:
```sql
SELECT memory_text, created_at
FROM memories
WHERE user_id = '123456'
ORDER BY embedding <=> '[query_embedding_vector]'
LIMIT 5;
```

---

## Dynamic Tools Tables

### `dynamic_tools`

User-created custom tools (advanced feature).

```sql
CREATE TABLE dynamic_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    tool_name VARCHAR(100) NOT NULL,
    tool_description TEXT NOT NULL,
    tool_code TEXT NOT NULL,               -- Python code (validated)
    tool_type VARCHAR(50) NOT NULL,        -- "read_only", "data_write", "data_delete"
    approved BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, tool_name)
);
```

**Security**: Code validated before execution (see `src/agent/dynamic_tools.py`)

---

### `tool_approval_requests`

Pending approval requests for dynamic tools.

```sql
CREATE TABLE tool_approval_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    tool_id UUID NOT NULL REFERENCES dynamic_tools(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, approved, rejected
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);
```

---

## Onboarding Tables

### `user_onboarding`

Track onboarding progress for new users.

```sql
CREATE TABLE user_onboarding (
    user_id VARCHAR(255) PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
    state VARCHAR(100) NOT NULL,           -- "welcome", "collect_age", "collect_goals", "complete"
    path VARCHAR(50) DEFAULT 'standard',   -- "standard", "quick", "detailed"
    data JSONB,                            -- Collected onboarding data
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

---

### `sleep_quiz_submissions`

Sleep quality quiz responses (onboarding feature).

```sql
CREATE TABLE sleep_quiz_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    responses JSONB NOT NULL,              -- Quiz answers
    sleep_score INTEGER,
    recommendations JSONB,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Multi-User Support Tables

### `subscriptions`

User subscription status for premium features (future).

```sql
CREATE TABLE subscriptions (
    user_id VARCHAR(255) PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
    plan VARCHAR(50) DEFAULT 'free',       -- free, premium, pro
    status VARCHAR(50) DEFAULT 'active',   -- active, cancelled, expired
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);
```

---

### `invite_codes`

Invitation system for controlled access.

```sql
CREATE TABLE invite_codes (
    code VARCHAR(50) PRIMARY KEY,
    created_by VARCHAR(255) REFERENCES users(telegram_id),
    max_uses INTEGER DEFAULT 1,
    current_uses INTEGER DEFAULT 0,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Database Triggers

### Auto-Update Timestamps

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Applied to: users, user_habits, memories, tracking_categories
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

---

## Indexes Summary

**Performance-Critical Indexes**:
- `idx_food_entries_user_timestamp` - Food entry queries by date
- `idx_conversation_user_timestamp` - Conversation history retrieval
- `idx_reminders_user_active` - Active reminder lookups
- `memories_embedding_idx` - Vector similarity search (IVFFlat)
- GIN indexes on JSONB columns - Fast JSON key searches

**Index Maintenance**:
- IVFFlat indexes need periodic reindexing as data grows
- ANALYZE run weekly for query plan optimization

---

## Migration System

**Location**: `/migrations/`

**Naming Convention**: `NNN_description.sql`

**Execution**: Auto-run on Docker container startup via `docker-entrypoint-initdb.d`

**Key Migrations**:
- `001_initial_schema.sql` - Core tables
- `008_gamification_foundation.sql` - XP, streaks, achievements
- `016_user_habits.sql` - Habit extraction system
- `020_pgvector_mem0.sql` - Semantic memory support

**Creating New Migrations**:
1. Create `NNN_description.sql` (increment number)
2. Use `CREATE TABLE IF NOT EXISTS` for idempotence
3. Test migration on dev database
4. Commit to repository

---

## Data Retention and Privacy

**User Data Deletion**:
```sql
-- Cascade delete removes all user data
DELETE FROM users WHERE telegram_id = '123456';
-- Deletes: food_entries, reminders, tracking_entries, memories, etc.
```

**Data Retention**:
- Food entries: Indefinite (until user deletion)
- Conversation history: Last 1000 messages per user (pruned weekly)
- Photos: 30 days (then archived to cold storage)
- Audit logs: 1 year

---

## Performance Monitoring

**Query Performance**:
```sql
-- Slow query analysis
EXPLAIN ANALYZE SELECT * FROM food_entries
WHERE user_id = '123456' AND DATE(timestamp) = '2025-01-18';
```

**Connection Pool Status**:
```python
# psycopg-pool
print(f"Total connections: {pool.get_stats()['total']}")
print(f"Available: {pool.get_stats()['available']}")
```

**Database Size**:
```sql
SELECT pg_size_pretty(pg_database_size('health_agent'));
```

---

## Related Documentation

- **Service Layer**: `/docs/api/service-layer.md` - Services that query these tables
- **Agent Interface**: `/docs/api/agent-interface.md` - Tools that create/modify data
- **ADR-002**: Three-tier memory architecture (rationale for table organization)
- **Deployment Guide**: `/docs/deployment/database-migrations.md` - Migration procedures

## Revision History

- 2025-01-18: Initial database schema documentation created for Phase 3.7
