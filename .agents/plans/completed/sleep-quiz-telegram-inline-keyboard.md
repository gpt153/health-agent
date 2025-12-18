# Feature: Sleep Quiz for Telegram Bot with Inline Keyboards

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Implement a fast, mobile-optimized sleep quiz that users can complete in 60-90 seconds using Telegram inline keyboards. The quiz collects sleep data from the previous night including timing, quality, disruptions, phone usage, and current alertness. All questions use buttons, time pickers, and sliders to minimize typing.

The quiz is designed specifically for teenage boys (15+ years) based on validated sleep assessment instruments (PSQI, ASHS) and research on adolescent sleep patterns.

## User Story

As a health-conscious teenager
I want to quickly log my sleep quality each morning
So that I can track patterns and improve my sleep habits without spending more than 90 seconds

## Problem Statement

Current system lacks sleep tracking capabilities. Manual text-based logging is too slow and cumbersome for daily use. Research shows that:
- 77% of users abandon apps within 3 days if onboarding/daily tasks take too long
- Teenagers specifically need fast, mobile-optimized interfaces (<90 seconds completion time)
- Screen time is a critical factor affecting teenage sleep quality (needs tracking)
- Validated sleep assessment frameworks (PSQI) require specific metrics that aren't currently captured

## Solution Statement

Build an 8-question Telegram-native sleep quiz using ConversationHandler with inline keyboard buttons for all inputs. Quiz uses:
- Time pickers (inline buttons with hour/minute selection)
- Button grids (1-10 quality ratings)
- Toggle buttons (yes/no questions)
- Multi-select buttons (disruptions)
- Conditional follow-ups (phone usage duration)

Data saved to PostgreSQL for trend analysis and coaching insights.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**:
- Handlers (new sleep_quiz.py)
- Database (new sleep_entries table)
- Models (new sleep.py)
- Bot (new conversation handler registration)

**Dependencies**:
- python-telegram-bot v22.5+
- PostgreSQL (existing connection pool)
- Existing timezone support

---

## CONTEXT REFERENCES

### Relevant Codebase Files - IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

**Existing Handler Patterns:**
- `src/handlers/onboarding.py` (lines 1-589) - Why: Shows ConversationHandler pattern, state management, inline keyboard usage
- `src/handlers/food_photo.py` - Why: Shows message handling and database save patterns
- `src/bot.py` (lines 987-1023) - Why: Shows handler registration pattern in create_bot_application()

**Database Patterns:**
- `src/db/queries.py` (lines 40-63) - Why: Shows async database save pattern to mirror
- `src/db/connection.py` - Why: Connection pool usage pattern
- `migrations/001_initial_schema.sql` - Why: Database migration structure and patterns

**Model Patterns:**
- `src/models/food.py` - Why: Shows Pydantic model structure for data entries
- `src/models/onboarding.py` - Why: Shows enum and state model patterns
- `src/models/reminder.py` - Why: Shows model with JSONB schedule field pattern

**Utility Patterns:**
- `src/utils/timezone_helper.py` - Why: Timezone conversion for sleep timing calculations
- `src/utils/auth.py` - Why: User authorization pattern

### New Files to Create

- `src/handlers/sleep_quiz.py` - ConversationHandler with all quiz logic
- `src/models/sleep.py` - SleepEntry Pydantic model
- `migrations/005_sleep_tracking.sql` - Database schema for sleep entries
- `tests/integration/test_sleep_quiz_flow.py` - Integration tests for full quiz flow
- `tests/unit/test_sleep_models.py` - Unit tests for sleep data models

### Relevant Documentation - YOU SHOULD READ THESE BEFORE IMPLEMENTING!

**Research Documents (In Repository):**
- `telegram-sleep-quiz-implementation.md` (All lines) - **CRITICAL**: Complete implementation guide with code examples
  - Specific section: Buttons, Multi-Select, Sliders, Time Pickers (lines 33-326)
  - Specific section: Conversation State Management (lines 373-418)
  - Specific section: Recommended Questions (lines 80-145)
  - Why: Contains exact button layouts, callback patterns, and UX best practices

- `sleep-quiz-research.md` (All lines) - Why: Validated sleep assessment questions and research backing
  - Specific section: Recommended Questions for 15-Year-Old (lines 81-145)
  - Specific section: Question Grouping & Flow (lines 147-169)
  - Why: Evidence-based question selection and clinical thresholds

**python-telegram-bot Documentation:**
- [ConversationHandler docs](https://docs.python-telegram-bot.org/en/stable/telegram.ext.conversationhandler.html) - Specific section: States and transitions
- [InlineKeyboardButton example](https://github.com/python-telegram-bot/python-telegram-bot/blob/master/examples/inlinekeyboard.py) - Why: Pattern for button callbacks
- [CallbackQueryHandler docs](https://docs.python-telegram-bot.org/en/stable/telegram.ext.callbackqueryhandler.html) - Why: Handling button clicks

### Patterns to Follow

**Naming Conventions:**
```python
# State constants: UPPERCASE with underscores
BEDTIME, SLEEP_LATENCY, WAKE_TIME = range(8)

# Callback data: lowercase with underscores, max 64 bytes
callback_data="latency_0-15"  # Not "sleep_latency_less_than_15_minutes"

# Function names: snake_case, descriptive verb
async def show_bedtime_picker(update, context):
    pass
```

**Error Handling:**
```python
# From src/handlers/onboarding.py:523
try:
    await operation()
    logger.info(f"Success: {user_id}")
except Exception as e:
    logger.error(f"Failed: {e}", exc_info=True)
    await update.message.reply_text("Sorry, something went wrong!")
```

**Logging Pattern:**
```python
# From src/handlers/onboarding.py:100
logger.info(f"User {user_id} selected path: {path}")

# From src/db/queries.py:26
logger.info(f"Created user: {telegram_id}")
```

**Inline Keyboard Pattern (FROM telegram-sleep-quiz-implementation.md:42-73):**
```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

keyboard = [
    [InlineKeyboardButton("Option 1", callback_data="option_1")],
    [InlineKeyboardButton("Option 2", callback_data="option_2")],
]
reply_markup = InlineKeyboardMarkup(keyboard)

await update.message.reply_text("Question?", reply_markup=reply_markup)

# Handle callback
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # CRITICAL: Remove loading animation

    # Parse callback_data
    data = query.data

    # Update message to show selection
    await query.edit_message_text(text=f"✅ Selected: {data}")
```

**Database Save Pattern:**
```python
# From src/db/queries.py:41-63
async def save_food_entry(entry: FoodEntry) -> None:
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO table_name (columns) VALUES (%s, %s)""",
                (value1, value2)
            )
            await conn.commit()
    logger.info(f"Saved entry for user {entry.user_id}")
```

**Context.user_data for State (FROM telegram-sleep-quiz-implementation.md:88-142):**
```python
# Store temporary quiz data
if 'sleep_quiz_data' not in context.user_data:
    context.user_data['sleep_quiz_data'] = {}

context.user_data['sleep_quiz_data']['bedtime'] = "22:00"

# Retrieve later
bedtime = context.user_data['sleep_quiz_data'].get('bedtime')
```

---

## IMPLEMENTATION PLAN

### Phase 1: Database Foundation

Set up database schema and connection patterns before any handler logic.

**Tasks:**
- Create migration file with sleep_entries table
- Add database query functions for sleep data
- Create Pydantic models for sleep entries

### Phase 2: Core Quiz Logic

Implement ConversationHandler with all 8 questions using inline keyboards.

**Tasks:**
- Create sleep_quiz handler file
- Implement state machine with 8 states
- Build inline keyboard layouts for each question
- Add callback handlers for button clicks

### Phase 3: Time Picker Implementation

Custom time picker using inline buttons (no typing required).

**Tasks:**
- Build hour/minute picker UI
- Handle increment/decrement callbacks
- Validate time inputs
- Calculate sleep duration

### Phase 4: Integration & Testing

Connect to bot, add feature discovery, test full flow.

**Tasks:**
- Register handler in bot.py
- Add feature discovery tracking
- Write integration tests
- Manual testing checklist

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE migrations/005_sleep_tracking.sql

- **IMPLEMENT**: Complete database schema for sleep_entries table
- **PATTERN**: Mirror structure from migrations/001_initial_schema.sql:10-73
- **IMPORTS**: None (SQL file)
- **SCHEMA FIELDS**:
  ```sql
  - id UUID PRIMARY KEY DEFAULT gen_random_uuid()
  - user_id VARCHAR(255) REFERENCES users(telegram_id) ON DELETE CASCADE
  - logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  - bedtime TIME NOT NULL
  - sleep_latency_minutes INTEGER NOT NULL
  - wake_time TIME NOT NULL
  - total_sleep_hours FLOAT NOT NULL
  - night_wakings INTEGER NOT NULL
  - sleep_quality_rating INTEGER CHECK (1-10)
  - disruptions JSONB
  - phone_usage BOOLEAN NOT NULL
  - phone_duration_minutes INTEGER
  - alertness_rating INTEGER CHECK (1-10)
  ```
- **INDEXES**: Add index on (user_id, logged_at DESC) for query performance
- **GOTCHA**: Use TIME type for bedtime/wake_time, not TIMESTAMP
- **VALIDATE**: `PGPASSWORD=postgres psql -h localhost -U postgres -d health_agent -f migrations/005_sleep_tracking.sql`

### CREATE src/models/sleep.py

- **IMPLEMENT**: Pydantic models for SleepEntry with validation
- **PATTERN**: Mirror src/models/food.py:1-45 structure
- **IMPORTS**:
  ```python
  from pydantic import BaseModel, Field, field_validator
  from datetime import datetime, time
  from typing import Optional, List
  ```
- **MODELS**:
  ```python
  class SleepEntry(BaseModel):
      id: str
      user_id: str
      logged_at: datetime
      bedtime: time
      sleep_latency_minutes: int = Field(ge=0, le=300)  # 0-5 hours max
      wake_time: time
      total_sleep_hours: float = Field(ge=0, le=24)
      night_wakings: int = Field(ge=0, le=20)
      sleep_quality_rating: int = Field(ge=1, le=10)
      disruptions: List[str] = Field(default_factory=list)
      phone_usage: bool
      phone_duration_minutes: Optional[int] = Field(None, ge=0, le=480)
      alertness_rating: int = Field(ge=1, le=10)
  ```
- **GOTCHA**: Use time type (not datetime) for bedtime/wake_time
- **VALIDATE**: `python -c "from src.models.sleep import SleepEntry; print('✓ Import successful')"`

### ADD sleep query functions to src/db/queries.py

- **IMPLEMENT**: async save_sleep_entry() and get_sleep_entries() functions
- **PATTERN**: Mirror save_food_entry pattern at src/db/queries.py:41-63
- **IMPORTS**: Add `from src.models.sleep import SleepEntry` at top
- **FUNCTIONS**:
  ```python
  async def save_sleep_entry(entry: SleepEntry) -> None:
      """Save sleep quiz entry to database"""
      async with db.connection() as conn:
          async with conn.cursor() as cur:
              await cur.execute(
                  """INSERT INTO sleep_entries (...) VALUES (...)""",
                  (entry.id, entry.user_id, entry.logged_at, ...)
              )
              await conn.commit()
      logger.info(f"Saved sleep entry for {entry.user_id}")

  async def get_sleep_entries(user_id: str, days: int = 7) -> list[dict]:
      """Get recent sleep entries for user"""
      # Query sleep_entries WHERE user_id AND logged_at > now() - days
      # ORDER BY logged_at DESC
  ```
- **GOTCHA**: Convert time objects to strings for psycopg: `str(entry.bedtime)`
- **GOTCHA**: Convert list to JSON: `json.dumps(entry.disruptions)`
- **VALIDATE**: `python -c "from src.db.queries import save_sleep_entry; print('✓')"`

### CREATE src/handlers/sleep_quiz.py - Part 1: Imports and States

- **IMPLEMENT**: File structure, imports, state constants
- **PATTERN**: Mirror src/handlers/onboarding.py:1-20
- **IMPORTS**:
  ```python
  import logging
  from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
  from telegram.ext import (
      ConversationHandler, CommandHandler, CallbackQueryHandler, ContextTypes
  )
  from src.db.queries import save_sleep_entry, get_sleep_entries
  from src.models.sleep import SleepEntry
  from src.utils.auth import is_authorized
  from datetime import datetime, time as time_type
  from uuid import uuid4
  import json

  logger = logging.getLogger(__name__)
  ```
- **STATE CONSTANTS**:
  ```python
  # Define conversation states
  BEDTIME, SLEEP_LATENCY, WAKE_TIME, NIGHT_WAKINGS = range(4)
  QUALITY, PHONE, DISRUPTIONS, ALERTNESS = range(4, 8)
  ```
- **VALIDATE**: `python -c "from src.handlers.sleep_quiz import *; print('✓')"`

### IMPLEMENT start_sleep_quiz() entry point

- **IMPLEMENT**: Quiz entry point, authorization check, welcome message
- **PATTERN**: Mirror src/handlers/onboarding.py:21-60
- **CODE**:
  ```python
  async def start_sleep_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
      """Entry point for sleep quiz"""
      user_id = str(update.effective_user.id)

      # Check authorization
      if not await is_authorized(user_id):
          return ConversationHandler.END

      # Initialize quiz data storage
      context.user_data['sleep_quiz_data'] = {}

      message = (
          "😴 **Good morning! Let's log your sleep**\n\n"
          "This takes about 60 seconds.\n\n"
          "Ready? Let's start!"
      )

      await update.message.reply_text(message, parse_mode="Markdown")

      # Show first question immediately
      return await show_bedtime_question(update, context)
  ```
- **GOTCHA**: Must return state constant (BEDTIME) to transition conversation
- **VALIDATE**: Function compiles without syntax errors

### IMPLEMENT show_bedtime_question() - Time Picker UI

- **IMPLEMENT**: Custom time picker using inline keyboard buttons
- **PATTERN**: FROM telegram-sleep-quiz-implementation.md:239-290
- **CODE**:
  ```python
  async def show_bedtime_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
      """Show bedtime question with time picker"""
      user_id = str(update.effective_user.id)

      # Default to 10 PM if no prior data
      hour = context.user_data['sleep_quiz_data'].get('bedtime_hour', 22)
      minute = context.user_data['sleep_quiz_data'].get('bedtime_minute', 0)

      keyboard = [
          [
              InlineKeyboardButton("🔼", callback_data="bed_h_up"),
              InlineKeyboardButton("", callback_data="noop"),
              InlineKeyboardButton("🔼", callback_data="bed_m_up"),
          ],
          [
              InlineKeyboardButton(f"{hour:02d}", callback_data="noop"),
              InlineKeyboardButton(":", callback_data="noop"),
              InlineKeyboardButton(f"{minute:02d}", callback_data="noop"),
          ],
          [
              InlineKeyboardButton("🔽", callback_data="bed_h_down"),
              InlineKeyboardButton("", callback_data="noop"),
              InlineKeyboardButton("🔽", callback_data="bed_m_down"),
          ],
          [InlineKeyboardButton("✅ Confirm", callback_data="bed_confirm")],
      ]
      reply_markup = InlineKeyboardMarkup(keyboard)

      text = "**Q1/8: What time did you get into bed?**\n\nUse ⬆️⬇️ to adjust time"

      if update.callback_query:
          await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
      else:
          await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

      return BEDTIME
  ```
- **GOTCHA**: Check if update.callback_query exists (subsequent calls) vs update.message (first call)
- **GOTCHA**: Time picker increments: hours by 1 (0-23), minutes by 15 (0/15/30/45)
- **VALIDATE**: Function compiles

### IMPLEMENT handle_bedtime_callback() - Time Picker Logic

- **IMPLEMENT**: Handle time picker button clicks (up/down/confirm)
- **PATTERN**: FROM telegram-sleep-quiz-implementation.md:267-290
- **CODE**:
  ```python
  async def handle_bedtime_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
      """Handle bedtime time picker callbacks"""
      query = update.callback_query
      await query.answer()  # CRITICAL: Remove loading spinner

      data = query.data
      hour = context.user_data['sleep_quiz_data'].get('bedtime_hour', 22)
      minute = context.user_data['sleep_quiz_data'].get('bedtime_minute', 0)

      if data == "bed_h_up":
          hour = (hour + 1) % 24
      elif data == "bed_h_down":
          hour = (hour - 1) % 24
      elif data == "bed_m_up":
          minute = (minute + 15) % 60
      elif data == "bed_m_down":
          minute = (minute - 15) % 60
      elif data == "bed_confirm":
          # Save bedtime and move to next question
          context.user_data['sleep_quiz_data']['bedtime'] = f"{hour:02d}:{minute:02d}"
          return await show_sleep_latency_question(update, context)
      elif data == "noop":
          # No-op buttons (display only)
          return BEDTIME

      # Update stored values
      context.user_data['sleep_quiz_data']['bedtime_hour'] = hour
      context.user_data['sleep_quiz_data']['bedtime_minute'] = minute

      # Rebuild picker with new values
      return await show_bedtime_question(update, context)
  ```
- **GOTCHA**: ALWAYS call query.answer() first to remove loading animation
- **GOTCHA**: Use modulo (%) for wrapping hour (0-23) and minute (0-45-30-15-0)
- **VALIDATE**: Test hour/minute increment/decrement logic with edge cases

### IMPLEMENT show_sleep_latency_question()

- **IMPLEMENT**: Sleep latency question with 4 button options
- **PATTERN**: FROM telegram-sleep-quiz-implementation.md:42-73
- **CODE**:
  ```python
  async def show_sleep_latency_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
      """Q2: How long to fall asleep?"""
      keyboard = [
          [InlineKeyboardButton("Less than 15 min", callback_data="latency_0")],
          [InlineKeyboardButton("15-30 min", callback_data="latency_15")],
          [InlineKeyboardButton("30-60 min", callback_data="latency_45")],
          [InlineKeyboardButton("More than 1 hour", callback_data="latency_90")],
      ]
      reply_markup = InlineKeyboardMarkup(keyboard)

      text = "**Q2/8: How long did it take you to fall asleep?**"
      await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

      return SLEEP_LATENCY
  ```
- **GOTCHA**: Callback_data encodes midpoint values (0, 15, 45, 90 minutes)
- **VALIDATE**: Function compiles

### IMPLEMENT handle_sleep_latency_callback()

- **IMPLEMENT**: Save selected latency, show next question
- **CODE**:
  ```python
  async def handle_sleep_latency_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
      """Handle sleep latency selection"""
      query = update.callback_query
      await query.answer()

      # Parse latency from callback_data
      latency_str = query.data.replace("latency_", "")
      latency_minutes = int(latency_str)

      context.user_data['sleep_quiz_data']['sleep_latency_minutes'] = latency_minutes

      # Confirm selection
      await query.edit_message_text(f"✅ Sleep latency: {latency_minutes} minutes")

      return await show_wake_time_question(update, context)
  ```
- **VALIDATE**: Function compiles

### IMPLEMENT show_wake_time_question() - Time Picker #2

- **IMPLEMENT**: Wake time picker (same pattern as bedtime)
- **PATTERN**: Reuse bedtime picker logic, different callbacks
- **CODE**: Same structure as show_bedtime_question() but:
  - Default hour: 7 AM
  - Callback prefixes: "wake_h_up", "wake_m_up", "wake_confirm"
  - Text: "Q3/8: What time did you wake up this morning?"
- **GOTCHA**: Don't forget to update callback_data prefixes to "wake_" not "bed_"
- **VALIDATE**: Function compiles

### IMPLEMENT handle_wake_time_callback()

- **IMPLEMENT**: Wake time picker callbacks
- **PATTERN**: Mirror handle_bedtime_callback logic
- **CODE**: Same logic but store to 'wake_time' key, different callback prefix "wake_"
- **VALIDATE**: Function compiles

### IMPLEMENT show_night_wakings_question()

- **IMPLEMENT**: Night wakings with 3 button options
- **CODE**:
  ```python
  keyboard = [
      [InlineKeyboardButton("No", callback_data="wakings_0")],
      [InlineKeyboardButton("Yes, 1-2 times", callback_data="wakings_1")],
      [InlineKeyboardButton("Yes, 3+ times", callback_data="wakings_3")],
  ]
  text = "**Q4/8: Did you wake up during the night?**"
  ```
- **VALIDATE**: Function compiles

### IMPLEMENT handle_night_wakings_callback()

- **IMPLEMENT**: Save waking count, advance
- **CODE**: Parse "wakings_0" → 0, "wakings_1" → 2 (midpoint), "wakings_3" → 4 (estimate)
- **VALIDATE**: Function compiles

### IMPLEMENT show_quality_rating_question() - Slider (Button Grid)

- **IMPLEMENT**: Quality rating using 2-row button grid (1-10)
- **PATTERN**: FROM telegram-sleep-quiz-implementation.md:154-169
- **CODE**:
  ```python
  keyboard = [
      [InlineKeyboardButton(str(i), callback_data=f"quality_{i}") for i in range(1, 6)],
      [InlineKeyboardButton(str(i), callback_data=f"quality_{i}") for i in range(6, 11)],
  ]
  text = (
      "**Q5/8: How would you rate your sleep quality?**\n\n"
      "😫 1-2 = Terrible\n"
      "😐 5-6 = Okay\n"
      "😊 9-10 = Excellent"
  )
  ```
- **GOTCHA**: Button grid more user-friendly than incremental slider for mobile
- **VALIDATE**: Function compiles

### IMPLEMENT handle_quality_rating_callback()

- **IMPLEMENT**: Save quality rating (1-10)
- **CODE**: Parse "quality_7" → 7, store to 'sleep_quality_rating'
- **VALIDATE**: Function compiles

### IMPLEMENT show_phone_usage_question()

- **IMPLEMENT**: Phone usage toggle (Yes/No)
- **CODE**:
  ```python
  keyboard = [
      [
          InlineKeyboardButton("✅ Yes", callback_data="phone_yes"),
          InlineKeyboardButton("❌ No", callback_data="phone_no"),
      ],
  ]
  text = "**Q6/8: Did you use your phone/screen while in bed?**"
  ```
- **VALIDATE**: Function compiles

### IMPLEMENT handle_phone_usage_callback() - Conditional Follow-up

- **IMPLEMENT**: If yes, show duration question; if no, skip to disruptions
- **PATTERN**: FROM telegram-sleep-quiz-implementation.md:348-370
- **CODE**:
  ```python
  query = update.callback_query
  await query.answer()

  if query.data == "phone_yes":
      context.user_data['sleep_quiz_data']['phone_usage'] = True
      # Show follow-up duration question
      keyboard = [
          [InlineKeyboardButton("< 15 min", callback_data="phone_dur_7")],
          [InlineKeyboardButton("15-30 min", callback_data="phone_dur_22")],
          [InlineKeyboardButton("30-60 min", callback_data="phone_dur_45")],
          [InlineKeyboardButton("1+ hour", callback_data="phone_dur_90")],
      ]
      text = "**For how long?**"
      await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
      return PHONE
  else:
      context.user_data['sleep_quiz_data']['phone_usage'] = False
      context.user_data['sleep_quiz_data']['phone_duration_minutes'] = 0
      await query.edit_message_text("✅ Noted: No phone usage")
      return await show_disruptions_question(update, context)
  ```
- **GOTCHA**: Conditional state transition - phone_yes stays in PHONE state, phone_no jumps to DISRUPTIONS
- **VALIDATE**: Test both branches

### IMPLEMENT handle_phone_duration_callback()

- **IMPLEMENT**: Save phone duration if user selected yes
- **CODE**: Parse "phone_dur_22" → 22 minutes, store to 'phone_duration_minutes'
- **VALIDATE**: Function compiles

### IMPLEMENT show_disruptions_question() - Multi-Select

- **IMPLEMENT**: Disruptions multi-select with checkmarks
- **PATTERN**: FROM telegram-sleep-quiz-implementation.md:84-142
- **CODE**:
  ```python
  # Initialize selections set if not exists
  if 'disruptions_selected' not in context.user_data['sleep_quiz_data']:
      context.user_data['sleep_quiz_data']['disruptions_selected'] = set()

  selected = context.user_data['sleep_quiz_data']['disruptions_selected']

  keyboard = [
      [InlineKeyboardButton(
          f"{'✅ ' if 'noise' in selected else ''}🔊 Noise",
          callback_data="disrupt_noise"
      )],
      [InlineKeyboardButton(
          f"{'✅ ' if 'light' in selected else ''}💡 Light",
          callback_data="disrupt_light"
      )],
      [InlineKeyboardButton(
          f"{'✅ ' if 'temp' in selected else ''}🌡️ Temperature",
          callback_data="disrupt_temp"
      )],
      [InlineKeyboardButton(
          f"{'✅ ' if 'stress' in selected else ''}😰 Stress/worry",
          callback_data="disrupt_stress"
      )],
      [InlineKeyboardButton(
          f"{'✅ ' if 'dream' in selected else ''}😱 Bad dream",
          callback_data="disrupt_dream"
      )],
      [InlineKeyboardButton(
          f"{'✅ ' if 'pain' in selected else ''}🤕 Pain",
          callback_data="disrupt_pain"
      )],
      [InlineKeyboardButton("✅ Done", callback_data="disrupt_done")],
  ]
  text = "**Q7/8: What disrupted your sleep?** (Select all that apply)"
  ```
- **GOTCHA**: Must rebuild keyboard on every callback to update checkmarks
- **VALIDATE**: Function compiles

### IMPLEMENT handle_disruptions_callback()

- **IMPLEMENT**: Toggle selections, rebuild keyboard until "Done"
- **CODE**:
  ```python
  query = update.callback_query
  await query.answer()

  if query.data == "disrupt_done":
      # Save disruptions list and advance
      selected = context.user_data['sleep_quiz_data']['disruptions_selected']
      context.user_data['sleep_quiz_data']['disruptions'] = list(selected)
      return await show_alertness_question(update, context)
  else:
      # Toggle selection
      disruption = query.data.replace("disrupt_", "")
      selected = context.user_data['sleep_quiz_data']['disruptions_selected']

      if disruption in selected:
          selected.remove(disruption)
      else:
          selected.add(disruption)

      # Rebuild keyboard with updated checkmarks
      return await show_disruptions_question(update, context)
  ```
- **GOTCHA**: Set operations for toggle (add if not exists, remove if exists)
- **VALIDATE**: Test multi-select toggle logic

### IMPLEMENT show_alertness_question() - Final Question

- **IMPLEMENT**: Alertness rating (1-10 button grid)
- **CODE**: Same pattern as quality rating
  ```python
  keyboard = [
      [InlineKeyboardButton(str(i), callback_data=f"alert_{i}") for i in range(1, 6)],
      [InlineKeyboardButton(str(i), callback_data=f"alert_{i}") for i in range(6, 11)],
  ]
  text = (
      "**Q8/8: How tired/alert do you feel RIGHT NOW?**\n\n"
      "😴 1-2 = Exhausted\n"
      "😐 5-6 = Normal\n"
      "⚡ 9-10 = Wide awake"
  )
  ```
- **VALIDATE**: Function compiles

### IMPLEMENT handle_alertness_callback() - Save & Complete

- **IMPLEMENT**: Save alertness, calculate totals, save to database, show summary
- **CODE**:
  ```python
  query = update.callback_query
  await query.answer()

  alertness = int(query.data.replace("alert_", ""))
  context.user_data['sleep_quiz_data']['alertness_rating'] = alertness

  # Calculate total sleep duration
  quiz_data = context.user_data['sleep_quiz_data']
  bedtime_str = quiz_data['bedtime']  # "22:00"
  wake_str = quiz_data['wake_time']  # "07:00"
  latency = quiz_data['sleep_latency_minutes']

  # Parse times
  bed_hour, bed_min = map(int, bedtime_str.split(':'))
  wake_hour, wake_min = map(int, wake_str.split(':'))

  # Calculate duration (handle overnight)
  bed_total_min = bed_hour * 60 + bed_min
  wake_total_min = wake_hour * 60 + wake_min
  if wake_total_min < bed_total_min:
      wake_total_min += 24 * 60  # Add 24 hours

  sleep_minutes = wake_total_min - bed_total_min - latency
  total_sleep_hours = sleep_minutes / 60.0

  # Create SleepEntry
  from src.models.sleep import SleepEntry
  from datetime import time as time_type

  entry = SleepEntry(
      id=str(uuid4()),
      user_id=str(update.effective_user.id),
      logged_at=datetime.now(),
      bedtime=time_type(bed_hour, bed_min),
      sleep_latency_minutes=latency,
      wake_time=time_type(wake_hour, wake_min),
      total_sleep_hours=round(total_sleep_hours, 2),
      night_wakings=quiz_data.get('night_wakings', 0),
      sleep_quality_rating=quiz_data['sleep_quality_rating'],
      disruptions=quiz_data.get('disruptions', []),
      phone_usage=quiz_data['phone_usage'],
      phone_duration_minutes=quiz_data.get('phone_duration_minutes'),
      alertness_rating=alertness
  )

  # Save to database
  await save_sleep_entry(entry)

  # Log feature usage
  from src.db.queries import log_feature_usage
  await log_feature_usage(entry.user_id, "sleep_tracking")

  # Show summary
  hours = int(total_sleep_hours)
  minutes = int((total_sleep_hours % 1) * 60)
  quality_emoji = "😊" if entry.sleep_quality_rating >= 8 else "😐" if entry.sleep_quality_rating >= 5 else "😫"

  summary = f"""✅ **Sleep Logged!**

🛏️ **Bedtime:** {bedtime_str}
😴 **Fell asleep:** {latency} min
⏰ **Woke up:** {wake_str}
⏱️ **Total sleep:** {hours}h {minutes}m

🌙 **Quality:** {quality_emoji} {entry.sleep_quality_rating}/10
📱 **Phone usage:** {"Yes" if entry.phone_usage else "No"}
😌 **Alertness:** {alertness}/10

💡 **Tip:** You got {hours}h {minutes}m of sleep. Aim for 8-10h for optimal health!

[📊 View Week] [📈 See Trends]"""

  await query.edit_message_text(summary, parse_mode="Markdown")

  # Clean up quiz data
  del context.user_data['sleep_quiz_data']

  logger.info(f"Sleep quiz completed for user {entry.user_id}")

  return ConversationHandler.END
  ```
- **GOTCHA**: Handle overnight sleep (wake_time < bedtime) by adding 24 hours
- **GOTCHA**: Convert time strings to time_type objects for Pydantic model
- **GOTCHA**: Return ConversationHandler.END to exit conversation
- **VALIDATE**: Test sleep duration calculation with various bedtime/wake combinations

### CREATE ConversationHandler and cancel function

- **IMPLEMENT**: Build ConversationHandler with all states and fallback
- **PATTERN**: FROM telegram-sleep-quiz-implementation.md:401-414
- **CODE**:
  ```python
  async def cancel_sleep_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
      """Cancel the sleep quiz"""
      await update.message.reply_text("Sleep quiz cancelled. You can start again with /sleep_quiz")
      if 'sleep_quiz_data' in context.user_data:
          del context.user_data['sleep_quiz_data']
      return ConversationHandler.END

  # Build conversation handler
  sleep_quiz_handler = ConversationHandler(
      entry_points=[CommandHandler('sleep_quiz', start_sleep_quiz)],
      states={
          BEDTIME: [CallbackQueryHandler(handle_bedtime_callback)],
          SLEEP_LATENCY: [CallbackQueryHandler(handle_sleep_latency_callback)],
          WAKE_TIME: [CallbackQueryHandler(handle_wake_time_callback)],
          NIGHT_WAKINGS: [CallbackQueryHandler(handle_night_wakings_callback)],
          QUALITY: [CallbackQueryHandler(handle_quality_rating_callback)],
          PHONE: [CallbackQueryHandler(handle_phone_duration_callback, pattern="^phone_dur_")],
          DISRUPTIONS: [CallbackQueryHandler(handle_disruptions_callback)],
          ALERTNESS: [CallbackQueryHandler(handle_alertness_callback)],
      },
      fallbacks=[CommandHandler('cancel', cancel_sleep_quiz)],
  )
  ```
- **GOTCHA**: PHONE state has conditional logic - phone_yes handler triggers duration Q, phone_no skips state
- **GOTCHA**: Pattern matching with pattern="^phone_dur_" ensures only duration callbacks handled in PHONE state
- **VALIDATE**: Import and verify handler structure

### UPDATE src/bot.py to register sleep_quiz_handler

- **IMPLEMENT**: Add import and handler registration
- **PATTERN**: src/bot.py:1025-1053
- **IMPORTS**: Add `from src.handlers.sleep_quiz import sleep_quiz_handler` at top
- **REGISTRATION**: Add in create_bot_application():
  ```python
  # After line 1045 (after onboarding handlers)
  app.add_handler(sleep_quiz_handler)
  logger.info("Sleep quiz handler registered")
  ```
- **GOTCHA**: ConversationHandler must be added BEFORE MessageHandler (message handlers are catch-all)
- **VALIDATE**: `python -c "from src.bot import create_bot_application; print('✓')"`

### ADD log_feature_usage() if not exists

- **IMPLEMENT**: Feature usage tracking function in src/db/queries.py
- **PATTERN**: Mirror existing query patterns
- **CODE**:
  ```python
  async def log_feature_usage(user_id: str, feature_name: str) -> None:
      """Log feature usage for analytics"""
      async with db.connection() as conn:
          async with conn.cursor() as cur:
              # Check if feature_usage_log table exists, create if not
              # INSERT INTO feature_usage_log or UPDATE usage count
              pass  # Implement if table exists, otherwise skip for MVP
      logger.info(f"Logged feature usage: {user_id} used {feature_name}")
  ```
- **GOTCHA**: This may already exist - check before implementing
- **VALIDATE**: Grep for log_feature_usage in src/db/queries.py first

### RUN database migration

- **IMPLEMENT**: Execute migration to create sleep_entries table
- **VALIDATE**:
  ```bash
  PGPASSWORD=postgres psql -h localhost -U postgres -d health_agent -f migrations/005_sleep_tracking.sql

  # Verify table created
  PGPASSWORD=postgres psql -h localhost -U postgres -d health_agent -c "\d sleep_entries"
  ```
- **EXPECTED**: Table schema displayed with all columns

### CREATE tests/integration/test_sleep_quiz_flow.py

- **IMPLEMENT**: Integration test for full quiz flow
- **PATTERN**: tests/integration/test_food_workflow.py structure
- **IMPORTS**:
  ```python
  import pytest
  from datetime import datetime, time
  from src.db.queries import save_sleep_entry, get_sleep_entries
  from src.models.sleep import SleepEntry
  from uuid import uuid4
  ```
- **TESTS**:
  ```python
  @pytest.mark.asyncio
  async def test_save_and_retrieve_sleep_entry():
      """Test saving sleep entry to database"""
      entry = SleepEntry(
          id=str(uuid4()),
          user_id="test_user_123",
          logged_at=datetime.now(),
          bedtime=time(22, 0),
          sleep_latency_minutes=15,
          wake_time=time(7, 0),
          total_sleep_hours=8.75,
          night_wakings=0,
          sleep_quality_rating=8,
          disruptions=[],
          phone_usage=False,
          phone_duration_minutes=None,
          alertness_rating=7
      )

      await save_sleep_entry(entry)
      entries = await get_sleep_entries("test_user_123", days=1)

      assert len(entries) > 0
      assert entries[0]['sleep_quality_rating'] == 8
  ```
- **VALIDATE**: `pytest tests/integration/test_sleep_quiz_flow.py -v`

### CREATE tests/unit/test_sleep_models.py

- **IMPLEMENT**: Unit tests for SleepEntry validation
- **TESTS**:
  ```python
  from src.models.sleep import SleepEntry
  from datetime import datetime, time
  import pytest

  def test_sleep_entry_validation():
      """Test Pydantic validation"""
      # Valid entry
      entry = SleepEntry(
          id="test", user_id="u1", logged_at=datetime.now(),
          bedtime=time(22, 0), sleep_latency_minutes=15,
          wake_time=time(7, 0), total_sleep_hours=8.5,
          night_wakings=0, sleep_quality_rating=8,
          disruptions=[], phone_usage=False,
          phone_duration_minutes=None, alertness_rating=7
      )
      assert entry.sleep_quality_rating == 8

      # Invalid rating (out of range)
      with pytest.raises(ValueError):
          SleepEntry(..., sleep_quality_rating=11, ...)  # > 10
  ```
- **VALIDATE**: `pytest tests/unit/test_sleep_models.py -v`

### MANUAL TESTING - Sleep Quiz Flow

- **IMPLEMENT**: Complete manual test of all quiz paths
- **CHECKLIST**:
  - [ ] /sleep_quiz command starts quiz
  - [ ] Bedtime picker increments/decrements correctly
  - [ ] Confirm button saves bedtime and advances
  - [ ] All 8 questions display in order
  - [ ] Button callbacks respond without lag
  - [ ] query.answer() called (no infinite loading)
  - [ ] Multi-select disruptions toggle correctly
  - [ ] Phone usage "No" skips duration question
  - [ ] Phone usage "Yes" shows duration question
  - [ ] Sleep duration calculated correctly (overnight handling)
  - [ ] Summary shows correct data
  - [ ] Database entry created
  - [ ] /cancel command exits quiz
  - [ ] Edge case: Bedtime 23:00, Wake 01:00 (overnight)
- **VALIDATE**: All checklist items pass

### ADD quick-select time preset buttons (OPTIONAL ENHANCEMENT)

- **IMPLEMENT**: Add common time presets for faster selection
- **PATTERN**: FROM telegram-sleep-quiz-implementation.md:292-309
- **CODE**: Add row above time picker:
  ```python
  preset_row = [
      InlineKeyboardButton("10 PM", callback_data="bed_preset_22:00"),
      InlineKeyboardButton("11 PM", callback_data="bed_preset_23:00"),
      InlineKeyboardButton("12 AM", callback_data="bed_preset_00:00"),
  ]
  keyboard.insert(0, preset_row)  # Add as first row
  ```
- **GOTCHA**: Handle preset callbacks separately, immediately confirm
- **VALIDATE**: Optional - only implement if time allows

---

## TESTING STRATEGY

### Unit Tests

**Scope:** Pydantic models, time calculation logic

**Test Files:**
- `tests/unit/test_sleep_models.py`

**Coverage Requirements:**
- SleepEntry model validation (valid and invalid inputs)
- Field constraints (rating 1-10, duration 0-24, etc.)
- Optional vs required fields

**Fixtures:**
```python
@pytest.fixture
def sample_sleep_entry():
    return SleepEntry(
        id=str(uuid4()), user_id="test_user",
        logged_at=datetime.now(), bedtime=time(22, 0),
        sleep_latency_minutes=15, wake_time=time(7, 0),
        total_sleep_hours=8.75, night_wakings=0,
        sleep_quality_rating=8, disruptions=[],
        phone_usage=False, phone_duration_minutes=None,
        alertness_rating=7
    )
```

### Integration Tests

**Scope:** Database operations, full quiz flow simulation

**Test Files:**
- `tests/integration/test_sleep_quiz_flow.py`

**Test Cases:**
- Save sleep entry to database
- Retrieve sleep entries by user_id
- Multiple entries for same user
- Date range filtering (last 7 days)
- JSONB field storage (disruptions array)

### Edge Cases

**Critical Edge Cases to Test:**

1. **Overnight Sleep (wake_time < bedtime)**
   - Bedtime: 23:00, Wake: 06:00
   - Expected: 7 hours total (not -17 hours)

2. **Callback Data Size Limit**
   - Max 64 bytes for callback_data
   - Current longest: "phone_dur_90" = 12 bytes ✓

3. **Multi-Select State Persistence**
   - Select noise, light → deselect light → Done
   - Expected: Only 'noise' in disruptions list

4. **Quiz Cancellation Mid-Flow**
   - Start quiz → Q3 → /cancel
   - Expected: context.user_data cleaned up, no orphaned data

5. **Concurrent Quiz Attempts**
   - User starts quiz, abandons, starts new quiz
   - Expected: Old quiz data overwritten

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Code Quality

```bash
# Python import validation
python -c "from src.handlers.sleep_quiz import sleep_quiz_handler; print('✓ Imports valid')"

# Model validation
python -c "from src.models.sleep import SleepEntry; print('✓ Models valid')"

# Database queries validation
python -c "from src.db.queries import save_sleep_entry, get_sleep_entries; print('✓ Queries valid')"
```

**Expected**: All import checks pass with ✓

### Level 2: Database Migration

```bash
# Run migration
PGPASSWORD=postgres psql -h localhost -U postgres -d health_agent -f migrations/005_sleep_tracking.sql

# Verify table structure
PGPASSWORD=postgres psql -h localhost -U postgres -d health_agent -c "\d sleep_entries"

# Verify indexes
PGPASSWORD=postgres psql -h localhost -U postgres -d health_agent -c "\di idx_sleep_entries_user_logged"
```

**Expected**: Table created with all columns, indexes exist

### Level 3: Unit Tests

```bash
# Run unit tests
pytest tests/unit/test_sleep_models.py -v

# With coverage
pytest tests/unit/test_sleep_models.py --cov=src.models.sleep --cov-report=term-missing
```

**Expected**: All tests pass, coverage >80%

### Level 4: Integration Tests

```bash
# Run integration tests
pytest tests/integration/test_sleep_quiz_flow.py -v

# Full test suite
pytest tests/ -v -k sleep
```

**Expected**: All integration tests pass

### Level 5: Manual Bot Testing

```bash
# Start bot
python -m src.main

# In Telegram:
# 1. Send /sleep_quiz
# 2. Complete full quiz (all 8 questions)
# 3. Verify summary displays
# 4. Check database:
PGPASSWORD=postgres psql -h localhost -U postgres -d health_agent -c "SELECT * FROM sleep_entries ORDER BY logged_at DESC LIMIT 1;"
```

**Expected**:
- Quiz completes without errors
- Database entry created
- All data fields populated correctly

### Level 6: Edge Case Validation

```bash
# Test overnight sleep calculation manually:
python3 << EOF
bed_hour, bed_min = 23, 30
wake_hour, wake_min = 6, 15
latency = 20

bed_total = bed_hour * 60 + bed_min
wake_total = wake_hour * 60 + wake_min
if wake_total < bed_total:
    wake_total += 24 * 60

sleep_min = wake_total - bed_total - latency
hours = sleep_min / 60.0
print(f"Sleep duration: {hours:.2f} hours")
assert 6.5 <= hours <= 7.0, f"Expected ~6.75h, got {hours}h"
print("✓ Overnight calculation correct")
EOF
```

**Expected**: Calculation outputs ~6.75 hours

---

## ACCEPTANCE CRITERIA

- [ ] Sleep quiz accessible via /sleep_quiz command
- [ ] All 8 questions functional with inline keyboards
- [ ] No typing required (all buttons/pickers)
- [ ] Quiz completes in 60-90 seconds
- [ ] Data saved to sleep_entries table in PostgreSQL
- [ ] Sleep duration calculated correctly (handles overnight)
- [ ] Multi-select disruptions work (checkmarks update)
- [ ] Phone usage conditional logic works (skip duration if "No")
- [ ] Summary displays with calculated metrics
- [ ] All validation commands pass (Levels 1-6)
- [ ] Unit test coverage >80% for sleep models
- [ ] Integration tests pass for database operations
- [ ] No Telegram API errors (query.answer() called)
- [ ] Cancel command cleans up state
- [ ] No regressions in existing features
- [ ] Feature usage logged for analytics

---

## COMPLETION CHECKLIST

- [ ] All 27 tasks completed in order
- [ ] Database migration executed successfully
- [ ] Sleep entry model created and validated
- [ ] All 8 quiz questions implemented
- [ ] Time pickers functional (bedtime & wake time)
- [ ] Multi-select disruptions working
- [ ] Conditional phone duration question working
- [ ] Sleep duration calculation correct (overnight handling)
- [ ] Summary message displays properly
- [ ] ConversationHandler registered in bot.py
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing
- [ ] Manual testing checklist completed
- [ ] All validation commands (Levels 1-6) pass
- [ ] Edge cases tested (overnight, multi-select, cancellation)
- [ ] No linting/syntax errors
- [ ] No database connection errors
- [ ] Feature usage logging works
- [ ] Code follows project patterns

---

## NOTES

### Design Decisions

**1. Why Inline Keyboards over Mini Apps?**
- Faster development (2-3 days vs 1-2 weeks)
- No external hosting required
- Works entirely within Telegram chat
- Good enough for MVP (80% solution)
- Can migrate to Mini App later if needed

**2. Time Picker Implementation**
- Custom inline button picker (not native time picker)
- Increments: hours by 1, minutes by 15 (reduces cognitive load)
- Presets as optional enhancement for speed
- Reference: telegram-sleep-quiz-implementation.md:222-290

**3. Sleep Duration Calculation**
- Handle overnight sleep (wake < bedtime) by adding 24 hours
- Subtract sleep latency from total time in bed
- Store as float (hours with 2 decimal precision)
- Clinical threshold: 8-10 hours recommended for 15-year-olds

**4. Multi-Select Pattern**
- Use set() for toggle logic (add/remove)
- Rebuild keyboard on every callback to update checkmarks
- "Done" button to confirm and advance
- Reference: telegram-sleep-quiz-implementation.md:84-142

### Trade-offs

**Accuracy vs Speed:**
- Using midpoint values for ranges (15-30 min → 22 min)
- Button grid for quality (discrete 1-10) instead of continuous slider
- 15-minute time increments instead of 1-minute precision
- **Justification**: Reduces cognitive load, faster completion, sufficient clinical precision

**Data Granularity:**
- Storing disruptions as JSONB array (flexible for future additions)
- Not tracking exact wake-up times during night (only count)
- **Justification**: Balances data richness with user burden

### Future Enhancements

**Phase 2 (Post-MVP):**
- Daily reminder at 9 AM to fill sleep quiz
- Weekly trend visualization
- Automatic insights ("You sleep better when no phone usage")
- Integration with onboarding (ask if user wants sleep tracking)

**Phase 3 (Advanced):**
- Migrate to Telegram Mini App with true sliders
- Export data to CSV/PDF
- Correlate with food/workout data
- Sleep score algorithm
- Recommendations based on PSQI scoring

### Research References

**All implementation patterns sourced from:**
- `telegram-sleep-quiz-implementation.md` - Telegram UI patterns and code examples
- `sleep-quiz-research.md` - Validated PSQI questions and clinical thresholds
- `ONBOARDING_STRATEGY.md` - UX best practices for engagement

**Key Statistics Applied:**
- 60-90 second completion target (retention research)
- 8 core questions (balance comprehensiveness vs burden)
- Mobile-first design (large buttons, thumb-friendly)
- Immediate value (summary with insights)

### Confidence Assessment

**One-Pass Implementation Success Probability: 8.5/10**

**High Confidence Because:**
- Complete code examples in telegram-sleep-quiz-implementation.md
- Existing onboarding.py shows exact ConversationHandler pattern
- Database patterns well-established in codebase
- All question types have reference implementations

**Potential Challenges:**
- Overnight sleep duration calculation edge cases
- Multi-select state management (set operations)
- CallbackQuery vs Message handling (first question)
- Callback data size limits (64 bytes - monitored)

**Mitigation:**
- Explicit validation commands for each critical path
- Edge case testing checklist
- Manual testing before deployment
- Incremental task validation (compile after each task)
