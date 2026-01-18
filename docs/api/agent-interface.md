# PydanticAI Agent Interface Documentation

This document describes the PydanticAI agent tools available in the Health Agent system. These tools enable the conversational AI to perform actions like saving food entries, managing reminders, tracking health metrics, and more.

---

## Agent Architecture

The Health Agent uses **PydanticAI** to define tools that the LLM can call during conversations. Two agents are configured:

1. **Claude Agent** - Uses Anthropic Claude 3.5 Sonnet
2. **GPT Agent** - Uses OpenAI GPT-4o

Both agents share the same tool set, allowing seamless switching between models.

### Tool Registration Pattern

```python
from pydantic_ai import Agent, RunContext

claude_agent = Agent(
    model="claude-3-5-sonnet-20241022",
    system_prompt=SYSTEM_PROMPT,
    deps_type=AgentDeps,
    retries=2
)

gpt_agent = Agent(
    model="openai:gpt-4o",
    system_prompt=SYSTEM_PROMPT,
    deps_type=AgentDeps,
    retries=2
)

# Tools are registered on both agents
@claude_agent.tool()
@gpt_agent.tool()
async def tool_name(ctx: RunContext[AgentDeps], param: type) -> ReturnType:
    """Tool description for the LLM."""
    # Tool implementation
    ...
```

---

## Agent Dependencies (RunContext)

All tools receive a `RunContext[AgentDeps]` which provides access to services and user context.

```python
@dataclass
class AgentDeps:
    """Dependencies injected into agent tools"""
    telegram_id: str                    # User's Telegram ID
    memory_manager: MemoryFileManager   # Access to markdown files (profile.md, preferences.md)
    user_memory: dict                   # Pre-loaded user memory (profile, preferences, habits)
    reminder_manager: ReminderManager   # Reminder scheduling service (optional)
    bot_application: Application        # Telegram bot for sending notifications (optional)
```

**Accessing dependencies in tools**:
```python
async def my_tool(ctx: RunContext[AgentDeps], param: str) -> str:
    telegram_id = ctx.deps.telegram_id
    memory_manager = ctx.deps.memory_manager
    user_memory = ctx.deps.user_memory

    # Use dependencies
    await memory_manager.update_profile(telegram_id, {"field": param})
    ...
```

---

## Tool Categories

The Health Agent provides 30+ tools across these categories:

1. **Profile & Preferences** - Update user information and communication settings
2. **Food Tracking** - Log and query food entries
3. **Custom Tracking** - Create user-defined tracking categories
4. **Reminders** - Schedule, manage, and track health reminders
5. **Gamification** - XP, streaks, achievements, and challenges
6. **Memory & Facts** - Long-term memory management
7. **Dynamic Tools** - User-created custom tools (advanced)
8. **User Management** - Onboarding and multi-user support

---

## 1. Profile & Preferences Tools

### `update_profile`

Update user demographic information in `profile.md`.

```python
async def update_profile(
    ctx: RunContext[AgentDeps],
    field: str,
    value: str
) -> ProfileUpdateResult
```

**Parameters**:
- `field` (str): Profile field to update (e.g., "age", "height_cm", "weight_kg", "goal")
- `value` (str): New value for the field

**Returns**:
```python
ProfileUpdateResult(
    success=True,
    message="Age updated to 32",
    field="age",
    value="32"
)
```

**Example Usage** (natural language):
- "I'm 32 years old"
- "My current weight is 78kg"
- "Update my goal to lose 5kg"

**File Modified**: `production/data/{telegram_id}/profile.md`

---

### `save_preference`

Save communication preferences to `preferences.md`.

```python
async def save_preference(
    ctx: RunContext[AgentDeps],
    preference: str,
    value: str
) -> PreferenceSaveResult
```

**Parameters**:
- `preference` (str): Preference name (e.g., "communication_style", "reminder_time", "emoji_usage")
- `value` (str): Preference value

**Returns**:
```python
PreferenceSaveResult(
    success=True,
    message="Communication style set to casual",
    preference="communication_style",
    value="casual"
)
```

**Example Usage**:
- "I prefer casual communication"
- "Use lots of emojis"
- "Send reminders at 9am"

**File Modified**: `production/data/{telegram_id}/preferences.md`

---

## 2. Food Tracking Tools

### `get_daily_food_summary`

Retrieve food entries for a specific date with nutrition totals.

```python
async def get_daily_food_summary(
    ctx: RunContext[AgentDeps],
    date: Optional[str] = None
) -> DailyFoodSummaryResult
```

**Parameters**:
- `date` (str, optional): Date in YYYY-MM-DD format. Defaults to today.

**Returns**:
```python
DailyFoodSummaryResult(
    success=True,
    date="2025-01-18",
    total_calories=1850,
    total_protein=95.5,
    total_carbs=180.2,
    total_fat=62.3,
    entries=[
        {"time": "08:30", "foods": ["oatmeal", "banana"], "calories": 350},
        {"time": "12:45", "foods": ["chicken salad"], "calories": 450},
        ...
    ]
)
```

**Example Usage**:
- "What did I eat today?"
- "Show me yesterday's food log"
- "How many calories did I eat on January 15th?"

**Database Query**: `SELECT * FROM food_entries WHERE user_id = ? AND DATE(created_at) = ?`

---

### `update_food_entry_tool`

Correct a previously logged food entry.

```python
async def update_food_entry_tool(
    ctx: RunContext[AgentDeps],
    entry_id: str,
    corrected_foods: Optional[list[dict]] = None,
    corrected_calories: Optional[int] = None,
    corrected_protein: Optional[float] = None,
    corrected_carbs: Optional[float] = None,
    corrected_fat: Optional[float] = None,
    correction_reason: Optional[str] = None
) -> FoodUpdateResult
```

**Parameters**:
- `entry_id` (str): UUID of the food entry to update
- `corrected_*` (optional): New values for nutrition fields
- `correction_reason` (str, optional): Why the correction was made

**Returns**:
```python
FoodUpdateResult(
    success=True,
    message="Food entry updated",
    entry_id="abc-123-def",
    audit_log_created=True
)
```

**Example Usage**:
- "Actually that was 200g of chicken, not 150g"
- "Correct my last entry: I had 2 slices of pizza, not 1"

**Database Operations**:
- `UPDATE food_entries SET ...`
- `INSERT INTO food_entry_audit` (preserves original for audit trail)

---

### `log_food_from_text_validated`

Log food from text description with multi-agent validation.

```python
async def log_food_from_text_validated(
    ctx: RunContext[AgentDeps],
    food_description: str,
    validation_level: str = "standard"
) -> FoodLogResult
```

**Parameters**:
- `food_description` (str): Natural language description of food
- `validation_level` (str): "quick" | "standard" | "thorough"

**Returns**:
```python
FoodLogResult(
    success=True,
    message="Food logged: 450 calories, 30g protein",
    foods=[{"name": "chicken breast", "amount": "200g"}],
    calories=450,
    protein=30.0,
    confidence="high"
)
```

**Example Usage**:
- "I ate 200g chicken breast and 150g brown rice"
- "I had a large burger with fries"

**Processing**:
1. Multi-agent consensus parses food description
2. USDA FoodData Central validates nutrition
3. Food entry saved to database

---

## 3. Custom Tracking Tools

### `create_new_tracking_category`

Create a custom tracking category (e.g., water intake, mood, sleep quality).

```python
async def create_new_tracking_category(
    ctx: RunContext[AgentDeps],
    name: str,
    fields: list[TrackingField],
    schedule: Optional[TrackingSchedule] = None
) -> TrackingCategoryResult
```

**Parameters**:
- `name` (str): Category name (e.g., "Water Intake")
- `fields` (list): List of fields to track (see `TrackingField` model)
- `schedule` (optional): Auto-reminder schedule

**TrackingField Model**:
```python
class TrackingField(BaseModel):
    name: str                      # Field name (e.g., "glasses")
    field_type: str                # "number", "text", "boolean", "select"
    required: bool = True
    default_value: Optional[str] = None
    options: Optional[list[str]] = None  # For "select" type
```

**Returns**:
```python
TrackingCategoryResult(
    success=True,
    message="Water intake tracking category created",
    category_name="Water Intake",
    category_id="uuid-123"
)
```

**Example Usage**:
- "Create a water intake tracker that measures glasses per day"
- "I want to track my mood (happy/neutral/sad) daily"

**Database**: `INSERT INTO tracking_categories`

---

### `log_tracking_entry`

Log an entry for a custom tracking category.

```python
async def log_tracking_entry(
    ctx: RunContext[AgentDeps],
    category_name: str,
    data: dict
) -> TrackingEntryResult
```

**Parameters**:
- `category_name` (str): Name of the tracking category
- `data` (dict): Field values (e.g., `{"glasses": 8}`)

**Returns**:
```python
TrackingEntryResult(
    success=True,
    message="Water intake logged: 8 glasses",
    category="Water Intake",
    data={"glasses": 8}
)
```

**Example Usage**:
- "I drank 8 glasses of water today"
- "My mood is happy"

**Database**: `INSERT INTO tracking_entries`

---

## 4. Reminder Tools

### `schedule_reminder`

Schedule a one-time or recurring reminder.

```python
async def schedule_reminder(
    ctx: RunContext[AgentDeps],
    message: str,
    time: str,
    is_recurring: bool = False,
    recurrence_pattern: Optional[str] = None
) -> ReminderScheduleResult
```

**Parameters**:
- `message` (str): Reminder message (e.g., "Take vitamins")
- `time` (str): Time in HH:MM format (e.g., "09:00")
- `is_recurring` (bool): True for daily reminders
- `recurrence_pattern` (str, optional): Cron pattern for complex schedules

**Returns**:
```python
ReminderScheduleResult(
    success=True,
    message="Daily reminder set for 9:00 AM",
    reminder_time="09:00",
    reminder_message="Take vitamins"
)
```

**Example Usage**:
- "Remind me to take vitamins daily at 9am"
- "Set a one-time reminder to weigh myself tomorrow at 7am"

**Database**: `INSERT INTO reminders` + APScheduler job

---

### `get_user_reminders`

List all active reminders for the user.

```python
async def get_user_reminders(
    ctx: RunContext[AgentDeps]
) -> RemindersListResult
```

**Returns**:
```python
RemindersListResult(
    success=True,
    reminders=[
        {"id": "uuid-1", "message": "Take vitamins", "time": "09:00", "recurring": True},
        {"id": "uuid-2", "message": "Weigh yourself", "time": "07:00", "recurring": False}
    ]
)
```

**Example Usage**:
- "Show me my reminders"
- "What reminders do I have?"

---

### `delete_reminder`

Delete a scheduled reminder.

```python
async def delete_reminder(
    ctx: RunContext[AgentDeps],
    reminder_id: str
) -> ReminderOperationResult
```

**Parameters**:
- `reminder_id` (str): UUID of the reminder to delete

**Returns**:
```python
ReminderOperationResult(
    success=True,
    message="Reminder deleted",
    reminder_id="uuid-123"
)
```

**Example Usage**:
- "Delete my vitamin reminder"
- "Remove the 9am reminder"

---

## 5. Gamification Tools

### `get_xp_status`

Get current XP, level, and tier information.

```python
async def get_xp_status(
    ctx: RunContext[AgentDeps]
) -> XPStatusResult
```

**Returns**:
```python
XPStatusResult(
    current_xp=450,
    level=3,
    tier="Bronze",
    xp_for_next_level=900,
    xp_progress_percent=50.0
)
```

**Example Usage**:
- "What's my level?"
- "How much XP do I have?"

**Database**: `SELECT * FROM user_xp WHERE user_id = ?`

---

### `get_streaks`

Get current and best streaks across all activities.

```python
async def get_streaks(
    ctx: RunContext[AgentDeps]
) -> StreakStatusResult
```

**Returns**:
```python
StreakStatusResult(
    daily_logging_streak=7,
    food_logging_streak=5,
    reminder_completion_streak=10,
    best_streak_ever=15
)
```

**Example Usage**:
- "What's my streak?"
- "Show me my current streaks"

**Database**: `SELECT * FROM user_streaks WHERE user_id = ?`

---

### `browse_challenges`

View available challenges to start.

```python
async def browse_challenges(
    ctx: RunContext[AgentDeps],
    difficulty: Optional[str] = None
) -> str
```

**Parameters**:
- `difficulty` (str, optional): Filter by difficulty ("easy", "medium", "hard")

**Returns**: Markdown-formatted list of challenges

**Example Usage**:
- "What challenges are available?"
- "Show me easy challenges"

**Database**: `SELECT * FROM challenges WHERE difficulty = ?`

---

### `start_challenge`

Begin a new challenge.

```python
async def start_challenge(
    ctx: RunContext[AgentDeps],
    challenge_name: str
) -> str
```

**Parameters**:
- `challenge_name` (str): Name of the challenge to start

**Returns**: Confirmation message with challenge details

**Example Usage**:
- "Start the 30-day protein challenge"
- "I want to do the daily water intake challenge"

**Database**: `INSERT INTO user_challenges`

---

## 6. Memory & Facts Tools

### `remember_fact`

Store an important fact about the user for long-term memory.

```python
async def remember_fact(
    ctx: RunContext[AgentDeps],
    fact: str,
    category: str = "general"
) -> MemoryResult
```

**Parameters**:
- `fact` (str): The fact to remember (e.g., "User is allergic to peanuts")
- `category` (str): Category for organization

**Returns**:
```python
MemoryResult(
    success=True,
    message="Fact remembered",
    fact_id="uuid-123"
)
```

**Example Usage**:
- User says: "I'm allergic to peanuts"
- Agent calls: `remember_fact(fact="User is allergic to peanuts", category="health")`

**Storage**: Mem0 (semantic memory with embeddings)

---

### `save_user_info`

Save structured user information to profile.

```python
async def save_user_info(
    ctx: RunContext[AgentDeps],
    info_type: str,
    info_value: str
) -> UserInfoResult
```

**Parameters**:
- `info_type` (str): Type of information (e.g., "dietary_restriction", "medical_condition")
- `info_value` (str): The information to save

**Example Usage**:
- "I'm vegetarian"
- "I have type 2 diabetes"

**File Modified**: `production/data/{telegram_id}/profile.md`

---

## 7. Dynamic Tools (Advanced)

### `create_dynamic_tool`

Create a custom tool at runtime based on user needs.

```python
async def create_dynamic_tool(
    ctx: RunContext[AgentDeps],
    tool_name: str,
    tool_description: str,
    parameters: list[dict],
    code: str
) -> DynamicToolResult
```

**Parameters**:
- `tool_name` (str): Name of the new tool
- `tool_description` (str): What the tool does
- `parameters` (list): Tool parameters with types
- `code` (str): Python code for the tool

**Security**:
- ⚠️ Code is validated before execution (sandboxed)
- ⚠️ User approval required for tools that modify data
- ⚠️ Limited to safe operations (no file system access, no network calls)

**Returns**:
```python
DynamicToolResult(
    success=True,
    message="Tool 'track_water' created",
    tool_name="track_water",
    requires_approval=True,
    approval_request_id="uuid-123"
)
```

**Example Usage**:
- User: "I want to track my water intake"
- Agent creates a custom `track_water()` tool dynamically

**Storage**: `INSERT INTO dynamic_tools` + runtime tool registration

---

## Tool Call Format

When the agent decides to call a tool, it generates a structured tool call:

```json
{
  "tool_name": "save_food_entry",
  "parameters": {
    "foods": [
      {"name": "chicken breast", "amount": "200g"},
      {"name": "brown rice", "amount": "150g"}
    ],
    "calories": 450,
    "protein": 30.5,
    "carbs": 45.0,
    "fat": 8.0
  }
}
```

PydanticAI executes the tool and returns the result to the agent, which then generates a natural language response to the user.

---

## Error Handling

All tools return structured results with `success` boolean:

```python
# Success
ProfileUpdateResult(success=True, message="Age updated", field="age", value="32")

# Failure
ProfileUpdateResult(success=False, message="Invalid age value", field="age", value="invalid")
```

The agent interprets the result and communicates errors naturally:
- ✅ Success: "I've updated your age to 32"
- ❌ Failure: "Sorry, I couldn't update your age - please provide a valid number"

---

## Tool Approval System

Some tools (especially dynamic tools and data modifications) require user approval:

1. Agent calls tool that requires approval
2. Tool creates `approval_request` in database
3. User receives approval prompt via Telegram
4. User approves/rejects
5. Tool executes (if approved)

**Tools requiring approval**:
- `create_dynamic_tool` (security risk)
- `update_food_entry_tool` (data modification)
- `delete_reminder` (data deletion)

---

## Testing Tools via API

All tools can be tested programmatically via the REST API in `RUN_MODE=api`:

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test_key_123" \
  -d '{
    "user_id": "test_user",
    "message": "What is my XP level?"
  }'
```

The API response includes:
- Agent's natural language response
- Tool calls made (for debugging)
- Tool results (for validation)

---

## Related Documentation

- **ADR-001**: PydanticAI framework decision and rationale
- **Component Diagram**: `/docs/architecture/component-diagram.md` - Agent architecture overview
- **Database Schema**: `/docs/api/database-schema.md` - Tables used by tools
- **REST API Reference**: `/API_README.md` - HTTP endpoints that wrap agent functionality

## Revision History

- 2025-01-18: Initial agent interface documentation created for Phase 3.7
