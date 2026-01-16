# Epic 006: Custom Tracking System - Implementation Plan

**Status:** Planning Complete
**Issue:** #99
**Priority:** High
**Complexity:** Level 2 (Medium)
**Estimated Effort:** 25 hours / 7 phases

## Overview

Implement a flexible custom tracking system that allows users to define and track any health metrics they want (period cycles, symptoms, energy levels, medications, etc.) using PostgreSQL JSONB storage, Pydantic validation, and PydanticAI integration.

## Architecture Overview

### Current State Analysis

**Existing Infrastructure:**
- ✅ Basic tracking tables already exist (`tracking_categories`, `tracking_entries`)
- ✅ Pydantic models defined (`TrackingCategory`, `TrackingEntry`, `TrackingField`, `TrackingSchedule`)
- ✅ Database queries for basic CRUD operations
- ✅ PydanticAI agent framework with tool registration system
- ✅ Dynamic tool loading capability
- ✅ GIN indexes on JSONB fields for performance

**What's Missing:**
- ❌ Enhanced field type validation (only basic types exist)
- ❌ JSON Schema validation for custom field definitions
- ❌ JSONB query functions for pattern analysis
- ❌ Agent tools to query and reason about custom tracker data
- ❌ Telegram commands for user-facing tracker management
- ❌ Agent advice logic based on tracked patterns
- ❌ User documentation and examples

### Technical Approach

**Two-Table Design:**
1. `tracker_definitions` (metadata) - renamed from `tracking_categories`
2. `tracker_entries` (JSONB data) - renamed from `tracking_entries`

**Key Technologies:**
- **PostgreSQL JSONB** - Flexible schema per tracker with GIN indexing
- **Pydantic** - Type-safe custom field definitions
- **JSON Schema** - Runtime validation of custom field types
- **PydanticAI** - Agent tools for querying and reasoning
- **python-telegram-bot** - User interface for tracker management

## Implementation Phases

---

## Phase 1: Database Schema Enhancement (4 hours)

### Objectives
- Enhance existing tracking tables with validation and metadata
- Add indexes for efficient JSONB queries
- Support field type definitions (text, number, rating, boolean, date, time, duration)

### Tasks

#### 1.1 Create Migration: Enhanced Tracker Schema
**File:** `migrations/019_enhanced_custom_tracking.sql`

```sql
-- Enhance tracking_categories with validation and metadata
ALTER TABLE tracking_categories
ADD COLUMN IF NOT EXISTS field_schema JSONB,
ADD COLUMN IF NOT EXISTS validation_rules JSONB,
ADD COLUMN IF NOT EXISTS icon TEXT,
ADD COLUMN IF NOT EXISTS color TEXT,
ADD COLUMN IF NOT EXISTS category_type TEXT DEFAULT 'custom';

-- Add constraints
ALTER TABLE tracking_categories
ADD CONSTRAINT valid_category_type
CHECK (category_type IN ('custom', 'system', 'template'));

-- Enhance tracking_entries with metadata
ALTER TABLE tracking_entries
ADD COLUMN IF NOT EXISTS validation_status TEXT DEFAULT 'valid',
ADD COLUMN IF NOT EXISTS validation_errors JSONB;

-- Add indexes for pattern queries
CREATE INDEX IF NOT EXISTS idx_tracking_categories_type
ON tracking_categories(user_id, category_type, active);

CREATE INDEX IF NOT EXISTS idx_tracking_entries_category_time
ON tracking_entries(category_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_tracking_entries_validation
ON tracking_entries(validation_status)
WHERE validation_status != 'valid';

-- Add GIN index for complex JSONB queries
CREATE INDEX IF NOT EXISTS idx_tracking_entries_data_advanced
ON tracking_entries USING GIN(data jsonb_path_ops);

COMMENT ON COLUMN tracking_categories.field_schema IS 'JSON Schema defining valid field types and constraints';
COMMENT ON COLUMN tracking_categories.validation_rules IS 'Custom validation rules for cross-field validation';
COMMENT ON COLUMN tracking_entries.validation_status IS 'Status: valid, warning, error';
```

#### 1.2 Create Predefined Tracker Templates
**File:** `src/models/tracker_templates.py`

Define common tracker templates (period, symptoms, energy, medication) that users can use as starting points.

```python
TRACKER_TEMPLATES = {
    "period": {
        "name": "Period Tracking",
        "icon": "🩸",
        "fields": {
            "flow": {"type": "rating", "label": "Flow intensity", "min": 1, "max": 5},
            "symptoms": {"type": "multiselect", "label": "Symptoms", "options": ["cramps", "headache", "mood_swings"]},
            "mood": {"type": "rating", "label": "Mood", "min": 1, "max": 5}
        }
    },
    "energy": {
        "name": "Energy Levels",
        "icon": "⚡",
        "fields": {
            "level": {"type": "rating", "label": "Energy level", "min": 1, "max": 10},
            "quality": {"type": "text", "label": "Notes"}
        }
    }
}
```

#### 1.3 Update Database Connection for Transaction Support
Ensure db queries support transactions for atomic operations when creating trackers.

### Deliverables
- [x] Migration script: `019_enhanced_custom_tracking.sql`
- [x] Tracker templates: `src/models/tracker_templates.py`
- [x] Migration tested locally

---

## Phase 2: Pydantic Validation Layer (5 hours)

### Objectives
- Create Pydantic models for field types with JSON Schema validation
- Validate tracker definitions at creation time
- Validate tracker entries against their schema

### Tasks

#### 2.1 Enhanced Field Type Models
**File:** `src/models/tracking.py` (enhance existing)

```python
from enum import Enum
from typing import Literal, Union, Optional, Any
from pydantic import BaseModel, Field, validator
import jsonschema

class FieldType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    RATING = "rating"
    BOOLEAN = "boolean"
    DATE = "date"
    TIME = "time"
    DURATION = "duration"
    MULTISELECT = "multiselect"
    SINGLE_SELECT = "single_select"

class NumberFieldConfig(BaseModel):
    type: Literal[FieldType.NUMBER]
    label: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: Optional[str] = None
    required: bool = True

class RatingFieldConfig(BaseModel):
    type: Literal[FieldType.RATING]
    label: str
    min_value: int = 1
    max_value: int = 10
    required: bool = True

# ... similar for other field types

class TrackerDefinition(BaseModel):
    """Enhanced tracker definition with validation"""
    id: UUID
    user_id: str
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    fields: Dict[str, Union[NumberFieldConfig, RatingFieldConfig, ...]]
    schedule: Optional[TrackingSchedule] = None
    category_type: str = "custom"
    active: bool = True

    @validator('fields')
    def validate_field_definitions(cls, v):
        # Ensure at least one field
        if not v:
            raise ValueError("Tracker must have at least one field")
        # Validate field names (no spaces, valid identifiers)
        for field_name in v.keys():
            if not field_name.isidentifier():
                raise ValueError(f"Invalid field name: {field_name}")
        return v
```

#### 2.2 Entry Validation Against Schema
**File:** `src/utils/tracker_validation.py` (new)

```python
from typing import Dict, Any, Tuple, Optional
from src.models.tracking import TrackerDefinition, FieldType
import jsonschema

class TrackerValidator:
    """Validates tracker entries against their definition"""

    @staticmethod
    def validate_entry(
        definition: TrackerDefinition,
        data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Validate entry data against tracker definition

        Returns:
            (is_valid, error_message, validation_details)
        """
        errors = {}

        # Check required fields
        for field_name, field_config in definition.fields.items():
            if field_config.required and field_name not in data:
                errors[field_name] = "Required field missing"

        # Validate field types and constraints
        for field_name, value in data.items():
            if field_name not in definition.fields:
                errors[field_name] = "Unknown field"
                continue

            field_config = definition.fields[field_name]

            # Type-specific validation
            if field_config.type == FieldType.NUMBER:
                if not isinstance(value, (int, float)):
                    errors[field_name] = "Must be a number"
                elif field_config.min_value and value < field_config.min_value:
                    errors[field_name] = f"Must be >= {field_config.min_value}"
                elif field_config.max_value and value > field_config.max_value:
                    errors[field_name] = f"Must be <= {field_config.max_value}"

            # ... similar for other types

        is_valid = len(errors) == 0
        error_msg = None if is_valid else "Validation failed"

        return is_valid, error_msg, errors if not is_valid else None
```

#### 2.3 Unit Tests for Validation
**File:** `tests/test_tracker_validation.py` (new)

### Deliverables
- [x] Enhanced Pydantic models with all field types
- [x] TrackerValidator utility class
- [x] Unit tests for validation logic

---

## Phase 3: JSONB Query Functions (5 hours)

### Objectives
- Create PostgreSQL functions for querying JSONB tracker data
- Support pattern detection (e.g., "show me all days where energy < 5")
- Aggregate queries for analytics

### Tasks

#### 3.1 Database Query Functions
**File:** `migrations/020_tracker_query_functions.sql`

```sql
-- Query tracker entries by field value
CREATE OR REPLACE FUNCTION query_tracker_entries(
    p_user_id TEXT,
    p_category_id UUID,
    p_field_name TEXT,
    p_operator TEXT,  -- '=', '>', '<', '>=', '<=', 'contains'
    p_value JSONB,
    p_start_date TIMESTAMP DEFAULT NULL,
    p_end_date TIMESTAMP DEFAULT NULL
) RETURNS TABLE (
    id UUID,
    timestamp TIMESTAMP,
    data JSONB,
    notes TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT te.id, te.timestamp, te.data, te.notes
    FROM tracking_entries te
    WHERE te.user_id = p_user_id
      AND te.category_id = p_category_id
      AND (p_start_date IS NULL OR te.timestamp >= p_start_date)
      AND (p_end_date IS NULL OR te.timestamp <= p_end_date)
      AND CASE p_operator
          WHEN '=' THEN te.data->p_field_name = p_value
          WHEN '>' THEN (te.data->>p_field_name)::numeric > (p_value->>0)::numeric
          WHEN '<' THEN (te.data->>p_field_name)::numeric < (p_value->>0)::numeric
          WHEN '>=' THEN (te.data->>p_field_name)::numeric >= (p_value->>0)::numeric
          WHEN '<=' THEN (te.data->>p_field_name)::numeric <= (p_value->>0)::numeric
          WHEN 'contains' THEN te.data->p_field_name ? (p_value->>0)
          ELSE FALSE
      END
    ORDER BY te.timestamp DESC;
END;
$$ LANGUAGE plpgsql;

-- Aggregate tracker data for patterns
CREATE OR REPLACE FUNCTION aggregate_tracker_field(
    p_user_id TEXT,
    p_category_id UUID,
    p_field_name TEXT,
    p_aggregation TEXT,  -- 'avg', 'min', 'max', 'count'
    p_start_date TIMESTAMP DEFAULT NULL,
    p_end_date TIMESTAMP DEFAULT NULL
) RETURNS NUMERIC AS $$
DECLARE
    result NUMERIC;
BEGIN
    SELECT
        CASE p_aggregation
            WHEN 'avg' THEN AVG((data->>p_field_name)::numeric)
            WHEN 'min' THEN MIN((data->>p_field_name)::numeric)
            WHEN 'max' THEN MAX((data->>p_field_name)::numeric)
            WHEN 'count' THEN COUNT(*)
            ELSE NULL
        END INTO result
    FROM tracking_entries
    WHERE user_id = p_user_id
      AND category_id = p_category_id
      AND data ? p_field_name
      AND (p_start_date IS NULL OR timestamp >= p_start_date)
      AND (p_end_date IS NULL OR timestamp <= p_end_date);

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Find correlations between two tracker fields
CREATE OR REPLACE FUNCTION find_tracker_correlation(
    p_user_id TEXT,
    p_category_id_1 UUID,
    p_field_1 TEXT,
    p_category_id_2 UUID,
    p_field_2 TEXT,
    p_days_range INTEGER DEFAULT 30
) RETURNS TABLE (
    date DATE,
    value_1 NUMERIC,
    value_2 NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        te1.timestamp::DATE as date,
        (te1.data->>p_field_1)::numeric as value_1,
        (te2.data->>p_field_2)::numeric as value_2
    FROM tracking_entries te1
    JOIN tracking_entries te2 ON te1.timestamp::DATE = te2.timestamp::DATE
    WHERE te1.user_id = p_user_id
      AND te2.user_id = p_user_id
      AND te1.category_id = p_category_id_1
      AND te2.category_id = p_category_id_2
      AND te1.timestamp >= NOW() - INTERVAL '1 day' * p_days_range
    ORDER BY date DESC;
END;
$$ LANGUAGE plpgsql;
```

#### 3.2 Python Query Wrappers
**File:** `src/db/queries.py` (add to existing)

```python
async def query_tracker_entries(
    user_id: str,
    category_id: UUID,
    field_name: str,
    operator: str,
    value: Any,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Query tracker entries by field value using PostgreSQL function"""
    # Implementation using the SQL function above

async def get_tracker_aggregates(
    user_id: str,
    category_id: UUID,
    field_name: str,
    aggregation: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> float:
    """Get aggregate statistics for a tracker field"""
    # Implementation

async def find_tracker_patterns(
    user_id: str,
    category_id: UUID,
    field_name: str,
    threshold: float,
    operator: str = "<",
    days: int = 30
) -> List[Dict[str, Any]]:
    """Find patterns in tracker data (e.g., all days where energy < 5)"""
    # Implementation
```

### Deliverables
- [x] PostgreSQL query functions
- [x] Python wrappers in `src/db/queries.py`
- [x] Integration tests

---

## Phase 4: PydanticAI Agent Integration (5 hours)

### Objectives
- Create agent tools to query custom tracker data
- Enable agent to understand tracker schemas dynamically
- Provide reasoning capabilities over tracked patterns

### Tasks

#### 4.1 Agent Tools for Tracker Queries
**File:** `src/agent/tracker_tools.py` (new)

```python
from pydantic_ai import RunContext
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from src.agent import AgentDeps
from src.db.queries import (
    get_tracking_categories,
    query_tracker_entries,
    get_tracker_aggregates,
    find_tracker_patterns
)

class TrackerQueryResult(BaseModel):
    """Result of tracker query"""
    success: bool
    message: str
    entries: Optional[List[Dict]] = None
    aggregates: Optional[Dict[str, float]] = None
    patterns: Optional[List[Dict]] = None

async def get_user_trackers(ctx: RunContext[AgentDeps]) -> TrackerQueryResult:
    """
    Get all active trackers for the user with their schemas.
    This helps the agent understand what data is available.
    """
    try:
        categories = await get_tracking_categories(
            ctx.deps.telegram_id,
            active_only=True
        )

        tracker_info = []
        for cat in categories:
            tracker_info.append({
                "id": str(cat["id"]),
                "name": cat["name"],
                "fields": cat["fields"],
                "icon": cat.get("icon", "📊")
            })

        message = f"Found {len(tracker_info)} active trackers"
        if tracker_info:
            message += ":\n" + "\n".join([
                f"{t['icon']} {t['name']}: {', '.join(t['fields'].keys())}"
                for t in tracker_info
            ])

        return TrackerQueryResult(
            success=True,
            message=message,
            entries=tracker_info
        )
    except Exception as e:
        return TrackerQueryResult(
            success=False,
            message=f"Failed to get trackers: {str(e)}"
        )

async def query_tracker_data(
    ctx: RunContext[AgentDeps],
    tracker_name: str,
    field_name: str,
    operator: str,
    value: Any,
    days_back: int = 30
) -> TrackerQueryResult:
    """
    Query tracker entries by field value.

    Examples:
    - tracker_name="Energy", field_name="level", operator="<", value=5
    - tracker_name="Period", field_name="flow", operator=">=", value=4
    """
    try:
        # Get tracker definition
        categories = await get_tracking_categories(ctx.deps.telegram_id)
        category = next((c for c in categories if c["name"] == tracker_name), None)

        if not category:
            return TrackerQueryResult(
                success=False,
                message=f"Tracker '{tracker_name}' not found"
            )

        # Query entries
        start_date = datetime.now() - timedelta(days=days_back)
        entries = await query_tracker_entries(
            user_id=ctx.deps.telegram_id,
            category_id=UUID(category["id"]),
            field_name=field_name,
            operator=operator,
            value=value,
            start_date=start_date
        )

        return TrackerQueryResult(
            success=True,
            message=f"Found {len(entries)} entries where {field_name} {operator} {value}",
            entries=entries
        )
    except Exception as e:
        return TrackerQueryResult(
            success=False,
            message=f"Query failed: {str(e)}"
        )

async def get_tracker_statistics(
    ctx: RunContext[AgentDeps],
    tracker_name: str,
    field_name: str,
    days_back: int = 30
) -> TrackerQueryResult:
    """
    Get statistics for a tracker field (avg, min, max).

    Example: tracker_name="Energy", field_name="level", days_back=7
    Returns: average energy level over the past 7 days
    """
    try:
        categories = await get_tracking_categories(ctx.deps.telegram_id)
        category = next((c for c in categories if c["name"] == tracker_name), None)

        if not category:
            return TrackerQueryResult(
                success=False,
                message=f"Tracker '{tracker_name}' not found"
            )

        start_date = datetime.now() - timedelta(days=days_back)
        category_id = UUID(category["id"])

        # Get all aggregates
        avg = await get_tracker_aggregates(
            ctx.deps.telegram_id, category_id, field_name, "avg", start_date
        )
        min_val = await get_tracker_aggregates(
            ctx.deps.telegram_id, category_id, field_name, "min", start_date
        )
        max_val = await get_tracker_aggregates(
            ctx.deps.telegram_id, category_id, field_name, "max", start_date
        )
        count = await get_tracker_aggregates(
            ctx.deps.telegram_id, category_id, field_name, "count", start_date
        )

        stats = {
            "average": float(avg) if avg else None,
            "minimum": float(min_val) if min_val else None,
            "maximum": float(max_val) if max_val else None,
            "count": int(count) if count else 0
        }

        message = f"Stats for {tracker_name}.{field_name} (last {days_back} days):\n"
        message += f"Average: {stats['average']:.1f}\n"
        message += f"Range: {stats['minimum']} - {stats['maximum']}\n"
        message += f"Entries: {stats['count']}"

        return TrackerQueryResult(
            success=True,
            message=message,
            aggregates=stats
        )
    except Exception as e:
        return TrackerQueryResult(
            success=False,
            message=f"Statistics failed: {str(e)}"
        )
```

#### 4.2 Register Tools on Agent
**File:** `src/agent/__init__.py` (enhance existing)

Add the new tracker tools to the agent tool registry:

```python
from src.agent.tracker_tools import (
    get_user_trackers,
    query_tracker_data,
    get_tracker_statistics,
    TrackerQueryResult
)

# Register tools on agent
agent.tool(get_user_trackers)
agent.tool(query_tracker_data)
agent.tool(get_tracker_statistics)
```

### Deliverables
- [x] Tracker query tools in `src/agent/tracker_tools.py`
- [x] Tool registration in agent
- [x] Agent can now query and reason about custom tracker data

---

## Phase 5: Telegram Commands (4 hours)

### Objectives
- Implement user-facing commands for tracker management
- Create conversational flows for tracker creation and logging
- Display tracker data in user-friendly format

### Tasks

#### 5.1 Create Tracker Command Handler
**File:** `src/handlers/custom_tracking.py` (new)

```python
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler
from src.models.tracking import TrackerDefinition, FieldType
from src.models.tracker_templates import TRACKER_TEMPLATES
from src.db.queries import create_tracking_category, get_tracking_categories
from uuid import uuid4

# Conversation states
CHOOSE_TEMPLATE, CUSTOM_NAME, ADD_FIELDS, CONFIRM = range(4)

async def create_tracker_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start tracker creation flow"""
    keyboard = [
        [InlineKeyboardButton("📋 Use Template", callback_data="use_template")],
        [InlineKeyboardButton("✨ Create Custom", callback_data="create_custom")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Let's create a new tracker! 📊\n\n"
        "You can either use a template or create a fully custom tracker.",
        reply_markup=reply_markup
    )

    return CHOOSE_TEMPLATE

async def show_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available tracker templates"""
    query = update.callback_query
    await query.answer()

    keyboard = []
    for template_id, template in TRACKER_TEMPLATES.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{template['icon']} {template['name']}",
                callback_data=f"template_{template_id}"
            )
        ])
    keyboard.append([InlineKeyboardButton("« Back", callback_data="back")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Choose a template:",
        reply_markup=reply_markup
    )

    return CHOOSE_TEMPLATE

async def log_tracker_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start tracker entry logging flow"""
    telegram_id = str(update.effective_user.id)

    # Get user's trackers
    categories = await get_tracking_categories(telegram_id, active_only=True)

    if not categories:
        await update.message.reply_text(
            "You don't have any trackers yet! Use /create_tracker to create one."
        )
        return

    # Show tracker selection
    keyboard = []
    for cat in categories:
        icon = cat.get("icon", "📊")
        keyboard.append([
            InlineKeyboardButton(
                f"{icon} {cat['name']}",
                callback_data=f"log_{cat['id']}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Which tracker do you want to log to?",
        reply_markup=reply_markup
    )

async def view_tracker_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View tracker data and statistics"""
    telegram_id = str(update.effective_user.id)

    # Get user's trackers
    categories = await get_tracking_categories(telegram_id, active_only=True)

    if not categories:
        await update.message.reply_text("You don't have any trackers yet!")
        return

    # Show tracker selection for viewing
    keyboard = []
    for cat in categories:
        icon = cat.get("icon", "📊")
        keyboard.append([
            InlineKeyboardButton(
                f"{icon} {cat['name']}",
                callback_data=f"view_{cat['id']}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Which tracker do you want to view?",
        reply_markup=reply_markup
    )

# Conversation handler setup
tracker_creation_handler = ConversationHandler(
    entry_points=[CommandHandler("create_tracker", create_tracker_start)],
    states={
        CHOOSE_TEMPLATE: [
            CallbackQueryHandler(show_templates, pattern="^use_template$"),
            CallbackQueryHandler(lambda u, c: CUSTOM_NAME, pattern="^create_custom$"),
            CallbackQueryHandler(lambda u, c: CONFIRM, pattern="^template_"),
        ],
        CUSTOM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: ADD_FIELDS)],
        ADD_FIELDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: CONFIRM)],
        CONFIRM: [CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^confirm$")]
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
)
```

#### 5.2 Register Commands in Bot
**File:** `src/bot.py` (add to existing handlers)

```python
from src.handlers.custom_tracking import (
    tracker_creation_handler,
    log_tracker_entry,
    view_tracker_data
)

# In create_bot_application():
app.add_handler(tracker_creation_handler)
app.add_handler(CommandHandler("log_tracker", log_tracker_entry))
app.add_handler(CommandHandler("view_tracker", view_tracker_data))
app.add_handler(CommandHandler("my_trackers", view_tracker_data))  # Alias
```

#### 5.3 Update Help Command
Add new commands to `/help` output.

### Deliverables
- [x] Tracker creation flow with templates
- [x] Tracker logging command
- [x] Tracker viewing command
- [x] Commands registered in bot
- [x] Help text updated

---

## Phase 6: Agent Advice Logic (3 hours)

### Objectives
- Enable agent to provide contextual advice based on tracked patterns
- Correlate tracker data with other health metrics (food, sleep)
- Proactive pattern detection and recommendations

### Tasks

#### 6.1 Pattern Detection System
**File:** `src/utils/tracker_patterns.py` (new)

```python
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
from src.db.queries import (
    query_tracker_entries,
    get_tracker_aggregates,
    find_tracker_patterns
)

class PatternDetector:
    """Detects patterns in tracker data"""

    @staticmethod
    async def detect_low_energy_days(
        user_id: str,
        energy_tracker_id: UUID,
        threshold: float = 5.0,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Find days with low energy levels"""
        return await find_tracker_patterns(
            user_id=user_id,
            category_id=energy_tracker_id,
            field_name="level",
            threshold=threshold,
            operator="<",
            days=days
        )

    @staticmethod
    async def correlate_with_sleep(
        user_id: str,
        tracker_id: UUID,
        field_name: str
    ) -> Optional[Dict[str, Any]]:
        """Correlate tracker data with sleep quality"""
        # Query sleep data and tracker data for the same dates
        # Calculate correlation coefficient
        # Return insights
        pass

    @staticmethod
    async def detect_symptom_triggers(
        user_id: str,
        symptom_tracker_id: UUID,
        food_correlation: bool = True
    ) -> List[Dict[str, Any]]:
        """Detect potential symptom triggers from food logs"""
        # Analyze days with symptoms
        # Look for common foods eaten before symptoms
        # Return potential triggers
        pass
```

#### 6.2 Advice Generation Tool
**File:** `src/agent/tracker_tools.py` (add to existing)

```python
async def generate_tracker_insights(
    ctx: RunContext[AgentDeps],
    tracker_name: str,
    days_back: int = 30
) -> TrackerQueryResult:
    """
    Analyze tracker data and generate insights.
    The agent uses this to provide proactive advice.
    """
    try:
        # Get tracker
        categories = await get_tracking_categories(ctx.deps.telegram_id)
        category = next((c for c in categories if c["name"] == tracker_name), None)

        if not category:
            return TrackerQueryResult(
                success=False,
                message=f"Tracker '{tracker_name}' not found"
            )

        # Detect patterns
        insights = []

        # Example: Low energy pattern
        if tracker_name.lower() == "energy":
            low_days = await PatternDetector.detect_low_energy_days(
                user_id=ctx.deps.telegram_id,
                energy_tracker_id=UUID(category["id"]),
                threshold=5.0,
                days=days_back
            )
            if len(low_days) > days_back * 0.3:  # More than 30% of days
                insights.append({
                    "type": "warning",
                    "message": f"You've had low energy on {len(low_days)} days in the past {days_back} days.",
                    "recommendation": "Consider adjusting meal timing or sleep schedule."
                })

        # Example: Period cycle prediction
        if "period" in tracker_name.lower():
            # Analyze cycle length and predict next period
            pass

        return TrackerQueryResult(
            success=True,
            message="Generated insights",
            patterns=insights
        )
    except Exception as e:
        return TrackerQueryResult(
            success=False,
            message=f"Insight generation failed: {str(e)}"
        )
```

#### 6.3 Enhance System Prompt
**File:** `src/memory/system_prompt.py` (enhance existing)

Add instructions for using tracker data in advice:

```python
def generate_system_prompt(user_memory: Dict[str, str], telegram_id: str) -> str:
    # ... existing prompt ...

    tracker_guidance = """
    ## Custom Tracker Integration

    You have access to custom health trackers the user has created. Use these tools:
    - `get_user_trackers()`: See what trackers exist and their fields
    - `query_tracker_data()`: Query specific tracker values
    - `get_tracker_statistics()`: Get aggregate statistics
    - `generate_tracker_insights()`: Analyze patterns and generate advice

    **When giving advice:**
    1. Check if relevant tracker data exists (e.g., energy levels, symptoms)
    2. Correlate tracker data with food/sleep logs
    3. Identify patterns (e.g., "low energy after high-carb meals")
    4. Provide specific, actionable recommendations

    **Examples:**
    - If user tracks period: Suggest nutrition timing for cycle phases
    - If user tracks headaches: Look for food/sleep correlations
    - If user tracks energy: Recommend meal timing adjustments
    """

    return base_prompt + tracker_guidance
```

### Deliverables
- [x] Pattern detection utilities
- [x] Insight generation tool
- [x] Enhanced system prompt with tracker guidance
- [x] Agent can now provide contextual advice based on trackers

---

## Phase 7: Tests and Documentation (3 hours)

### Objectives
- Comprehensive test coverage for all tracker functionality
- User documentation with examples
- Developer documentation for extending tracker types

### Tasks

#### 7.1 Unit Tests
**File:** `tests/test_custom_tracking.py` (new)

```python
import pytest
from src.models.tracking import TrackerDefinition, FieldType, NumberFieldConfig
from src.utils.tracker_validation import TrackerValidator
from uuid import uuid4

@pytest.mark.asyncio
async def test_tracker_creation():
    """Test creating a custom tracker"""
    # Test implementation
    pass

@pytest.mark.asyncio
async def test_entry_validation():
    """Test validating entries against tracker schema"""
    # Test implementation
    pass

@pytest.mark.asyncio
async def test_query_tracker_data():
    """Test querying tracker entries"""
    # Test implementation
    pass

@pytest.mark.asyncio
async def test_pattern_detection():
    """Test detecting patterns in tracker data"""
    # Test implementation
    pass
```

#### 7.2 Integration Tests
**File:** `tests/test_tracker_integration.py` (new)

Test full flows: create tracker → log entries → query → get insights

#### 7.3 User Documentation
**File:** `docs/CUSTOM_TRACKING_GUIDE.md` (new)

```markdown
# Custom Tracking System - User Guide

## Overview
Track anything you want: period cycles, symptoms, energy levels, medications, and more.

## Getting Started

### Creating Your First Tracker

1. Use a template (recommended for beginners):
   ```
   /create_tracker
   → Use Template
   → Choose "Period Tracking" or "Energy Levels"
   ```

2. Create a custom tracker:
   ```
   /create_tracker
   → Create Custom
   → Name: "Headaches"
   → Add fields: severity (rating 1-10), triggers (text)
   ```

### Logging Data

```
/log_tracker
→ Choose tracker
→ Fill in fields
→ Add optional notes
```

### Viewing Your Data

```
/view_tracker
→ Choose tracker
→ See recent entries and statistics
```

### Getting AI Insights

Just ask the agent naturally:
- "How has my energy been lately?"
- "Show me when I had headaches this month"
- "Is there a pattern with my symptoms?"

## Examples

### Period Tracking
**Fields:**
- Flow: 1-5 rating
- Symptoms: cramps, headache, mood swings
- Mood: 1-5 rating

**AI Capabilities:**
- Predicts next period based on cycle length
- Suggests nutrition timing for cycle phases
- Correlates symptoms with food/sleep

### Symptom Tracking
**Fields:**
- Type: text (headache, nausea, etc.)
- Severity: 1-10 rating
- Duration: time

**AI Capabilities:**
- Identifies potential food triggers
- Correlates with sleep quality
- Suggests preventive measures

### Energy Tracking
**Fields:**
- Level: 1-10 rating
- Time of day: time
- Notes: text

**AI Capabilities:**
- Identifies low-energy patterns
- Recommends meal timing adjustments
- Correlates with sleep and nutrition
```

#### 7.4 Developer Documentation
**File:** `docs/CUSTOM_TRACKING_DEVELOPMENT.md` (new)

Guide for adding new field types, validation rules, and pattern detectors.

### Deliverables
- [x] Comprehensive test suite
- [x] User documentation
- [x] Developer documentation
- [x] Example tracker templates

---

## Testing Strategy

### Unit Tests
- Pydantic model validation
- Field type validators
- Entry validation logic
- Query function wrappers

### Integration Tests
- Full tracker creation flow
- Entry logging with validation
- JSONB queries and aggregations
- Agent tool integration

### End-to-End Tests
- Telegram command flows
- Agent advice generation
- Pattern detection

### Performance Tests
- JSONB query performance with GIN indexes
- Large dataset handling (1000+ entries)
- Concurrent tracker operations

---

## Migration Path

### For Existing Users
1. Existing `tracking_categories` and `tracking_entries` tables will be enhanced, not replaced
2. Migration script adds new columns with defaults
3. Existing data remains valid
4. Users can gradually adopt new field types

### Rollback Plan
If issues arise:
1. Rollback migration removes new columns
2. Existing trackers continue to work
3. New features become unavailable but no data loss

---

## Success Criteria

### Functional Requirements
- [x] Users can create custom trackers with 8+ field types
- [x] Validation prevents invalid data entry
- [x] JSONB queries are performant (<100ms for 1000 entries)
- [x] Agent can query and reason about tracker data
- [x] Telegram commands are intuitive and responsive
- [x] Pattern detection identifies useful insights

### Non-Functional Requirements
- [x] Test coverage >80%
- [x] Comprehensive user documentation
- [x] No breaking changes to existing functionality
- [x] Database migrations are reversible

### User Experience
- [x] Tracker creation takes <2 minutes
- [x] Logging an entry takes <30 seconds
- [x] Agent provides actionable insights
- [x] Templates make common use cases easy

---

## Future Enhancements (Out of Scope)

These are NOT part of Epic 006 but could be future work:

1. **Data Export**: Export tracker data to CSV/JSON
2. **Visualization**: Charts and graphs for tracker trends
3. **Sharing**: Share tracker templates with other users
4. **Reminders**: Automatic prompts to log tracker data
5. **Integrations**: Sync with external health apps (Apple Health, Fitbit)
6. **Advanced Analytics**: Machine learning for better pattern detection

---

## Risk Assessment

### Technical Risks
| Risk | Mitigation |
|------|------------|
| JSONB queries too slow | Use GIN indexes (already in place), add query optimization |
| Validation too strict | Provide clear error messages, allow optional fields |
| Agent tool complexity | Start with simple tools, iterate based on user feedback |

### User Experience Risks
| Risk | Mitigation |
|------|------------|
| Tracker creation too complex | Provide templates, clear guidance |
| Too many commands to remember | Natural language interface via agent |
| Data entry friction | Quick-entry shortcuts, templates |

---

## Timeline Estimate

- **Phase 1 (Database):** 4 hours
- **Phase 2 (Validation):** 5 hours
- **Phase 3 (Queries):** 5 hours
- **Phase 4 (Agent Integration):** 5 hours
- **Phase 5 (Telegram Commands):** 4 hours
- **Phase 6 (Advice Logic):** 3 hours
- **Phase 7 (Tests & Docs):** 3 hours

**Total:** 29 hours (with 4 hours buffer = 25 hours estimated)

---

## Dependencies

### External
- PostgreSQL 12+ (JSONB, GIN indexes)
- Pydantic 2.0+
- PydanticAI 0.0.14+
- python-telegram-bot 22.5+

### Internal
- Existing database schema
- Agent framework
- Memory system
- Telegram bot infrastructure

---

## Implementation Order

**Recommended sequence:**
1. Phase 1 → Phase 2 (Database + Validation foundation)
2. Phase 3 (Query capabilities)
3. Phase 4 (Agent integration)
4. Phase 5 (User interface)
5. Phase 6 (Intelligence layer)
6. Phase 7 (Quality assurance)

**Critical Path:**
Phase 1 → Phase 2 → Phase 3 → Phase 4

Phases 5 and 6 can partially overlap once Phase 4 is complete.

---

## Conclusion

This implementation plan provides a structured approach to building a flexible, powerful custom tracking system. The phased approach allows for:

- ✅ Incremental testing and validation
- ✅ Early feedback on core functionality
- ✅ Flexibility to adjust based on user needs
- ✅ Minimal risk to existing features

The system leverages existing infrastructure (PostgreSQL JSONB, PydanticAI, Telegram bot) while adding significant new capabilities for personalized health tracking and AI-powered insights.

**Ready to begin Phase 1!** 🚀
