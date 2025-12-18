# Feature: Dual-Path Progressive Onboarding System

The following plan is comprehensive and research-backed. Validate documentation and codebase patterns before implementing. Pay special attention to naming of existing utils, types, and models. Import from the right files.

## Feature Description

Implement a research-backed dual-path onboarding system for the AI Health Coach Telegram bot that serves both users in a hurry (Quick Start: 30-45s) and users wanting comprehensive understanding (Full Tour: 90-120s), plus an organic discovery path (Just Chat). The system uses progressive disclosure to showcase features (food tracking, voice notes, reminders, custom tracking, pep talks, adaptive personality) contextually rather than front-loading all capabilities at once.

**Industry Context**: 77% of users abandon apps within 3 days. Day 1 retention averages 22-26%. Our goal is to achieve 50%+ Day 1 retention through strategic onboarding.

## User Story

As a **new health-conscious user**
I want to **quickly understand what the bot can do and start using core features immediately**
So that **I can decide if this tool is valuable without investing time in lengthy tutorials**

## Problem Statement

Current onboarding (bot.py:210-268) is a static welcome message that:
- Lists features without demonstrating them
- Provides no personalization or path choice
- Has no progressive disclosure of capabilities
- Offers no "aha moment" or immediate value
- Results in poor feature discovery (users don't know about voice notes, custom tracking, reminders, pep talks, visual pattern learning, etc.)

## Solution Statement

Implement a three-path onboarding system with database-driven state management that:
1. **Quick Start** - 30-45 second path: timezone → pick focus → try ONE feature → done
2. **Full Tour** - 90-120 second interactive demo of all features with hands-on trials
3. **Just Chat** - Organic discovery with contextual feature reveals during conversation

All paths use progressive disclosure and get users to value quickly (< 30 seconds to first interaction).

## Feature Metadata

**Feature Type**: New Capability (Enhancement to existing /start command)
**Estimated Complexity**: High
**Primary Systems Affected**:
- Bot handlers (src/bot.py)
- Database schema (new tables + queries)
- Memory management (timezone/preference setup)
- Message routing logic

**Dependencies**:
- Existing: python-telegram-bot, PostgreSQL, memory_manager
- New: None (uses existing stack)

---

## CONTEXT REFERENCES

### Relevant Codebase Files - IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

**Bot Handlers & Flow:**
- `src/bot.py` (lines 210-268) - Current /start command, shows pattern to follow
- `src/bot.py` (lines 270-372) - Activation flow pattern (multi-step without ConversationHandler)
- `src/bot.py` (lines 641-756) - Message routing with status checks (handle_message)
- `src/bot.py` (lines 1012-1040) - Handler registration pattern in create_bot_application()
- `src/bot.py` (lines 678-715) - Timezone setup flow (existing multi-step pattern)

**Database Patterns:**
- `migrations/001_initial_schema.sql` - Table creation pattern with indexes
- `migrations/002_conversation_history.sql` - User-related table pattern
- `migrations/002_subscription_and_invites.sql` - ALTER TABLE pattern for extending users table
- `migrations/003_dynamic_tools.sql` - Complex table with JSONB, comments, versioning
- `src/db/queries.py` (lines 1-50) - Connection pool usage pattern
- `src/db/queries.py` (lines 187-281) - Conversation history save/load pattern
- `src/db/queries.py` (lines 786-813) - User subscription status pattern

**Memory & Preferences:**
- `src/memory/file_manager.py` (lines 72-93) - update_profile pattern
- `src/memory/file_manager.py` (lines 95-116) - update_preferences pattern
- `src/memory/file_manager.py` (lines 152-186) - save_observation pattern
- `src/memory/templates.py` (lines 18-32) - PREFERENCES_TEMPLATE structure

**Testing Patterns:**
- `tests/unit/test_memory.py` - Async test pattern with fixtures
- `tests/integration/test_food_workflow.py` - End-to-end workflow testing
- `pytest.ini` - Test configuration (asyncio_mode = auto)

### New Files to Create

- `migrations/004_onboarding_system.sql` - Database schema for onboarding state
- `src/handlers/onboarding.py` - All onboarding logic (handlers for each path)
- `src/models/onboarding.py` - Pydantic models for onboarding state
- `tests/unit/test_onboarding_state.py` - Unit tests for state management
- `tests/integration/test_onboarding_flow.py` - End-to-end onboarding tests

### Relevant Documentation - YOU SHOULD READ THESE BEFORE IMPLEMENTING!

**Telegram Bot Framework:**
- [python-telegram-bot ConversationHandler v22.5](https://docs.python-telegram-bot.org/en/stable/telegram.ext.conversationhandler.html)
  - Section: ConversationHandler API Reference
  - Why: Understand conversation state patterns (NOTE: we won't use this, but understand the concepts)
- [python-telegram-bot Examples - conversationbot.py](https://github.com/python-telegram-bot/python-telegram-bot/blob/master/examples/conversationbot.py)
  - Why: See entry_points and states pattern (we'll adapt to database-driven approach)

**State Management Best Practices:**
- [Build a stateful serverless Telegram bot - Part 2](https://janikvonrotz.ch/2020/01/21/build-a-stateful-serverless-telegram-bot-part-2/)
  - Section: FSM (Finite State Machine) pattern
  - Why: Understand state transition logic for onboarding flows
- [Two design patterns for Telegram Bots](https://dev.to/madhead/two-design-patterns-for-telegram-bots-59f5)
  - Section: Handler pattern and chain of responsibility
  - Why: Handler should have two inputs: update and current state

**Onboarding Research:**
- [App Onboarding Guide - Top 10 Examples 2025](https://uxcam.com/blog/10-apps-with-great-user-onboarding/)
  - Section: Progressive onboarding and time-to-value
  - Why: Research-backed patterns used in onboarding strategy
- [Progressive Disclosure UI Patterns](https://agentic-design.ai/patterns/ui-ux-patterns/progressive-disclosure-patterns)
  - Section: Contextual feature reveal patterns
  - Why: Implement Just Chat path with progressive disclosure

### Patterns to Follow

**Database-Driven State Management (NOT ConversationHandler):**
The codebase uses database state instead of ConversationHandler. Mirror this pattern:
```python
# From src/bot.py:652-672 (activation flow)
subscription = await get_user_subscription_status(user_id)

if subscription and subscription['status'] == 'pending':
    # Handle pending activation
    await activate(update, context)
    return

# Route based on status
if subscription['status'] == 'onboarding':
    await handle_onboarding_step(update, context)
    return
```

**Async Connection Pool Pattern:**
```python
# From src/db/queries.py:1-50
async with db.connection() as conn:
    async with conn.cursor() as cur:
        await cur.execute(query, params)
        await conn.commit()  # For writes
```

**Handler Registration Pattern:**
```python
# From src/bot.py:1012-1040
def create_bot_application() -> Application:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("transparency", transparency))

    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app
```

**Migration Pattern with Comments:**
```sql
-- From migrations/002_conversation_history.sql
CREATE TABLE IF NOT EXISTS conversation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversation_user_timestamp
    ON conversation_history(user_id, timestamp DESC);

COMMENT ON TABLE conversation_history IS 'Stores conversation messages for context';
```

**Memory File Update Pattern:**
```python
# From src/memory/file_manager.py:95-116
async def update_preferences(self, user_id: str, preference: str, value: str) -> None:
    """Update user preference in preferences.md"""
    prefs_path = self.data_path / user_id / "preferences.md"

    # Read current content
    content = prefs_path.read_text()

    # Update specific field
    # ... modification logic ...

    # Write back
    prefs_path.write_text(updated_content)
    logger.info(f"Updated preference for {user_id}: {preference}={value}")
```

**Async Test Pattern:**
```python
# From tests/unit/test_memory.py
@pytest.mark.asyncio
async def test_create_user_files(memory_manager, temp_data_dir):
    """Test creating memory files for new user"""
    user_id = "test_user_123"

    await memory_manager.create_user_files(user_id)

    # Verify files created
    user_dir = temp_data_dir / user_id
    assert user_dir.exists()
    assert (user_dir / "profile.md").exists()
```

---

## IMPLEMENTATION PLAN

### Phase 1: Database Foundation
Set up persistent onboarding state tracking with PostgreSQL tables and query functions.

**Tasks:**
- Create migration file with two tables: user_onboarding_state, feature_discovery_log
- Implement query functions for CRUD operations on both tables
- Add database initialization to main.py startup

### Phase 2: Onboarding Models & State Machine
Define data structures and state transition logic for the three onboarding paths.

**Tasks:**
- Create Pydantic models for onboarding state, steps, and paths
- Implement state machine logic for Quick Start flow (4 steps)
- Implement state machine logic for Full Tour flow (7 steps)
- Implement state machine logic for Just Chat (contextual triggers)

### Phase 3: Handler Implementation
Build message handlers for each onboarding step and path.

**Tasks:**
- Refactor existing /start command to branch to path selection
- Implement Quick Start handlers (timezone, focus selection, feature demo)
- Implement Full Tour handlers (profile, food demo, voice demo, tracking, reminders, personality, learning)
- Implement Just Chat contextual feature reveals

### Phase 4: Integration & Routing
Connect onboarding system to existing bot infrastructure.

**Tasks:**
- Update handle_message() to route onboarding-state users
- Integrate with existing memory_manager for timezone/preferences
- Integrate with existing auth system (subscription status)
- Add feature discovery logging throughout existing handlers

### Phase 5: Testing & Validation
Ensure comprehensive coverage and validate against acceptance criteria.

**Tasks:**
- Write unit tests for state machine logic
- Write unit tests for each handler function
- Write integration tests for complete flows (Quick Start, Full Tour, Just Chat)
- Manual testing via Telegram bot

---

## STEP-BY-STEP TASKS

Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE migrations/004_onboarding_system.sql

- **IMPLEMENT**: Two tables - user_onboarding_state and feature_discovery_log
- **PATTERN**: Mirror migrations/002_conversation_history.sql structure (lines 1-15)
- **IMPORTS**: None (SQL file)
- **GOTCHA**: Use VARCHAR(255) for user_id to match users.telegram_id type
- **VALIDATE**: `PGPASSWORD=postgres psql -h localhost -U postgres -d health_agent -f migrations/004_onboarding_system.sql`

```sql
-- User onboarding state tracking
CREATE TABLE IF NOT EXISTS user_onboarding_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) UNIQUE NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    onboarding_path VARCHAR(20),             -- 'quick', 'full', 'chat', NULL (not started)
    current_step VARCHAR(50) NOT NULL DEFAULT 'welcome',
    step_data JSONB DEFAULT '{}',            -- Stores partial inputs during flow
    completed_steps TEXT[] DEFAULT '{}',     -- Array of completed step names
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    last_interaction_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Feature discovery and usage tracking
CREATE TABLE IF NOT EXISTS feature_discovery_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    feature_name VARCHAR(100) NOT NULL,
    discovery_method VARCHAR(50),            -- 'onboarding', 'contextual', 'help_command'
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    first_used_at TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_onboarding_user_step
    ON user_onboarding_state(user_id, current_step)
    WHERE completed_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_onboarding_last_interaction
    ON user_onboarding_state(last_interaction_at DESC)
    WHERE completed_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_feature_discovery_user_feature
    ON feature_discovery_log(user_id, feature_name);

CREATE INDEX IF NOT EXISTS idx_feature_discovery_unused
    ON feature_discovery_log(user_id)
    WHERE first_used_at IS NULL;

-- Comments for documentation
COMMENT ON TABLE user_onboarding_state IS 'Tracks user progress through onboarding paths';
COMMENT ON TABLE feature_discovery_log IS 'Tracks when users discover and use features';
COMMENT ON COLUMN user_onboarding_state.step_data IS 'Stores partial inputs (name, goals, etc) during multi-step flows';
COMMENT ON COLUMN feature_discovery_log.discovery_method IS 'How the user learned about this feature';
```

### UPDATE src/db/queries.py

- **IMPLEMENT**: Add query functions for onboarding state management
- **PATTERN**: Mirror get_conversation_history pattern (queries.py:216-281)
- **IMPORTS**: `import json` for JSONB handling, `from typing import Optional, dict, list`
- **GOTCHA**: Use `dict_row` factory (already set in connection.py) for dict access
- **VALIDATE**: `python -c "from src.db.queries import get_onboarding_state; print('Import successful')"`

Add these functions at the end of src/db/queries.py:

```python
# ==========================================
# Onboarding State Management
# ==========================================

async def get_onboarding_state(user_id: str) -> Optional[dict]:
    """Get current onboarding state for user"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT onboarding_path, current_step, step_data,
                       completed_steps, started_at, completed_at, last_interaction_at
                FROM user_onboarding_state
                WHERE user_id = %s
                """,
                (user_id,)
            )
            row = await cur.fetchone()
            return dict(row) if row else None


async def start_onboarding(user_id: str, path: str) -> None:
    """Initialize onboarding state for a user"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO user_onboarding_state (user_id, onboarding_path, current_step)
                VALUES (%s, %s, 'path_selection')
                ON CONFLICT (user_id) DO UPDATE SET
                    onboarding_path = EXCLUDED.onboarding_path,
                    current_step = 'path_selection',
                    started_at = CURRENT_TIMESTAMP,
                    last_interaction_at = CURRENT_TIMESTAMP
                """,
                (user_id, path)
            )
            await conn.commit()
    logger.info(f"Started onboarding for {user_id} on path: {path}")


async def update_onboarding_step(
    user_id: str,
    new_step: str,
    step_data: dict = None,
    mark_complete: str = None
) -> None:
    """Update user's current onboarding step and optionally mark previous step complete"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            if mark_complete:
                # Mark previous step as complete and advance
                await cur.execute(
                    """
                    UPDATE user_onboarding_state
                    SET current_step = %s,
                        step_data = %s,
                        completed_steps = array_append(completed_steps, %s),
                        last_interaction_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                    """,
                    (new_step, json.dumps(step_data or {}), mark_complete, user_id)
                )
            else:
                # Just update current step
                await cur.execute(
                    """
                    UPDATE user_onboarding_state
                    SET current_step = %s,
                        step_data = %s,
                        last_interaction_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                    """,
                    (new_step, json.dumps(step_data or {}), user_id)
                )
            await conn.commit()
    logger.info(f"Updated onboarding step for {user_id}: {new_step}")


async def complete_onboarding(user_id: str) -> None:
    """Mark onboarding as completed"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE user_onboarding_state
                SET current_step = 'completed',
                    completed_at = CURRENT_TIMESTAMP,
                    last_interaction_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                """,
                (user_id,)
            )
            await conn.commit()
    logger.info(f"Completed onboarding for {user_id}")


async def log_feature_discovery(
    user_id: str,
    feature_name: str,
    discovery_method: str = "contextual"
) -> None:
    """Log when a user discovers a feature"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO feature_discovery_log
                (user_id, feature_name, discovery_method)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, feature_name) DO NOTHING
                """,
                (user_id, feature_name, discovery_method)
            )
            await conn.commit()
    logger.info(f"Logged feature discovery: {user_id} -> {feature_name}")


async def log_feature_usage(user_id: str, feature_name: str) -> None:
    """Log when a user actually uses a feature"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO feature_discovery_log
                (user_id, feature_name, first_used_at, usage_count, last_used_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, feature_name)
                DO UPDATE SET
                    first_used_at = COALESCE(feature_discovery_log.first_used_at, CURRENT_TIMESTAMP),
                    usage_count = feature_discovery_log.usage_count + 1,
                    last_used_at = CURRENT_TIMESTAMP
                """,
                (user_id, feature_name)
            )
            await conn.commit()
```

### CREATE src/models/onboarding.py

- **IMPLEMENT**: Pydantic models for onboarding state and paths
- **PATTERN**: Mirror src/models/user.py structure (lines 6-14)
- **IMPORTS**: `from pydantic import BaseModel, Field; from typing import Optional, List; from datetime import datetime`
- **GOTCHA**: Use Optional for nullable fields
- **VALIDATE**: `python -c "from src.models.onboarding import OnboardingState; print('Import successful')"`

```python
"""Onboarding state models"""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class OnboardingState(BaseModel):
    """User's current onboarding state"""

    user_id: str
    onboarding_path: Optional[Literal["quick", "full", "chat"]] = None
    current_step: str = "welcome"
    step_data: dict = Field(default_factory=dict)
    completed_steps: List[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_interaction_at: Optional[datetime] = None

    @property
    def is_complete(self) -> bool:
        """Check if onboarding is complete"""
        return self.completed_at is not None or self.current_step == "completed"

    @property
    def is_active(self) -> bool:
        """Check if onboarding is in progress"""
        return self.started_at is not None and not self.is_complete


class OnboardingPath(BaseModel):
    """Configuration for an onboarding path"""

    name: Literal["quick", "full", "chat"]
    display_name: str
    description: str
    estimated_time: str
    steps: List[str]


class FeatureDiscovery(BaseModel):
    """Feature discovery tracking"""

    user_id: str
    feature_name: str
    discovery_method: str
    discovered_at: datetime
    first_used_at: Optional[datetime] = None
    usage_count: int = 0
    last_used_at: Optional[datetime] = None

    @property
    def has_been_used(self) -> bool:
        """Check if feature has been used at least once"""
        return self.first_used_at is not None


# Onboarding path configurations
ONBOARDING_PATHS = {
    "quick": OnboardingPath(
        name="quick",
        display_name="Quick Start",
        description="Jump right in (30 sec)",
        estimated_time="30-45 seconds",
        steps=["path_selection", "timezone_setup", "focus_selection", "feature_demo", "completed"]
    ),
    "full": OnboardingPath(
        name="full",
        display_name="Show Me Around",
        description="Full tour (2 min)",
        estimated_time="90-120 seconds",
        steps=[
            "path_selection", "timezone_setup", "profile_setup",
            "food_demo", "voice_demo", "tracking_demo", "reminders_demo",
            "personality_demo", "learning_explanation", "completed"
        ]
    ),
    "chat": OnboardingPath(
        name="chat",
        display_name="Just Chat",
        description="I'll learn as we go",
        estimated_time="Ongoing",
        steps=["path_selection", "completed"]  # Minimal steps, features revealed contextually
    )
}

# Feature names for discovery tracking
TRACKABLE_FEATURES = [
    "food_tracking",
    "voice_notes",
    "custom_tracking",
    "reminders",
    "personality_customization",
    "visual_patterns",
    "transparency_view",
    "pep_talks",
    "daily_summaries"
]
```

### CREATE src/handlers/onboarding.py

- **IMPLEMENT**: All onboarding handler functions for three paths
- **PATTERN**: Mirror src/bot.py handler structure (lines 210-268 for /start, 270-372 for activate)
- **IMPORTS**: `from telegram import Update, ReplyKeyboardMarkup, KeyboardButton; from telegram.ext import ContextTypes; import logging; from src.db.queries import *; from src.models.onboarding import *; from src.memory.file_manager import memory_manager`
- **GOTCHA**: Always check `should_process_message(update)` first (topic filter)
- **VALIDATE**: `python -c "from src.handlers.onboarding import handle_onboarding_start; print('Import successful')"`

```python
"""Onboarding handlers for dual-path progressive onboarding"""
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from src.db.queries import (
    get_onboarding_state,
    start_onboarding,
    update_onboarding_step,
    complete_onboarding,
    log_feature_discovery,
    get_user_subscription_status
)
from src.models.onboarding import ONBOARDING_PATHS, TRACKABLE_FEATURES
from src.memory.file_manager import memory_manager
from src.utils.auth import is_authorized

logger = logging.getLogger(__name__)


async def handle_onboarding_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show path selection screen after activation
    Called from refactored /start command
    """
    user_id = str(update.effective_user.id)

    # Check if already has onboarding state
    state = await get_onboarding_state(user_id)

    if state and state.get('completed_at'):
        # Already completed onboarding, show regular welcome
        await update.message.reply_text(
            "👋 Welcome back! How can I help you today?\n\n"
            "Send a food photo, ask me anything, or type /help for commands."
        )
        return

    # Show path selection with inline keyboard
    message = (
        "✅ You're all set! Let's get you started.\n\n"
        "I'm your AI health coach - I track food, workouts, sleep, "
        "give pep talks, and learn your habits over time.\n\n"
        "**How should we start?**"
    )

    # Create keyboard with three options
    keyboard = [
        ["Quick Start 🚀"],
        ["Show Me Around 🎬"],
        ["Just Chat 💬"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")

    # Initialize onboarding state
    await start_onboarding(user_id, "pending")  # Will be set when user picks path

    logger.info(f"Showed path selection to user {user_id}")


async def handle_path_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle user's path selection (Quick Start, Full Tour, Just Chat)
    """
    user_id = str(update.effective_user.id)
    text = update.message.text.lower()

    # Determine selected path
    if "quick" in text or "🚀" in text:
        path = "quick"
    elif "show" in text or "tour" in text or "around" in text or "🎬" in text:
        path = "full"
    elif "chat" in text or "💬" in text:
        path = "chat"
    else:
        # Invalid selection, show options again
        await update.message.reply_text(
            "Please choose one of the three options:",
            reply_markup=ReplyKeyboardMarkup(
                [["Quick Start 🚀"], ["Show Me Around 🎬"], ["Just Chat 💬"]],
                one_time_keyboard=True,
                resize_keyboard=True
            )
        )
        return

    # Update state with selected path
    await start_onboarding(user_id, path)

    # Route to appropriate first step
    if path == "quick":
        await quick_start_timezone(update, context)
    elif path == "full":
        await full_tour_timezone(update, context)
    elif path == "chat":
        await just_chat_start(update, context)

    logger.info(f"User {user_id} selected path: {path}")


async def quick_start_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick Start Step 1: Set timezone"""
    user_id = str(update.effective_user.id)

    # Check if user already has timezone
    from src.utils.timezone_helper import get_timezone_from_profile
    existing_tz = get_timezone_from_profile(user_id)

    if existing_tz:
        # Already has timezone, skip to focus selection
        await update_onboarding_step(user_id, "focus_selection", mark_complete="timezone_setup")
        await quick_start_focus_selection(update, context)
        return

    # Show timezone setup
    message = (
        "🌍 **Quick setup: What's your timezone?**\n\n"
        "Two ways to set it:\n"
        "📍 Share your location (tap 📎 → Location)\n"
        "⌨️ Or type it: \"America/New_York\", \"Europe/London\", etc.\n\n"
        "_Why? So reminders hit at the right time!_"
    )

    # Create keyboard with location button
    keyboard = [[KeyboardButton("📍 Share Location", request_location=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    await update_onboarding_step(user_id, "timezone_setup")


async def quick_start_focus_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick Start Step 2: Pick main focus"""
    user_id = str(update.effective_user.id)

    message = (
        "🎯 **What's your main goal right now?**\n\n"
        "Pick what matters most to you:"
    )

    keyboard = [
        ["🍽️ Track nutrition"],
        ["💪 Build workout habit"],
        ["😴 Improve sleep"],
        ["🏃 General health coaching"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    await update_onboarding_step(user_id, "focus_selection", mark_complete="timezone_setup")


async def quick_start_feature_demo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick Start Step 3: Demo the selected feature"""
    user_id = str(update.effective_user.id)
    text = update.message.text.lower()

    # Determine selected focus and show appropriate demo
    if "nutrition" in text or "food" in text or "🍽️" in text:
        focus = "nutrition"
        message = (
            "🍽️ **Perfect! Let's try it right now.**\n\n"
            "Send me a photo of your last meal or snack.\n"
            "I'll analyze it and show you calories + macros instantly.\n\n"
            "📸 **Try it →** (send any food photo)"
        )
        await log_feature_discovery(user_id, "food_tracking", "onboarding")

    elif "workout" in text or "exercise" in text or "💪" in text:
        focus = "workout"
        message = (
            "💪 **Nice! Let's log your first workout.**\n\n"
            "Tell me what you did today. Examples:\n"
            "• \"Just did 30 min cardio\"\n"
            "• \"Leg day: squats, deadlifts, lunges\"\n"
            "• \"Rest day\"\n\n"
            "I'll remember it and can remind you tomorrow!"
        )
        await log_feature_discovery(user_id, "custom_tracking", "onboarding")

    elif "sleep" in text or "😴" in text:
        focus = "sleep"
        message = (
            "😴 **Great choice! Sleep is crucial.**\n\n"
            "Rate your sleep quality last night (1-10).\n\n"
            "I'll track this and help you spot patterns!"
        )
        await log_feature_discovery(user_id, "custom_tracking", "onboarding")

    else:
        focus = "general"
        message = (
            "🏃 **Awesome! I'm here to help with everything.**\n\n"
            "Let's start simple: Tell me about your health goals.\n"
            "Just chat naturally - I'll suggest features as you need them!"
        )

    # Save focus to step_data
    state = await get_onboarding_state(user_id)
    step_data = state.get('step_data', {}) if state else {}
    step_data['focus'] = focus

    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
    await update_onboarding_step(user_id, "feature_demo", step_data=step_data, mark_complete="focus_selection")


async def quick_start_complete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick Start Step 4: Complete onboarding"""
    user_id = str(update.effective_user.id)

    message = (
        "🎉 **Great! That's the core flow.**\n\n"
        "⚡ **Quick tips:**\n"
        "• Send photos anytime → I'll analyze food\n"
        "• Voice notes work too (I transcribe them)\n"
        "• Just chat normally - I'll suggest features as you need them\n\n"
        "Want to see everything I can do? Type \"show features\" or just start chatting!"
    )

    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
    await complete_onboarding(user_id)

    logger.info(f"User {user_id} completed Quick Start onboarding")


async def full_tour_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Full Tour Step 1: Set timezone (same as quick start)"""
    await quick_start_timezone(update, context)


async def full_tour_profile_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Full Tour Step 2: Collect profile information"""
    user_id = str(update.effective_user.id)

    message = (
        "👤 **Tell me about yourself** (optional, but helps me personalize):\n\n"
        "• What's your name?\n"
        "• Your age?\n"
        "• Current goal? (lose weight, build muscle, maintain health)\n\n"
        "You can skip any question - just say \"skip\" or \"next\""
    )

    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
    await update_onboarding_step(user_id, "profile_setup", mark_complete="timezone_setup")


async def full_tour_food_demo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Full Tour Step 3: Interactive food tracking demo"""
    user_id = str(update.effective_user.id)

    message = (
        "🎬 **Here's what I can do. Let's try them!**\n\n"
        "**1️⃣ 📸 FOOD TRACKING**\n"
        "Send me ANY food photo → instant calories + macros\n"
        "No logging, no searching databases - just snap and send.\n\n"
        "→ **Try it now:** Send me a photo from your gallery!"
    )

    await update.message.reply_text(message, parse_mode="Markdown")
    await update_onboarding_step(user_id, "food_demo", mark_complete="profile_setup")
    await log_feature_discovery(user_id, "food_tracking", "onboarding")


async def full_tour_complete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Full Tour: Complete onboarding after all demos"""
    user_id = str(update.effective_user.id)

    message = (
        "🎉 **Tour complete! You're ready.**\n\n"
        "📝 **Quick reference:**\n"
        "/transparency - See what I know about you\n"
        "/settings - Change my personality\n"
        "/help - Full command list\n\n"
        "🚀 **Start by:**\n"
        "• Sending a food photo\n"
        "• Telling me your goal\n"
        "• Or just chat - I'll guide you!\n\n"
        "What would you like to do first?"
    )

    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
    await complete_onboarding(user_id)

    logger.info(f"User {user_id} completed Full Tour onboarding")


async def just_chat_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Just Chat: Start organic discovery mode"""
    user_id = str(update.effective_user.id)

    message = (
        "💬 **Perfect! I learn best through conversation anyway.**\n\n"
        "Tell me what brings you here - a goal, a question, "
        "or just \"I want to get healthier\" works too.\n\n"
        "I'll introduce features naturally as you need them."
    )

    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
    await complete_onboarding(user_id)  # Mark as complete, but discovery is ongoing

    logger.info(f"User {user_id} selected Just Chat path")


async def handle_onboarding_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Main router for onboarding messages
    Called from bot.py handle_message() when user is in onboarding
    """
    user_id = str(update.effective_user.id)
    state = await get_onboarding_state(user_id)

    if not state:
        # No onboarding state, shouldn't be here
        return

    current_step = state.get('current_step')
    path = state.get('onboarding_path')

    # Route to appropriate handler based on current step
    if current_step == "path_selection":
        await handle_path_selection(update, context)

    elif current_step == "timezone_setup":
        # Handle timezone input (either location or text)
        if update.message.location:
            # Location shared
            from src.utils.timezone_helper import get_timezone_from_coordinates, update_timezone_in_profile
            lat = update.message.location.latitude
            lon = update.message.location.longitude
            tz = get_timezone_from_coordinates(lat, lon)
            update_timezone_in_profile(user_id, tz)

            await update.message.reply_text(
                f"✅ Got it! Your timezone is **{tz}**",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            # Text timezone
            from src.utils.timezone_helper import update_timezone_in_profile
            import pytz
            try:
                tz_input = update.message.text.strip()
                pytz.timezone(tz_input)  # Validate
                update_timezone_in_profile(user_id, tz_input)
                await update.message.reply_text(
                    f"✅ Great! Your timezone is now **{tz_input}**",
                    parse_mode="Markdown"
                )
            except:
                await update.message.reply_text(
                    "❌ Invalid timezone. Try \"America/New_York\" or share your location."
                )
                return

        # Advance to next step based on path
        if path == "quick":
            await quick_start_focus_selection(update, context)
        elif path == "full":
            await full_tour_profile_setup(update, context)

    elif current_step == "focus_selection":
        await quick_start_feature_demo(update, context)

    elif current_step == "feature_demo":
        # User tried the feature, complete quick start
        await quick_start_complete(update, context)

    elif current_step == "profile_setup":
        # Save profile data and advance
        # TODO: Parse name/age/goals from user message and save to memory
        await full_tour_food_demo(update, context)

    elif current_step == "food_demo":
        # User sent food photo or message, advance to voice demo
        # TODO: Show voice demo message
        await update_onboarding_step(user_id, "voice_demo", mark_complete="food_demo")
        # ... continue full tour steps

    # Add more step handlers as needed
```

### UPDATE src/bot.py

- **IMPLEMENT**: Refactor /start command to use new onboarding system
- **PATTERN**: Follow existing /start structure (bot.py:210-268)
- **IMPORTS**: Add `from src.handlers.onboarding import handle_onboarding_start, handle_onboarding_message`
- **GOTCHA**: Preserve existing activation check logic
- **VALIDATE**: `python -m pytest tests/ -v -k onboarding`

**Changes to `start()` function (around line 210):**

```python
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - now with onboarding"""
    user_id = str(update.effective_user.id)

    # Check topic filter
    if not should_process_message(update):
        return

    # Create user in database if doesn't exist (with pending status)
    if not await user_exists(user_id):
        await create_user(user_id)
        await memory_manager.create_user_files(user_id)

        # Auto-detect and set timezone for new users
        user_data = {
            "language_code": update.effective_user.language_code or "en"
        }
        # Note: detect_timezone_from_telegram needs implementation
        # For now, skip and let onboarding handle it

    # Check if user is activated
    from src.db.queries import get_user_subscription_status
    subscription = await get_user_subscription_status(user_id)

    if not subscription or subscription['status'] == 'pending':
        # User needs to activate with invite code
        pending_message = """👋 Welcome to AI Health Coach!

⚠️ **Activation Required**

To use this bot, you need an invite code.
Send your invite code to activate your account.

Example: `HEALTH2024`

Don't have a code? Contact the admin to request one."""
        await update.message.reply_text(pending_message)
        return

    # User is activated, check onboarding status
    from src.db.queries import get_onboarding_state
    onboarding = await get_onboarding_state(user_id)

    if not onboarding or not onboarding.get('completed_at'):
        # Start onboarding flow
        await handle_onboarding_start(update, context)
    else:
        # Already completed onboarding, show standard welcome
        welcome_message = f"""👋 Welcome back to your AI Health Coach!

✅ **Account Status:** {subscription['status'].title()} ({subscription['tier']})

Send me a food photo, ask me anything, or type /help for commands!"""

        await update.message.reply_text(welcome_message)
```

**Changes to `handle_message()` function (around line 641):**

Add routing logic before authorization check:

```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages - now with onboarding routing"""
    user_id = str(update.effective_user.id)

    # Check topic filter
    if not should_process_message(update):
        return

    text = update.message.text
    logger.info(f"Message from {user_id}: {text[:50]}...")

    # Check if user is pending activation
    from src.db.queries import get_user_subscription_status, get_onboarding_state
    subscription = await get_user_subscription_status(user_id)

    if subscription and subscription['status'] == 'pending':
        # ... existing activation code ...
        return

    # Check if user is in onboarding
    onboarding = await get_onboarding_state(user_id)
    if onboarding and not onboarding.get('completed_at'):
        # Route to onboarding handler
        await handle_onboarding_message(update, context)
        return

    # Check authorization (for active users)
    if not await is_authorized(user_id):
        return

    # ... rest of existing handle_message code ...
```

### UPDATE src/bot.py - Handler Registration

- **IMPLEMENT**: Register onboarding import at top of file
- **PATTERN**: Existing import structure (bot.py:1-30)
- **IMPORTS**: `from src.handlers.onboarding import handle_onboarding_start, handle_onboarding_message`
- **GOTCHA**: No new handler registration needed (routing happens in existing handlers)
- **VALIDATE**: `python -c "import src.bot; print('Import successful')"`

Add to imports section (after line 23):

```python
from src.handlers.onboarding import handle_onboarding_start, handle_onboarding_message
```

No changes to `create_bot_application()` needed - onboarding is routed through existing handlers.

### ADD Feature Discovery Logging to Existing Handlers

- **IMPLEMENT**: Add `log_feature_usage()` calls to existing feature handlers
- **PATTERN**: Single line addition after feature is used
- **IMPORTS**: Already imported in queries
- **GOTCHA**: Only log on actual usage, not discovery
- **VALIDATE**: Manual testing - check feature_discovery_log table after using features

**Changes:**

In `handle_photo()` (around line 758):
```python
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle food photos"""
    user_id = str(update.effective_user.id)

    # ... existing code ...

    # Log feature usage
    from src.db.queries import log_feature_usage
    await log_feature_usage(user_id, "food_tracking")

    # ... rest of existing code ...
```

In `handle_voice()` (around line 890):
```python
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice notes"""
    user_id = str(update.effective_user.id)

    # ... existing code ...

    # Log feature usage
    from src.db.queries import log_feature_usage
    await log_feature_usage(user_id, "voice_notes")

    # ... rest of existing code ...
```

In `schedule_reminder()` tool (src/agent/__init__.py around line 412):
```python
@agent.tool
async def schedule_reminder(ctx, reminder_time: str, message: str) -> ReminderScheduleResult:
    """Schedule a daily reminder"""
    deps: AgentDeps = ctx.deps

    # ... existing code ...

    # Log feature usage
    from src.db.queries import log_feature_usage
    await log_feature_usage(deps.telegram_id, "reminders")

    # ... rest of existing code ...
```

### CREATE tests/unit/test_onboarding_state.py

- **IMPLEMENT**: Unit tests for onboarding state machine and models
- **PATTERN**: Mirror tests/unit/test_memory.py async test structure
- **IMPORTS**: `import pytest; from src.models.onboarding import *; from src.db.queries import *`
- **GOTCHA**: Use `@pytest.mark.asyncio` for all async tests
- **VALIDATE**: `python -m pytest tests/unit/test_onboarding_state.py -v`

```python
"""Unit tests for onboarding state management"""
import pytest
from src.models.onboarding import OnboardingState, ONBOARDING_PATHS, TRACKABLE_FEATURES


class TestOnboardingModels:
    """Tests for onboarding Pydantic models"""

    def test_onboarding_state_creation(self):
        """Test creating an onboarding state"""
        state = OnboardingState(
            user_id="test_123",
            onboarding_path="quick",
            current_step="timezone_setup"
        )

        assert state.user_id == "test_123"
        assert state.onboarding_path == "quick"
        assert state.current_step == "timezone_setup"
        assert state.is_active is False  # started_at not set
        assert state.is_complete is False

    def test_onboarding_paths_config(self):
        """Test that all onboarding paths are configured"""
        assert "quick" in ONBOARDING_PATHS
        assert "full" in ONBOARDING_PATHS
        assert "chat" in ONBOARDING_PATHS

        quick_path = ONBOARDING_PATHS["quick"]
        assert quick_path.name == "quick"
        assert len(quick_path.steps) > 0
        assert "path_selection" in quick_path.steps
        assert "completed" in quick_path.steps

    def test_trackable_features_defined(self):
        """Test that trackable features are defined"""
        assert len(TRACKABLE_FEATURES) > 0
        assert "food_tracking" in TRACKABLE_FEATURES
        assert "voice_notes" in TRACKABLE_FEATURES
        assert "reminders" in TRACKABLE_FEATURES


@pytest.mark.asyncio
class TestOnboardingQueries:
    """Tests for onboarding database queries"""

    @pytest.fixture
    async def test_user_id(self):
        """Standard test user ID"""
        return "test_onboarding_user_456"

    @pytest.mark.asyncio
    async def test_get_nonexistent_onboarding_state(self, test_user_id):
        """Test getting state for user without onboarding"""
        from src.db.queries import get_onboarding_state

        state = await get_onboarding_state(test_user_id)
        assert state is None

    @pytest.mark.asyncio
    async def test_start_onboarding(self, test_user_id):
        """Test starting onboarding for a user"""
        from src.db.queries import start_onboarding, get_onboarding_state

        await start_onboarding(test_user_id, "quick")

        state = await get_onboarding_state(test_user_id)
        assert state is not None
        assert state["onboarding_path"] == "quick"
        assert state["current_step"] == "path_selection"
        assert state["started_at"] is not None

    @pytest.mark.asyncio
    async def test_update_onboarding_step(self, test_user_id):
        """Test updating onboarding step"""
        from src.db.queries import start_onboarding, update_onboarding_step, get_onboarding_state

        await start_onboarding(test_user_id, "quick")
        await update_onboarding_step(
            test_user_id,
            "timezone_setup",
            step_data={"timezone": "America/New_York"},
            mark_complete="path_selection"
        )

        state = await get_onboarding_state(test_user_id)
        assert state["current_step"] == "timezone_setup"
        assert "path_selection" in state["completed_steps"]
        assert state["step_data"]["timezone"] == "America/New_York"

    @pytest.mark.asyncio
    async def test_complete_onboarding(self, test_user_id):
        """Test marking onboarding as complete"""
        from src.db.queries import start_onboarding, complete_onboarding, get_onboarding_state

        await start_onboarding(test_user_id, "quick")
        await complete_onboarding(test_user_id)

        state = await get_onboarding_state(test_user_id)
        assert state["current_step"] == "completed"
        assert state["completed_at"] is not None
```

### CREATE tests/integration/test_onboarding_flow.py

- **IMPLEMENT**: Integration tests for complete onboarding flows
- **PATTERN**: Mirror tests/integration/test_food_workflow.py structure
- **IMPORTS**: `import pytest; from unittest.mock import Mock, AsyncMock, patch`
- **GOTCHA**: Mock Update and Context objects for Telegram handlers
- **VALIDATE**: `python -m pytest tests/integration/test_onboarding_flow.py -v`

```python
"""Integration tests for onboarding flows"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.handlers.onboarding import (
    handle_onboarding_start,
    handle_path_selection,
    quick_start_complete,
    handle_onboarding_message
)


@pytest.fixture
def mock_user_id():
    """Standard test user ID"""
    return "test_flow_user_789"


@pytest.fixture
def mock_update(mock_user_id):
    """Mock Telegram Update object"""
    update = Mock()
    update.effective_user.id = int(mock_user_id)
    update.message.text = ""
    update.message.reply_text = AsyncMock()
    update.message.location = None
    return update


@pytest.fixture
def mock_context():
    """Mock Telegram Context object"""
    context = Mock()
    context.user_data = {}
    context.bot.send_message = AsyncMock()
    return context


@pytest.mark.asyncio
class TestQuickStartFlow:
    """Test complete Quick Start onboarding flow"""

    @pytest.mark.asyncio
    async def test_complete_quick_start_flow(self, mock_update, mock_context, mock_user_id):
        """Test user completing entire Quick Start path"""

        # Step 1: Show path selection
        with patch("src.db.queries.get_onboarding_state", return_value=None):
            with patch("src.db.queries.start_onboarding", new_callable=AsyncMock):
                await handle_onboarding_start(mock_update, mock_context)

                # Verify path selection shown
                mock_update.message.reply_text.assert_called_once()
                call_args = mock_update.message.reply_text.call_args
                assert "How should we start" in call_args[0][0]

        # Step 2: User selects Quick Start
        mock_update.message.text = "Quick Start 🚀"
        with patch("src.db.queries.start_onboarding", new_callable=AsyncMock):
            with patch("src.handlers.onboarding.quick_start_timezone", new_callable=AsyncMock) as mock_tz:
                await handle_path_selection(mock_update, mock_context)

                # Verify routed to timezone setup
                mock_tz.assert_called_once()

        # Step 3: User sets timezone
        mock_update.message.text = "Europe/Stockholm"
        state_mock = {
            "onboarding_path": "quick",
            "current_step": "timezone_setup",
            "step_data": {},
            "completed_steps": [],
            "completed_at": None
        }

        with patch("src.db.queries.get_onboarding_state", return_value=state_mock):
            with patch("src.utils.timezone_helper.update_timezone_in_profile"):
                with patch("src.db.queries.update_onboarding_step", new_callable=AsyncMock):
                    with patch("src.handlers.onboarding.quick_start_focus_selection", new_callable=AsyncMock) as mock_focus:
                        await handle_onboarding_message(mock_update, mock_context)

                        # Verify advanced to focus selection
                        mock_focus.assert_called_once()

        # Step 4: User picks nutrition focus
        mock_update.message.text = "🍽️ Track nutrition"
        state_mock["current_step"] = "focus_selection"

        with patch("src.db.queries.get_onboarding_state", return_value=state_mock):
            with patch("src.db.queries.update_onboarding_step", new_callable=AsyncMock):
                with patch("src.db.queries.log_feature_discovery", new_callable=AsyncMock):
                    await handle_onboarding_message(mock_update, mock_context)

                    # Verify demo shown
                    assert mock_update.message.reply_text.called

        # Step 5: Complete onboarding
        with patch("src.db.queries.complete_onboarding", new_callable=AsyncMock) as mock_complete:
            await quick_start_complete(mock_update, mock_context)

            # Verify completion
            mock_complete.assert_called_once_with(mock_user_id)
            assert mock_update.message.reply_text.called


@pytest.mark.asyncio
class TestFullTourFlow:
    """Test complete Full Tour onboarding flow"""

    @pytest.mark.asyncio
    async def test_full_tour_path_selection(self, mock_update, mock_context):
        """Test selecting Full Tour path"""
        mock_update.message.text = "Show Me Around 🎬"

        with patch("src.db.queries.start_onboarding", new_callable=AsyncMock):
            with patch("src.handlers.onboarding.full_tour_timezone", new_callable=AsyncMock) as mock_tz:
                await handle_path_selection(mock_update, mock_context)

                # Verify routed to full tour
                mock_tz.assert_called_once()


@pytest.mark.asyncio
class TestJustChatFlow:
    """Test Just Chat onboarding path"""

    @pytest.mark.asyncio
    async def test_just_chat_immediate_completion(self, mock_update, mock_context, mock_user_id):
        """Test Just Chat path completes immediately"""
        mock_update.message.text = "Just Chat 💬"

        with patch("src.db.queries.start_onboarding", new_callable=AsyncMock):
            with patch("src.handlers.onboarding.just_chat_start", new_callable=AsyncMock) as mock_chat:
                await handle_path_selection(mock_update, mock_context)

                # Verify just chat started
                mock_chat.assert_called_once()
```

### MANUAL TESTING CHECKLIST

- **IMPLEMENT**: Manual validation via Telegram bot
- **PATTERN**: Interactive testing with real bot
- **IMPORTS**: N/A (manual testing)
- **GOTCHA**: Need activated account with invite code
- **VALIDATE**: Follow checklist below

**Manual Test Steps:**

1. **Quick Start Path:**
   ```
   ✓ Send /start
   ✓ Select "Quick Start 🚀"
   ✓ Share location OR type timezone
   ✓ Pick "Track nutrition"
   ✓ Send a food photo
   ✓ Verify completion message
   ✓ Check database: SELECT * FROM user_onboarding_state WHERE user_id='YOUR_ID';
   ```

2. **Full Tour Path:**
   ```
   ✓ Delete onboarding state: DELETE FROM user_onboarding_state WHERE user_id='YOUR_ID';
   ✓ Send /start
   ✓ Select "Show Me Around 🎬"
   ✓ Go through each demo step
   ✓ Verify completion
   ```

3. **Just Chat Path:**
   ```
   ✓ Delete onboarding state
   ✓ Send /start
   ✓ Select "Just Chat 💬"
   ✓ Verify immediate completion
   ✓ Chat normally and verify bot responds
   ```

4. **Feature Discovery Tracking:**
   ```
   ✓ Send a food photo
   ✓ Check: SELECT * FROM feature_discovery_log WHERE user_id='YOUR_ID';
   ✓ Verify "food_tracking" logged with usage_count incremented
   ```

5. **Returning User:**
   ```
   ✓ Complete onboarding
   ✓ Send /start again
   ✓ Verify sees "Welcome back" not onboarding
   ```

---

## TESTING STRATEGY

### Unit Tests

**Scope:** Isolated component testing
- Onboarding models (Pydantic validation)
- State machine logic
- Individual query functions
- Handler routing logic

**Framework:** pytest with pytest-asyncio
**Pattern:** Mirror existing test_memory.py structure
**Coverage Target:** 80%+ for new code

### Integration Tests

**Scope:** Multi-component workflows
- Complete Quick Start flow (4 steps)
- Complete Full Tour flow (7+ steps)
- Just Chat path (immediate completion)
- Database persistence across steps
- Feature discovery logging

**Framework:** pytest with mocked Telegram objects
**Pattern:** Mirror existing test_food_workflow.py structure

### Edge Cases

**Scenarios to test:**
1. User abandons onboarding mid-flow (incomplete state)
2. User sends /start during onboarding (should resume)
3. User sends /start after completion (should show welcome)
4. Invalid timezone input during timezone setup
5. Invalid path selection (typo in response)
6. Database connection failure during onboarding
7. User in pending activation state tries to start onboarding
8. Location sharing when timezone already set (should skip)

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Type Checking

```bash
# Python syntax check
python -m py_compile src/handlers/onboarding.py
python -m py_compile src/models/onboarding.py

# Type checking with mypy (if configured)
mypy src/handlers/onboarding.py src/models/onboarding.py

# Import validation
python -c "from src.handlers.onboarding import handle_onboarding_start; print('✓ Onboarding imports')"
python -c "from src.models.onboarding import OnboardingState; print('✓ Models import')"
python -c "from src.db.queries import get_onboarding_state; print('✓ Queries import')"
```

**Expected:** All commands pass with exit code 0

### Level 2: Database Migration

```bash
# Apply migration (ensure PostgreSQL is running)
PGPASSWORD=postgres psql -h localhost -U postgres -d health_agent -f migrations/004_onboarding_system.sql

# Verify tables created
PGPASSWORD=postgres psql -h localhost -U postgres -d health_agent -c "\d user_onboarding_state"
PGPASSWORD=postgres psql -h localhost -U postgres -d health_agent -c "\d feature_discovery_log"

# Verify indexes created
PGPASSWORD=postgres psql -h localhost -U postgres -d health_agent -c "\di" | grep onboarding
```

**Expected:** Tables and indexes exist

### Level 3: Unit Tests

```bash
# Run onboarding unit tests
python -m pytest tests/unit/test_onboarding_state.py -v

# Run with coverage
python -m pytest tests/unit/test_onboarding_state.py --cov=src.handlers.onboarding --cov=src.models.onboarding --cov-report=term-missing
```

**Expected:** All tests pass, coverage > 80%

### Level 4: Integration Tests

```bash
# Run onboarding integration tests
python -m pytest tests/integration/test_onboarding_flow.py -v

# Run all tests
python -m pytest tests/ -v
```

**Expected:** All tests pass with zero failures

### Level 5: Manual Bot Testing

```bash
# Start bot
python -m src.main

# In Telegram:
# 1. Send /start
# 2. Go through Quick Start flow
# 3. Verify completion

# Check database state
PGPASSWORD=postgres psql -h localhost -U postgres -d health_agent -c "SELECT * FROM user_onboarding_state ORDER BY started_at DESC LIMIT 5;"
PGPASSWORD=postgres psql -h localhost -U postgres -d health_agent -c "SELECT * FROM feature_discovery_log ORDER BY discovered_at DESC LIMIT 10;"
```

**Expected:** Bot responds correctly, database records created

---

## ACCEPTANCE CRITERIA

- [x] Three onboarding paths implemented (Quick Start, Full Tour, Just Chat)
- [x] Database tables created with proper indexes and constraints
- [x] All query functions implemented and tested
- [x] Onboarding state persists across bot restarts
- [x] Users can complete Quick Start in < 60 seconds
- [x] Full Tour showcases all major features interactively
- [x] Just Chat provides immediate value without tutorial
- [x] Feature discovery tracks usage across all handlers
- [x] /start command branches to onboarding or welcome based on state
- [x] Returning users see welcome message, not onboarding
- [x] All validation commands pass with zero errors
- [x] Unit test coverage > 80% for new code
- [x] Integration tests verify complete flows
- [x] Manual testing confirms UX matches strategy document
- [x] No regressions in existing functionality

---

## COMPLETION CHECKLIST

- [ ] Migration file created and applied successfully
- [ ] All query functions implemented in src/db/queries.py
- [ ] Onboarding models created in src/models/onboarding.py
- [ ] Onboarding handlers created in src/handlers/onboarding.py
- [ ] src/bot.py updated with onboarding routing
- [ ] Feature discovery logging added to existing handlers
- [ ] Unit tests created and passing
- [ ] Integration tests created and passing
- [ ] All validation commands executed successfully:
  - [ ] Syntax & type checking
  - [ ] Database migration applied
  - [ ] Unit tests pass with >80% coverage
  - [ ] Integration tests pass
  - [ ] Manual bot testing complete
- [ ] Database queries verified in psql
- [ ] Quick Start path tested end-to-end
- [ ] Full Tour path tested end-to-end
- [ ] Just Chat path tested end-to-end
- [ ] Feature discovery logging verified
- [ ] No existing tests broken (run full suite)
- [ ] Code reviewed for quality and maintainability

---

## NOTES

### Design Decisions

**1. Database-Driven State vs ConversationHandler**
- Decision: Use database state management
- Rationale: Matches existing codebase pattern (activation flow, timezone setup)
- Trade-off: Slightly more database queries, but consistent with project architecture

**2. Onboarding as Enhancement vs Separate System**
- Decision: Integrate into existing /start command and handle_message routing
- Rationale: Minimal changes to existing code, natural user flow
- Trade-off: More conditional logic in handlers, but better cohesion

**3. Three Paths vs Progressive Disclosure Only**
- Decision: Offer explicit path choice + contextual discovery
- Rationale: Research shows 77% abandon without quick value; choice respects user agency
- Trade-off: More code to maintain, but higher retention expected

### Implementation Risks

**Risk 1: Migration Failures**
- Mitigation: Test migration on empty database first, use IF NOT EXISTS
- Rollback: Migrations are idempotent and can be re-run

**Risk 2: State Synchronization Issues**
- Mitigation: All state changes go through single query functions with transactions
- Monitoring: Log all state transitions for debugging

**Risk 3: User Confusion with Multiple Paths**
- Mitigation: Clear descriptions of each path with time estimates
- Fallback: Just Chat path as catch-all for confused users

### Future Enhancements (Out of Scope)

- Day 2, 7, 14, 30 check-in messages (from strategy document)
- A/B testing framework for path selection copy
- Analytics dashboard for onboarding funnel analysis
- Resume onboarding from abandonment point
- Onboarding skip option for advanced users
- Personalized path recommendation based on user attributes

### Performance Considerations

- Database queries: ~2-4 queries per onboarding message (acceptable for low volume)
- Memory impact: Minimal (onboarding state is small JSONB)
- Bot response time: < 200ms for state lookups (connection pool handles this)

---

**Confidence Score:** 8/10 for one-pass implementation success

**Reasoning:**
- ✅ Comprehensive codebase analysis completed
- ✅ Clear patterns identified and documented
- ✅ External research incorporated
- ✅ Database schema well-defined
- ⚠️ Handler complexity moderate (many steps to implement)
- ⚠️ Manual testing required for full validation

**Estimated Implementation Time:** 6-8 hours for experienced developer

**Critical Path:** Database → Models → Handlers → Integration → Testing
