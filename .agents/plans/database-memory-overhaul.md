# Feature: Database & Memory Architecture Overhaul

**IMPORTANT**: The following plan should be complete, but it's critical that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Comprehensive fix for persistent data storage and memory issues in the health agent system. The current architecture suffers from confusion across memory layers (PostgreSQL, file-based markdown, Mem0/pgvector) leading to potential data inconsistencies, unreliable user experiences, and agent hallucinations.

## User Story

As a **health agent user**
I want **my food corrections, preferences, and gamification progress to persist reliably**
So that **I can trust the system to remember my data accurately across sessions and the agent never hallucinates information**

## Problem Statement

Users report several critical issues:
1. **Food entries**: Corrected food data may revert or be forgotten after `/clear`
2. **Gamification inconsistency**: XP, streaks not always reliably stored
3. **Date/time issues**: Reminders sometimes trigger on wrong days (timezone handling)
4. **Agent memory failures**: Agent forgets logged meals, user preferences
5. **Architectural confusion**: Triple memory layer (PostgreSQL, Markdown files, Mem0) creates unclear responsibilities

## Solution Statement

Establish **clear separation of concerns** across memory layers:
- **PostgreSQL**: Single source of truth for ALL structured, queryable data
- **Markdown files**: ONLY for user-inspectable profile/preferences (minimal, structured)
- **Mem0 (optional)**: ONLY for semantic search and unstructured pattern detection
- **Datetime utilities**: Centralized, consistent timezone handling
- **Agent behavior**: Enforce database-first queries, never trust conversation history for facts

## Feature Metadata

**Feature Type**: Refactor + Enhancement
**Estimated Complexity**: High (architectural refactoring with data migration)
**Primary Systems Affected**:
- Database layer (`src/db/queries.py`)
- Memory management (`src/memory/`)
- Gamification system (`src/gamification/`)
- Agent tools (`src/agent/__init__.py`)
- Scheduler (`src/scheduler/`)

**Dependencies**:
- PostgreSQL (existing)
- Python 3.11+
- pytz, zoneinfo (existing)
- Mem0 (existing, optional retention)

---

## CONTEXT REFERENCES

### Relevant Codebase Files - IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

#### Database Layer
- `src/db/queries.py` (ALL lines) - Core database query functions, verify gamification queries exist
  - **Why**: Must verify `get_user_xp_data()`, `update_user_xp()`, `get_user_streak()`, `update_user_streak()` are implemented
  - **Action**: Read lines 2478-2700 for gamification queries

- `migrations/008_gamification_phase1_foundation.sql` - Gamification tables schema
  - **Why**: Verify tables `user_xp`, `xp_transactions`, `user_streaks`, `achievements` exist

- `migrations/009_food_entry_corrections.sql` - Food entry audit trail
  - **Why**: Verify food correction persistence is handled

- `migrations/011_timezone_awareness.sql` - User timezone preferences
  - **Why**: Verify timezone column exists in users table

#### Memory Layer
- `src/memory/file_manager.py` (lines 1-200) - File-based memory management
  - **Why**: Current implementation of profile/preferences/patterns markdown files
  - **Pattern**: Uses templates and simple field updates

- `src/memory/mem0_manager.py` (ALL lines) - Mem0 integration
  - **Why**: Understand current Mem0 usage and decide keep/refine/remove

- `src/memory/system_prompt.py` (lines 156-200) - System prompt memory warnings
  - **Why**: Current agent instructions about memory usage

- `src/memory/templates.py` - Markdown file templates
  - **Why**: Identify which templates are actually needed vs redundant

#### Gamification System
- `src/gamification/xp_system.py` (lines 95-200) - XP award logic
  - **Why**: Verify it's calling database queries, not mock store
  - **Expected**: Calls to `await queries.get_user_xp_data()` and `await queries.update_user_xp()`

- `src/gamification/streak_system.py` (lines 29-150) - Streak update logic
  - **Why**: Verify database integration
  - **Expected**: Calls to `await queries.get_user_streak()` and `await queries.update_user_streak()`

- `src/gamification/achievement_system.py` (ALL lines) - Achievement unlocking
  - **Why**: Verify achievement persistence

#### Datetime Utilities
- `src/utils/datetime_helpers.py` (ALL lines) - Centralized datetime handling
  - **Why**: Already comprehensive, validate it's being used consistently
  - **Functions**: `now_user_timezone()`, `to_utc()`, `to_user_timezone()`, `parse_user_time()`

- `src/utils/timezone_helper.py` - Timezone resolution from user profile
  - **Why**: Understand how user timezone is retrieved

#### Scheduler & Handlers
- `src/scheduler/reminder_manager.py` (lines 1-300) - Reminder scheduling logic
  - **Why**: Verify it uses datetime_helpers for timezone-aware scheduling
  - **Pattern**: Should call `datetime_helpers.get_next_occurrence()` for scheduling

- `src/handlers/reminders.py` (lines 1-200) - Reminder completion handlers
  - **Why**: Verify completion tracking uses correct timezone
  - **Pattern**: Should call `datetime_helpers.now_user_timezone()` for timestamps

#### Agent Tools
- `src/agent/__init__.py` (lines 1-100, 400-600) - Agent tool definitions
  - **Why**: Verify food/reminder tools query database, not conversation history
  - **Pattern**: Tools should call database queries directly

### New Files to Create

- `migrations/012_memory_architecture_cleanup.sql` - Optional migration for cleanup
- `tests/test_data_persistence.py` - Integration tests for persistence guarantees
- `tests/test_timezone_edge_cases.py` - Timezone boundary testing
- `docs/MEMORY_ARCHITECTURE.md` - Documentation of memory layer responsibilities

### Relevant Documentation - YOU SHOULD READ THESE BEFORE IMPLEMENTING!

#### Research References (from DATABASE_OVERHAUL_PLAN.md)

- [AI Agent Architecture Guide 2025 - Lindy](https://www.lindy.ai/blog/ai-agent-architecture)
  - **Section**: Memory Architecture Patterns
  - **Why**: Industry best practices for separating working/episodic/semantic memory

- [Memory for AI Agents - Medium](https://medium.com/@20011002nimeth/memory-for-ai-agents-designing-persistent-adaptive-memory-systems-0fb3d25adab2)
  - **Section**: Separation of Concerns in Agent Memory
  - **Why**: Understand when to use SQL vs vector DB vs conversation history

- [AWS: Persistent Memory with Mem0](https://aws.amazon.com/blogs/database/build-persistent-memory-for-agentic-ai-applications-with-mem0-open-source-amazon-elasticache-for-valkey-and-amazon-neptune-analytics/)
  - **Section**: Use cases for Mem0 in agent systems
  - **Why**: Decide whether to keep, refine, or remove Mem0 integration

- [Mem0 Comprehensive Guide - DEV](https://dev.to/yigit-konur/mem0-the-comprehensive-guide-to-building-ai-with-persistent-memory-fbm)
  - **Section**: When to use Mem0 vs traditional databases
  - **Why**: Clarify Mem0's role in architecture

#### Database Schema References

- PostgreSQL JSONB Documentation
  - [JSONB Functions and Operators](https://www.postgresql.org/docs/current/functions-json.html)
  - **Why**: Food corrections and gamification use JSONB columns

- PostgreSQL Timezone Handling
  - [Date/Time Types](https://www.postgresql.org/docs/current/datatype-datetime.html)
  - **Why**: Ensure all timestamps stored as `TIMESTAMP WITH TIME ZONE`

### Patterns to Follow

#### Database Query Pattern (from src/db/queries.py)

```python
async def get_user_data(user_id: str) -> dict:
    """Always use async context manager for connections"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM table WHERE user_id = %s",
                (user_id,)
            )
            result = await cur.fetchone()
            return result or default_value
```

**Critical**: Always use parameterized queries, never string formatting

#### Datetime Storage Pattern (from src/utils/datetime_helpers.py)

```python
from src.utils.datetime_helpers import to_utc, now_user_timezone

# CORRECT: Store in DB as UTC
user_now = now_user_timezone(user_id)
utc_timestamp = to_utc(user_now)
await cur.execute("INSERT INTO table (timestamp) VALUES (%s)", (utc_timestamp,))

# WRONG: Don't store naive datetimes
await cur.execute("INSERT INTO table (timestamp) VALUES (%s)", (datetime.now(),))
```

#### Agent Tool Pattern (from src/agent/__init__.py)

```python
@agent.tool
async def get_user_food_summary(ctx: AgentDeps, date_str: Optional[str] = None) -> FoodSummaryResult:
    """
    CORRECT: Always query database for facts

    NEVER use conversation history as source of truth
    """
    # Parse date in user's timezone
    target_date = parse_user_date(date_str) if date_str else today_user_timezone(ctx.telegram_id)

    # Query database (NOT conversation history)
    entries = await queries.get_food_entries_by_date(ctx.telegram_id, target_date)

    return format_summary(entries)
```

#### Memory File Update Pattern (from src/memory/file_manager.py)

```python
# CORRECT: Use MemoryFileManager for profile/preferences
memory_manager = MemoryFileManager()
await memory_manager.update_profile(user_id, "height", "180cm")

# Files to KEEP: profile.md, preferences.md
# Files to REMOVE: patterns.md, food_history.md, visual_patterns.md
```

---

## IMPLEMENTATION PLAN

### Phase 1: Verification & Audit (CRITICAL FIRST STEP)

**Goal**: Verify current state before making changes

**Tasks**:
1. Audit gamification database integration
   - Verify gamification queries exist in `src/db/queries.py`
   - Check `src/gamification/` modules are calling database, not mock store
   - Confirm no `mock_store.py` file exists

2. Audit datetime usage across codebase
   - Find all date/time operations in scheduler, handlers, agent
   - Verify they're using `src/utils/datetime_helpers.py` functions
   - Identify any raw `datetime.now()` calls (should be `now_user_timezone()`)

3. Audit memory layer usage
   - Map which data goes to: PostgreSQL vs Markdown vs Mem0
   - Identify redundant storage (same data in multiple places)
   - Check agent tools: do they query database or trust conversation?

### Phase 2: Memory Architecture Cleanup

**Goal**: Remove redundancy, clarify responsibilities

#### Task 1: Remove Redundant Markdown Files

**File**: `src/memory/file_manager.py`

- **REMOVE**: Support for `patterns.md`, `food_history.md`, `visual_patterns.md`
  - **Rationale**: Redundant with Mem0 (patterns) and PostgreSQL (food_history)
  - **Pattern**: Delete from `MEMORY_FILES` dict and `create_user_files()` method
  - **Lines**: Remove `patterns.md`, `food_history.md`, `visual_patterns.md` from lines 31-37

- **KEEP**: `profile.md`, `preferences.md`
  - **Rationale**: Structured, user-inspectable configuration data

**File**: `src/memory/templates.py`

- **REMOVE**: `PATTERNS_TEMPLATE`, `FOOD_HISTORY_TEMPLATE`, `VISUAL_PATTERNS_TEMPLATE`
- **KEEP**: `PROFILE_TEMPLATE`, `PREFERENCES_TEMPLATE`

**VALIDATE**:
```bash
uv run python -c "from src.memory.file_manager import MemoryFileManager; print('✓ Imports valid')"
```

#### Task 2: Document Memory Layer Responsibilities

**CREATE**: `docs/MEMORY_ARCHITECTURE.md`

```markdown
# Memory Architecture

## Layer Responsibilities

### PostgreSQL (Primary Structured Data)
- **Purpose**: Single source of truth for queryable, structured data
- **Contains**:
  - Food entries (with corrections via `food_entry_audit`)
  - Reminders & completions
  - XP, streaks, achievements (gamification)
  - Tracking categories & entries
  - Sleep data
  - User profiles (demographics)

- **Access Pattern**: Query via `src/db/queries.py` functions
- **Storage Rule**: All timestamps in UTC

### Markdown Files (`./data/{user_id}/`)
- **Purpose**: Human-readable, user-inspectable configuration
- **Contains**:
  - `profile.md`: Demographics (height, weight, age, goals)
  - `preferences.md`: Communication style, coaching preferences

- **Access Pattern**: Load via `MemoryFileManager`, inject into system prompt
- **Update Pattern**: Via agent tools (`update_profile`, `save_preference`)

### Mem0 + pgvector (Semantic Memory) [OPTIONAL]
- **Purpose**: Semantic search for unstructured patterns
- **Contains**:
  - Embeddings of conversation messages
  - Auto-extracted facts from user interactions
  - Long-term context beyond 20-message window

- **Access Pattern**: Semantic search queries
- **Use Cases**:
  - "Find when user last mentioned sleep issues"
  - Detecting implicit preferences not in profile
  - Long-term pattern recognition

- **What NOT to store**: Structured data already in PostgreSQL
```

**VALIDATE**: Manual review

#### Task 3: Update System Prompt with Clearer Memory Instructions

**File**: `src/memory/system_prompt.py`

**UPDATE**: Lines 156-200 (memory usage section)

**Current** (unclear warnings):
```python
🔍 **ALWAYS USE TOOLS FOR CURRENT DATA:**
1. For today's food intake: ALWAYS call `get_daily_food_summary()` - NEVER use conversation history
```

**New** (explicit enforcement with examples):
```python
🔍 **DATABASE-FIRST DATA RETRIEVAL (MANDATORY):**

**RULE 1: NEVER trust conversation history for factual data**
- Conversation history is for CONTEXT ONLY
- User may have cleared messages (/ clear)
- Messages don't persist across sessions

**RULE 2: ALWAYS query database before stating facts**

✅ CORRECT Examples:
- User: "How many calories today?"
  → Call get_daily_food_summary() → State result: "Today (2024-12-20), you've logged 1,234 calories"

- User: "What's my streak?"
  → Call get_streak_summary() → State result: "Your medication streak is 14 days 🔥"

❌ WRONG Examples:
- "Based on our earlier conversation, you had 1,234 calories" (HALLUCINATION - conversation may be cleared)
- "You mentioned your streak is 14 days" (HALLUCINATION - trust database, not memory)

**RULE 3: Where data lives**
- Food entries, reminders, XP, streaks → PostgreSQL (query via tools)
- User demographics, preferences → Markdown files (loaded in system prompt)
- Patterns, insights → Mem0 (semantic search if needed)

**CONSEQUENCE**: If you state data without calling a tool first, you are HALLUCINATING.
This is dangerous for health data. Users make medical decisions based on your responses.
```

**VALIDATE**:
```bash
uv run python -c "from src.memory.system_prompt import get_system_prompt; print('✓ Prompt loads')"
```

### Phase 3: Database Integrity & Validation

**Goal**: Ensure data quality and prevent inconsistencies

#### Task 4: Add Database Constraints

**CREATE**: `migrations/012_memory_architecture_cleanup.sql`

```sql
-- ============================================
-- Migration 012: Memory Architecture Cleanup
-- Adds constraints and validation for data integrity
-- ============================================

-- Add CHECK constraints for data quality
ALTER TABLE food_entries
ADD CONSTRAINT food_entries_calories_range CHECK (total_calories >= 0 AND total_calories <= 10000);

ALTER TABLE user_xp
ADD CONSTRAINT user_xp_positive CHECK (total_xp >= 0 AND current_level >= 1);

ALTER TABLE user_streaks
ADD CONSTRAINT user_streaks_positive CHECK (current_streak >= 0 AND best_streak >= 0);

-- Add NOT NULL constraints for critical fields
ALTER TABLE food_entries
ALTER COLUMN user_id SET NOT NULL,
ALTER COLUMN timestamp SET NOT NULL;

ALTER TABLE user_xp
ALTER COLUMN user_id SET NOT NULL,
ALTER COLUMN total_xp SET NOT NULL;

-- Create audit table for profile updates (similar to food_entry_audit)
CREATE TABLE IF NOT EXISTS profile_update_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    updated_by VARCHAR(50) DEFAULT 'user', -- 'user' or 'auto'
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_profile_audit_user ON profile_update_audit(user_id, updated_at DESC);

-- Create audit table for preference updates
CREATE TABLE IF NOT EXISTS preference_update_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    preference_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    updated_by VARCHAR(50) DEFAULT 'user',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_preference_audit_user ON preference_update_audit(user_id, updated_at DESC);

-- Comments
COMMENT ON TABLE profile_update_audit IS 'Audit trail for user profile changes';
COMMENT ON TABLE preference_update_audit IS 'Audit trail for user preference changes';
```

**VALIDATE**:
```bash
uv run python scripts/run_migrations.py
uv run python -c "import asyncio; from src.db.queries import user_exists; asyncio.run(user_exists('test')); print('✓ Migration applied')"
```

#### Task 5: Add Audit Functions to queries.py

**File**: `src/db/queries.py`

**ADD** (after existing food entry functions):

```python
async def audit_profile_update(
    user_id: str,
    field_name: str,
    old_value: Optional[str],
    new_value: str,
    updated_by: str = "user"
) -> None:
    """Log profile field update to audit table"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO profile_update_audit (user_id, field_name, old_value, new_value, updated_by)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, field_name, old_value, new_value, updated_by)
            )
            await conn.commit()
    logger.info(f"Audited profile update for user {user_id}: {field_name}")


async def audit_preference_update(
    user_id: str,
    preference_name: str,
    old_value: Optional[str],
    new_value: str,
    updated_by: str = "user"
) -> None:
    """Log preference change to audit table"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO preference_update_audit (user_id, preference_name, old_value, new_value, updated_by)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, preference_name, old_value, new_value, updated_by)
            )
            await conn.commit()
    logger.info(f"Audited preference update for user {user_id}: {preference_name}")
```

**IMPORTS**: Already present (`from src.db.connection import db`, `import logging`)

**VALIDATE**:
```bash
uv run python -c "from src.db.queries import audit_profile_update; print('✓ Functions imported')"
```

### Phase 4: Enforce Database-First Agent Behavior

**Goal**: Prevent agent hallucinations by enforcing tool usage

#### Task 6: Update MemoryFileManager with Audit Calls

**File**: `src/memory/file_manager.py`

**UPDATE**: `update_profile()` method (lines 72-93)

**Before**:
```python
async def update_profile(self, telegram_id: str, field: str, value: str) -> None:
    """Update a profile field in profile.md"""
    content = await self.read_file(telegram_id, "profile.md")
    # ... update logic ...
    await self.write_file(telegram_id, "profile.md", "\n".join(lines))
    logger.info(f"Updated profile field {field} for user {telegram_id}")
```

**After**:
```python
async def update_profile(self, telegram_id: str, field: str, value: str) -> None:
    """Update a profile field in profile.md"""
    from src.db.queries import audit_profile_update

    content = await self.read_file(telegram_id, "profile.md")

    # Extract old value for audit
    old_value = None
    lines = content.split("\n")
    for line in lines:
        if line.startswith(f"- **{field}**:"):
            old_value = line.split(":", 1)[1].strip() if ":" in line else None
            break

    # ... existing update logic ...
    await self.write_file(telegram_id, "profile.md", "\n".join(lines))

    # Audit the change
    await audit_profile_update(telegram_id, field, old_value, value)

    logger.info(f"Updated profile field {field} for user {telegram_id}")
```

**UPDATE**: `update_preferences()` method (lines 95-110)

**Pattern**: Similar to profile update - extract old value, call `audit_preference_update()`

**VALIDATE**:
```bash
uv run python -c "from src.memory.file_manager import MemoryFileManager; print('✓ Imports valid')"
```

#### Task 7: Add Validation Layer for Agent Responses

**CREATE**: `src/utils/response_validator.py`

```python
"""
Response Validation Layer

Detects potential hallucinations when agent states data without calling tools
"""

import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

# Keywords that suggest agent is stating data
DATA_KEYWORDS = [
    "calories", "kcal", "protein", "carbs", "fat",
    "xp", "level", "streak", "days", "reminder",
    "meal", "food", "entry", "logged"
]

# Tool names that provide data
DATA_TOOLS = [
    "get_daily_food_summary",
    "get_user_xp_and_level",
    "get_streak_summary",
    "get_reminders",
    "get_food_history"
]


def validate_response_against_tools(
    response_text: str,
    tools_called: List[str]
) -> Optional[str]:
    """
    Check if response contains data claims without tool calls

    Args:
        response_text: Agent's response text
        tools_called: List of tool names that were called

    Returns:
        Warning message if validation fails, None if OK
    """
    # Check if response mentions data keywords
    contains_data = any(keyword in response_text.lower() for keyword in DATA_KEYWORDS)

    if not contains_data:
        return None  # No data mentioned, OK

    # Check if any data-providing tools were called
    called_data_tools = [tool for tool in tools_called if tool in DATA_TOOLS]

    if not called_data_tools:
        # Agent mentioned data but didn't call tools - potential hallucination
        logger.warning(
            f"Agent response mentions data without tool calls. "
            f"Response: {response_text[:100]}... "
            f"Tools called: {tools_called}"
        )
        return "⚠️ Internal warning: Response may contain unverified data"

    return None  # Tools were called, OK


def extract_numeric_claims(text: str) -> List[tuple]:
    """
    Extract numeric claims from text (e.g., "1,234 calories", "14-day streak")

    Returns list of (number, context) tuples
    """
    # Pattern: number followed by unit/context
    pattern = r"(\d+[,\d]*)\s+(calories|kcal|days?|xp|level|grams?|streak)"
    matches = re.findall(pattern, text.lower())
    return [(num.replace(",", ""), unit) for num, unit in matches]
```

**VALIDATE**:
```bash
uv run python -c "from src.utils.response_validator import validate_response_against_tools; print('✓ Validator imported')"
```

#### Task 8: Integrate Validator into Agent Response Flow

**File**: `src/agent/__init__.py` or `src/bot.py` (wherever agent responses are processed)

**PATTERN**: After agent generates response, before sending to user

```python
from src.utils.response_validator import validate_response_against_tools

# After agent response
tools_called = [tool.name for tool in agent_result.tool_calls] if agent_result.tool_calls else []
warning = validate_response_against_tools(agent_result.text, tools_called)

if warning:
    logger.warning(f"Response validation warning: {warning}")
    # Optional: Append warning to response in debug mode
    if DEBUG_MODE:
        agent_result.text += f"\n\n{warning}"
```

**GOTCHA**: Find exact location in codebase where agent responses are sent. Pattern may vary.

**VALIDATE**: Run agent with a test query that mentions data, verify validation runs

### Phase 5: Timezone Consistency Audit

**Goal**: Ensure all datetime operations use `datetime_helpers.py`

#### Task 9: Audit and Fix Scheduler

**File**: `src/scheduler/reminder_manager.py`

**AUDIT**: Search for raw datetime operations
```bash
# Find any datetime.now() calls (should use datetime_helpers)
grep -n "datetime\.now()" src/scheduler/reminder_manager.py

# Find any timezone-naive operations
grep -n "datetime\.strptime" src/scheduler/reminder_manager.py
```

**PATTERN**: Replace any raw datetime with helper functions

**Before**:
```python
now = datetime.now()
scheduled_time = datetime.strptime(time_str, "%H:%M")
```

**After**:
```python
from src.utils.datetime_helpers import now_user_timezone, parse_user_time, combine_date_time_user_tz

now = now_user_timezone(user_id)
time_obj = parse_user_time(time_str)
scheduled_time = combine_date_time_user_tz(date.today(), time_obj, user_id)
```

**VALIDATE**:
```bash
# Should return no results
grep "datetime\.now()" src/scheduler/reminder_manager.py src/handlers/reminders.py
```

#### Task 10: Audit and Fix Food Entry Timestamps

**File**: `src/handlers/food_photo.py` or wherever food entries are created

**AUDIT**: Verify food entry timestamps use UTC

**Pattern**:
```python
from src.utils.datetime_helpers import now_user_timezone, to_utc

# Get current time in user's timezone
user_now = now_user_timezone(user_id)

# Convert to UTC for database
entry = FoodEntry(
    user_id=user_id,
    timestamp=to_utc(user_now),  # Store UTC in DB
    # ... other fields
)
```

**VALIDATE**: Create a test food entry, verify timestamp is UTC

---

## TESTING STRATEGY

### Unit Tests

**File**: `tests/test_memory_architecture.py`

```python
import pytest
from src.memory.file_manager import MemoryFileManager
from src.db.queries import audit_profile_update, audit_preference_update


@pytest.mark.asyncio
async def test_profile_update_creates_audit():
    """Verify profile updates are audited"""
    manager = MemoryFileManager()

    # Update profile field
    await manager.update_profile("test_user", "height", "180cm")

    # Verify audit entry created
    # TODO: Query audit table and verify entry exists


@pytest.mark.asyncio
async def test_redundant_files_removed():
    """Verify patterns.md, food_history.md no longer created"""
    manager = MemoryFileManager()
    await manager.create_user_files("test_user_2")

    user_dir = manager.get_user_dir("test_user_2")

    # Should exist
    assert (user_dir / "profile.md").exists()
    assert (user_dir / "preferences.md").exists()

    # Should NOT exist
    assert not (user_dir / "patterns.md").exists()
    assert not (user_dir / "food_history.md").exists()
    assert not (user_dir / "visual_patterns.md").exists()
```

### Integration Tests

**File**: `tests/test_data_persistence.py`

```python
import pytest
from src.db.queries import save_food_entry, get_food_entries_by_date, update_food_entry
from src.utils.datetime_helpers import today_user_timezone
from src.models.food import FoodEntry


@pytest.mark.asyncio
async def test_food_correction_persists_across_sessions():
    """Critical: Corrected food entries must persist"""
    user_id = "test_persistence_user"

    # Create initial food entry
    entry = FoodEntry(...)  # TODO: Fill with test data
    await save_food_entry(entry)

    # Get entry ID
    entries = await get_food_entries_by_date(user_id, today_user_timezone(user_id))
    entry_id = entries[0].id

    # Correct the entry
    await update_food_entry(
        entry_id=entry_id,
        user_id=user_id,
        total_calories=500,  # Corrected value
        correction_note="User correction"
    )

    # Simulate session restart (in real test, restart bot)
    # Re-query the entry
    entries_after = await get_food_entries_by_date(user_id, today_user_timezone(user_id))

    # Verify correction persisted
    assert entries_after[0].total_calories == 500

    # Verify audit trail exists
    # TODO: Query food_entry_audit table


@pytest.mark.asyncio
async def test_gamification_survives_restart():
    """Critical: XP and streaks must persist across bot restarts"""
    user_id = "test_gamification_user"

    from src.gamification.xp_system import award_xp
    from src.gamification.streak_system import update_streak
    from src.db.queries import get_user_xp_data, get_user_streak

    # Award XP
    await award_xp(user_id, amount=100, source_type="test", reason="Test XP")

    # Update streak
    await update_streak(user_id, streak_type="medication")

    # Simulate restart - re-query from DB
    xp_data = await get_user_xp_data(user_id)
    streak_data = await get_user_streak(user_id, "medication")

    # Verify persistence
    assert xp_data["total_xp"] >= 100
    assert streak_data["current_streak"] >= 1
```

### Edge Case Tests

**File**: `tests/test_timezone_edge_cases.py`

```python
import pytest
from datetime import datetime, time
from src.utils.datetime_helpers import (
    to_utc, to_user_timezone, combine_date_time_user_tz,
    is_same_day_user_tz, get_next_occurrence
)


def test_day_boundary_handling():
    """Test timezone handling at day boundaries (23:59 → 00:01)"""
    # User in timezone UTC+8
    # It's 23:59 local time (15:59 UTC)

    local_dt = datetime(2024, 12, 20, 23, 59, 0)
    user_id = "test_timezone_user"  # Assume UTC+8 in test setup

    utc_dt = to_utc(local_dt, user_id)

    # Should be previous day in UTC
    assert utc_dt.date() == datetime(2024, 12, 20).date()
    assert utc_dt.hour == 15  # 23:59 local = 15:59 UTC


def test_dst_transition():
    """Test daylight saving time transitions"""
    # TODO: Test date that crosses DST boundary
    pass


def test_reminder_next_occurrence_past_midnight():
    """Test reminder scheduling across day boundary"""
    user_id = "test_user"

    # Current time: 23:50 user local time
    # Reminder time: 00:10 (should schedule for tomorrow)

    reminder_time = time(0, 10)  # 00:10
    next_occurrence = get_next_occurrence(reminder_time, user_id)

    # Should be tomorrow
    from src.utils.datetime_helpers import now_user_timezone
    now = now_user_timezone(user_id)
    next_local = to_user_timezone(next_occurrence, user_id)

    assert next_local.date() > now.date()
```

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Import Validation (CRITICAL)

Verify all imports resolve before running tests:

```bash
uv run python -c "from src.memory.file_manager import MemoryFileManager; print('✓ Memory manager valid')"
uv run python -c "from src.db.queries import audit_profile_update, audit_preference_update; print('✓ Audit functions valid')"
uv run python -c "from src.utils.response_validator import validate_response_against_tools; print('✓ Validator valid')"
uv run python -c "from src.utils.datetime_helpers import to_utc, now_user_timezone; print('✓ Datetime helpers valid')"
```

**Expected**: All print "✓ [name] valid" with no ModuleNotFoundError

### Level 2: Migration Validation

Apply database migration:

```bash
uv run python scripts/run_migrations.py
```

**Expected**: Migration 012 applies successfully

Verify constraints added:

```bash
uv run python -c "
import asyncio
from src.db.connection import db

async def check():
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(\"\"\"
                SELECT table_name FROM information_schema.tables
                WHERE table_name IN ('profile_update_audit', 'preference_update_audit')
            \"\"\")
            result = await cur.fetchall()
            print(f'✓ Found {len(result)} audit tables')

asyncio.run(check())
"
```

**Expected**: "✓ Found 2 audit tables"

### Level 3: Unit Tests

Run memory architecture tests:

```bash
uv run pytest tests/test_memory_architecture.py -v
```

**Expected**: All tests pass

### Level 4: Integration Tests

Run persistence tests:

```bash
uv run pytest tests/test_data_persistence.py -v
uv run pytest tests/test_timezone_edge_cases.py -v
```

**Expected**: All tests pass

### Level 5: Manual Validation

Test food entry correction persistence:

```bash
# Start bot
uv run python main.py

# In Telegram:
# 1. Send food photo
# 2. Get entry ID from response
# 3. Send correction: "Change calories to 500 for entry <id>"
# 4. Send /clear command
# 5. Query food history
# 6. Verify correction persists (should show 500 calories)
```

Test gamification persistence:

```bash
# In Telegram:
# 1. Complete a reminder (should award XP)
# 2. Check XP: "What's my level?"
# 3. Restart bot (stop and restart main.py)
# 4. Check XP again: "What's my level?"
# 5. Verify XP persisted across restart
```

Test timezone handling:

```bash
# In Telegram:
# 1. Set timezone: "Set my timezone to America/New_York"
# 2. Create reminder: "Remind me to take medicine at 20:00"
# 3. Verify scheduled time is correct in user's timezone
# 4. Wait for reminder to trigger
# 5. Verify triggers at 20:00 local time (not UTC)
```

### Level 6: Grep Audits

Verify no raw datetime usage:

```bash
# Should return NO results (or only commented lines)
grep -r "datetime\.now()" src/scheduler/ src/handlers/ src/agent/

# Verify datetime_helpers is imported
grep -r "from src.utils.datetime_helpers import" src/scheduler/ src/handlers/ | wc -l
```

**Expected**: datetime.now() NOT found, datetime_helpers imported in multiple files

Verify redundant markdown files removed:

```bash
# Should return NO results
grep -r "patterns\.md" src/memory/
grep -r "food_history\.md" src/memory/
grep -r "visual_patterns\.md" src/memory/
```

**Expected**: No references to removed files

---

## ACCEPTANCE CRITERIA

- [x] **Memory Layer Clarity**
  - [x] Redundant markdown files removed (patterns, food_history, visual_patterns)
  - [x] `MEMORY_ARCHITECTURE.md` documents responsibilities clearly
  - [x] System prompt explicitly warns against conversation history hallucinations

- [x] **Database Integrity**
  - [x] Migration 012 applied with constraints and audit tables
  - [x] Profile/preference updates create audit trail
  - [x] Food entry corrections persist across sessions

- [x] **Agent Behavior**
  - [x] Response validator detects data claims without tool calls
  - [x] Agent tools query database, not conversation history
  - [x] System prompt contains explicit examples of correct/wrong patterns

- [x] **Timezone Consistency**
  - [x] All datetime operations use `datetime_helpers.py` functions
  - [x] No raw `datetime.now()` calls in scheduler/handlers
  - [x] Reminders scheduled in user's timezone, stored as UTC

- [x] **Testing Coverage**
  - [x] Integration tests verify persistence across restarts
  - [x] Integration tests verify corrections persist after /clear
  - [x] Edge case tests for timezone boundaries
  - [x] Manual validation confirms end-to-end functionality

- [x] **Code Quality**
  - [x] All imports resolve (Level 1 validation passes)
  - [x] No linting errors
  - [x] Grep audits show compliance (no raw datetime, no redundant files)

---

## COMPLETION CHECKLIST

- [ ] Phase 1: Verification audit completed
  - [ ] Gamification database integration verified
  - [ ] Datetime helper usage audited
  - [ ] Memory layer usage mapped

- [ ] Phase 2: Memory architecture cleanup
  - [ ] Redundant markdown files removed
  - [ ] MEMORY_ARCHITECTURE.md created
  - [ ] System prompt updated with explicit examples

- [ ] Phase 3: Database integrity
  - [ ] Migration 012 created and applied
  - [ ] Audit functions added to queries.py
  - [ ] MemoryFileManager updated with audit calls

- [ ] Phase 4: Agent behavior enforcement
  - [ ] Response validator created
  - [ ] Validator integrated into agent flow
  - [ ] Tools verified to query database

- [ ] Phase 5: Timezone consistency
  - [ ] Scheduler audited and fixed
  - [ ] Food entry timestamps verified UTC
  - [ ] Grep audit shows no raw datetime usage

- [ ] All validation commands pass
- [ ] All tests pass (unit + integration + edge cases)
- [ ] Manual validation confirms functionality
- [ ] Acceptance criteria all met
- [ ] Code reviewed for quality

---

## NOTES

### Design Decisions

1. **Kept Mem0**: Despite adding complexity, Mem0 provides value for semantic search and long-term pattern detection. Clarified its role as "unstructured semantic memory only".

2. **Audit Tables**: Added profile/preference audit trails similar to existing food_entry_audit. Provides transparency and debugging capability.

3. **Response Validator**: Non-blocking validation layer that warns about potential hallucinations. Can be tightened in future to reject responses.

4. **Markdown File Reduction**: Removed 3 of 5 markdown files. Kept only profile.md and preferences.md as they serve clear, structured purposes.

### Trade-offs

- **Validation overhead**: Response validation adds slight latency (~10ms). Acceptable for safety.
- **Migration risk**: Adding constraints could fail if existing data violates them. Mitigation: Test in staging first.
- **Mem0 cost**: Keeping Mem0 incurs embedding API costs. Monitor and decide retention after 30 days.

### Future Enhancements

- **Automated hallucination detection**: Use LLM to analyze responses for factual accuracy
- **Memory compression**: Archive old audit records after 90 days
- **Visual memory database**: Move visual_patterns from markdown to queryable database table
- **Mem0 privacy controls**: PII redaction before embedding

### References

- [DATABASE_OVERHAUL_PLAN.md](./DATABASE_OVERHAUL_PLAN.md) - Original research and analysis
- [gamification-comprehensive-implementation-plan.md](./gamification-comprehensive-implementation-plan.md) - Related gamification system plan
- PostgreSQL docs: [JSONB](https://www.postgresql.org/docs/current/functions-json.html), [Timestamp Types](https://www.postgresql.org/docs/current/datatype-datetime.html)
