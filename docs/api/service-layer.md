# Service Layer API Documentation

The Health Agent's service layer provides business logic services that are consumed by agent tools and API endpoints. This document describes the key services and their public methods.

---

## Architecture Overview

```
Agent Tools / API Endpoints
          ↓
    Service Layer (This Document)
          ↓
    Data Layer (PostgreSQL, Markdown, Mem0)
```

**Services**:
1. Memory Services (MemoryFileManager, Mem0Manager)
2. Vision Services (Multi-Agent Consensus)
3. Nutrition Services (USDA FoodData Central)
4. Gamification Services (XP, Streaks, Achievements)
5. Reminder Services (ReminderManager)
6. Dynamic Tool Services (Tool Manager)

---

## 1. Memory Services

### MemoryFileManager

Manages user configuration and preferences stored in Markdown files.

**Location**: `src/memory/file_manager.py`

#### Methods

##### `read_profile(telegram_id: str) -> dict`

Read user profile from `profile.md`.

**Returns**:
```python
{
    "age": 32,
    "height_cm": 175,
    "weight_kg": 78,
    "goal": "Lose 5kg and build muscle",
    "dietary_restrictions": ["vegetarian"],
    ...
}
```

##### `update_profile(telegram_id: str, updates: dict) -> None`

Update specific fields in `profile.md`.

**Example**:
```python
await memory_manager.update_profile("123456", {"age": 33, "weight_kg": 76})
```

##### `read_preferences(telegram_id: str) -> dict`

Read communication preferences from `preferences.md`.

**Returns**:
```python
{
    "communication_style": "casual",
    "emoji_usage": "frequent",
    "reminder_time": "09:00",
    ...
}
```

##### `save_preference(telegram_id: str, preference: str, value: str) -> None`

Save a single preference to `preferences.md`.

---

### Mem0Manager

Manages semantic memory using Mem0 library with PostgreSQL + pgvector.

**Location**: `src/memory/mem0_manager.py`

#### Methods

##### `add_memory(user_id: str, messages: list[dict]) -> None`

Extract and store important facts from a conversation.

**Example**:
```python
await mem0_manager.add_memory(
    user_id="user123",
    messages=[
        {"role": "user", "content": "I'm training for a marathon"},
        {"role": "assistant", "content": "Great! You'll need high carb intake"}
    ]
)
```

**Internal Process**:
1. Mem0 identifies important facts ("user is training for marathon")
2. Generates embedding using OpenAI
3. Stores in `memories` table with pgvector

##### `search_memories(user_id: str, query: str, limit: int = 5) -> list[str]`

Search semantic memories by similarity.

**Example**:
```python
memories = await mem0_manager.search_memories(
    user_id="user123",
    query="What should I eat before running?",
    limit=5
)
# Returns: ["User is training for marathon", "User prefers morning workouts", ...]
```

##### `delete_all_memories(user_id: str) -> None`

Delete all memories for a user (privacy/GDPR compliance).

---

## 2. Vision Services

### Multi-Agent Consensus System

Analyzes food photos using 3 specialist agents + 1 moderator for accurate nutrition estimation.

**Location**: `src/vision/multi_agent_consensus.py`

#### Methods

##### `analyze_food_photo(photo_path: str) -> dict`

Analyze food photo and return nutrition consensus.

**Returns**:
```python
{
    "foods": [
        {"name": "chicken breast", "amount": "200g"},
        {"name": "brown rice", "amount": "150g"}
    ],
    "calories": 450,
    "protein": 30.5,
    "carbs": 45.0,
    "fat": 8.0,
    "confidence": "high",  # high, medium, low
    "reasoning": "Conservative and USDA estimates aligned on calories...",
    "estimates": {
        "conservative": {"calories": 400, "protein": 28},
        "moderate": {"calories": 450, "protein": 30.5},
        "optimistic": {"calories": 520, "protein": 33}
    }
}
```

**Process**:
1. 3 specialist agents analyze photo in parallel
2. Moderator synthesizes estimates
3. USDA FoodData Central verification
4. Consensus built with confidence rating

**Latency**: ~5 seconds
**Cost**: ~$0.02 per photo (4 LLM calls)

---

## 3. Nutrition Services

### USDA FoodData Central Client

Interfaces with USDA's public nutrition database.

**Location**: `src/nutrition/usda_client.py`

#### Methods

##### `search_food(query: str) -> list[dict]`

Search for food in USDA database.

**Example**:
```python
results = await usda_client.search_food("chicken breast")
# Returns: [{"fdcId": 171477, "description": "Chicken, broilers, breast, raw"}]
```

##### `get_food_details(fdc_id: int) -> dict`

Get detailed nutrition information for a food.

**Returns**:
```python
{
    "fdcId": 171477,
    "description": "Chicken, broilers, breast, raw",
    "nutrients": {
        "calories": 110,  # per 100g
        "protein": 23.0,
        "carbohydrates": 0,
        "fat": 1.2
    }
}
```

##### `scale_nutrition(nutrition: dict, amount_grams: int) -> dict`

Scale nutrition data to a specific portion size.

**Example**:
```python
scaled = usda_client.scale_nutrition(nutrition_per_100g, amount_grams=200)
# Returns: {"calories": 220, "protein": 46.0, ...}
```

---

## 4. Gamification Services

### XP System

**Location**: `src/gamification/xp_system.py`

#### Methods

##### `award_xp(user_id: str, activity_type: str, quality_bonus: int = 0) -> dict`

Award XP for completing a health activity.

**Base XP by Activity**:
- Food log (text): 50 XP
- Food log (photo): 75 XP
- Reminder completion: 25 XP
- Challenge completion: 100-500 XP

**Returns**:
```python
{
    "xp_gained": 70,
    "total_xp": 520,
    "level": 3,
    "level_up": False,
    "new_level": None,
    "tier": "Bronze"
}
```

##### `calculate_level(xp: int) -> tuple[int, str]`

Calculate level and tier from XP amount.

**Formula**: `xp_for_level_N = N² × 100`

**Tiers**:
- Bronze: Levels 1-10
- Silver: Levels 11-25
- Gold: Levels 26-50
- Platinum: Levels 51+

**Example**:
```python
level, tier = calculate_level(xp=450)
# Returns: (3, "Bronze")
```

---

### Streak System

**Location**: `src/gamification/streak_system.py`

#### Methods

##### `update_streak(user_id: str, activity: str) -> dict`

Update streak for an activity.

**Returns**:
```python
{
    "current_streak": 7,
    "best_streak": 15,
    "streak_bonus_xp": 35  # min(current_streak × 5, 100)
}
```

##### `check_streak_broken(user_id: str, activity: str) -> bool`

Check if a streak was broken (no activity yesterday).

---

### Achievement System

**Location**: `src/gamification/achievement_system.py`

#### Methods

##### `check_achievements(user_id: str) -> list[dict]`

Check for newly unlocked achievements.

**Example Achievements**:
- "First Steps" - Log first food entry
- "Week Warrior" - 7-day logging streak
- "Centurion" - Log 100 food entries
- "Level 5" - Reach level 5

**Returns**:
```python
[
    {
        "achievement_id": "uuid-123",
        "name": "Week Warrior",
        "description": "Maintain a 7-day logging streak",
        "xp_reward": 100
    }
]
```

---

### Challenge System

**Location**: `src/gamification/challenge_system.py`

#### Methods

##### `get_available_challenges(difficulty: Optional[str] = None) -> list[dict]`

Get list of challenges user can start.

##### `start_challenge(user_id: str, challenge_id: str) -> dict`

Begin a new challenge for the user.

##### `update_challenge_progress(user_id: str, challenge_id: str, progress: dict) -> dict`

Update progress on an active challenge.

**Returns**:
```python
{
    "challenge_id": "uuid-123",
    "name": "30-Day Protein Challenge",
    "progress_percent": 45.0,
    "completed": False,
    "reward_xp": 500
}
```

---

## 5. Reminder Services

### ReminderManager

Manages scheduling and triggering of health reminders.

**Location**: `src/reminders/scheduler.py`

#### Methods

##### `schedule_reminder(user_id: str, message: str, time: str, is_recurring: bool) -> str`

Schedule a new reminder.

**Returns**: `reminder_id` (UUID)

**Internal**: Creates APScheduler job with cron trigger

##### `trigger_reminder(reminder_id: str) -> None`

Execute a scheduled reminder (called by APScheduler).

**Process**:
1. Fetch reminder from database
2. Send Telegram notification to user
3. Log completion in `reminder_completions` table
4. Award XP for completion

##### `get_user_reminders(user_id: str) -> list[dict]`

List all active reminders for a user.

##### `delete_reminder(reminder_id: str) -> None`

Delete a reminder and remove from scheduler.

---

## 6. Dynamic Tool Services

### Tool Manager

Manages runtime creation and validation of user-defined tools.

**Location**: `src/agent/dynamic_tools.py`

#### Methods

##### `validate_tool_code(code: str) -> tuple[bool, Optional[str]]`

Validate tool code for security and correctness.

**Checks**:
- No file system access
- No network calls
- No dangerous imports (os, subprocess, etc.)
- Valid Python syntax
- Type hints present

**Returns**: `(is_valid, error_message)`

##### `register_tool(tool_name: str, tool_func: callable) -> None`

Register a new tool on both agents (Claude, GPT-4o).

**Example**:
```python
async def track_water(ctx: RunContext[AgentDeps], glasses: int) -> str:
    # Tool implementation
    return f"Logged {glasses} glasses of water"

tool_manager.register_tool("track_water", track_water)
```

##### `classify_tool_type(code: str) -> str`

Classify tool based on operations (read-only, write, destructive).

**Returns**: "read_only" | "data_write" | "data_delete"

---

## Service Dependency Injection

Services are injected into agent tools via `RunContext[AgentDeps]`:

```python
# In src/bot.py or src/api/app.py
deps = AgentDeps(
    telegram_id=user_id,
    memory_manager=MemoryFileManager(),
    user_memory=await load_user_memory(user_id),
    reminder_manager=ReminderManager(),
    bot_application=bot_app
)

result = await claude_agent.run_sync(user_message, deps=deps)
```

This allows tools to access services without global state or tight coupling.

---

## Error Handling Patterns

All service methods use consistent error handling:

```python
# Service method
async def some_service_method(param: str) -> dict:
    try:
        result = await do_operation(param)
        return {"success": True, "data": result}
    except SomeSpecificError as e:
        logger.error(f"Operation failed: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return {"success": False, "error": "Internal server error"}
```

Agent tools interpret `success: False` and communicate errors naturally to users.

---

## Performance Considerations

### Async-First Design

All service methods are async to avoid blocking:

```python
# Good - Non-blocking
async def get_food_entries(user_id: str) -> list:
    return await db.fetch_all(query, {"user_id": user_id})

# Bad - Blocks event loop
def get_food_entries_sync(user_id: str) -> list:
    return db.fetch_all_sync(query, {"user_id": user_id})
```

### Database Connection Pooling

PostgreSQL connections managed by `psycopg-pool`:

```python
# src/db/connection.py
pool = AsyncConnectionPool(
    conninfo=DATABASE_URL,
    min_size=2,
    max_size=10
)
```

Prevents connection exhaustion under load.

### Caching (Future Enhancement)

Frequently accessed data (user profile, preferences) could be cached:

```python
# Future: Redis cache layer
cached_profile = await redis.get(f"profile:{user_id}")
if not cached_profile:
    profile = await memory_manager.read_profile(user_id)
    await redis.setex(f"profile:{user_id}", 3600, json.dumps(profile))
```

---

## Testing Services

Services can be unit tested independently:

```python
# tests/unit/test_xp_system.py
import pytest
from src.gamification.xp_system import award_xp

@pytest.mark.asyncio
async def test_award_xp_food_log():
    result = await award_xp(
        user_id="test_user",
        activity_type="food_log_photo",
        quality_bonus=10
    )

    assert result["xp_gained"] == 85  # 75 base + 10 bonus
    assert result["success"] == True
```

---

## Related Documentation

- **Agent Interface**: `/docs/api/agent-interface.md` - Tools that consume these services
- **Database Schema**: `/docs/api/database-schema.md` - Tables used by services
- **ADR-002**: Three-tier memory architecture (MemoryFileManager, Mem0Manager design)
- **ADR-004**: Multi-agent nutrition consensus (Vision service design)

## Revision History

- 2025-01-18: Initial service layer documentation created for Phase 3.7
