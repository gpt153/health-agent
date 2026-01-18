# Validation Layer Integration Guide

This guide shows how to integrate the new Pydantic validation layer into your handlers.

## Overview

The validation layer (`src/validators.py`) provides centralized input validation for:
- Message input (max 4000 chars, UTF-8 encoding)
- Nutrition values (ranges, no negatives, macro consistency)
- Date/time inputs (no future dates, valid timezones)
- Reminder frequency (intervals, operating hours, limits)

## Quick Start

```python
from src.validators import (
    MessageInput,
    NutritionValues,
    DateInput,
    ReminderFrequency,
    ReminderLimit,
    safe_validate,
    format_validation_error
)
```

## Integration Examples

### 1. Food Photo Handler

**File:** `src/handlers/food_photo.py`

```python
from telegram import Update
from telegram.ext import ContextTypes
from pydantic import ValidationError
from src.validators import MessageInput, NutritionValues, safe_validate

async def handle_food_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle food photo upload with validated caption"""

    # Validate caption if provided
    if update.message.caption:
        caption, error = safe_validate(MessageInput, text=update.message.caption)
        if error:
            await update.message.reply_text(error)
            return

        caption_text = caption.text
    else:
        caption_text = None

    # ... process food photo with AI ...

    # Validate AI nutrition response
    nutrition, error = safe_validate(
        NutritionValues,
        calories=ai_result.total_calories,
        protein=ai_result.total_macros.protein,
        carbs=ai_result.total_macros.carbs,
        fat=ai_result.total_macros.fat
    )

    if error:
        logger.warning(f"AI returned invalid nutrition: {error}")
        await update.message.reply_text(
            "⚠️ The AI estimate seems unusual. Please review:\n" +
            error +
            "\n\nWould you like to adjust the values?"
        )
        return

    # Save validated entry
    await save_food_entry(user_id, nutrition, caption_text)
```

### 2. Reminder Creation Handler

**File:** `src/handlers/reminders.py`

```python
from telegram import Update
from telegram.ext import ContextTypes
from datetime import time as dt_time
from src.validators import (
    MessageInput,
    ReminderFrequency,
    ReminderLimit,
    safe_validate
)

async def create_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new reminder with validation"""
    user_id = str(update.effective_user.id)

    # Check reminder limit first
    try:
        await ReminderLimit.check_daily_limit(user_id)
    except ValueError as e:
        await update.message.reply_text(str(e))
        return

    # Validate reminder message
    message, error = safe_validate(
        MessageInput,
        text=context.user_data.get('reminder_message')
    )
    if error:
        await update.message.reply_text(error)
        return

    # Validate reminder frequency
    frequency, error = safe_validate(
        ReminderFrequency,
        interval_minutes=context.user_data.get('interval', 1440),
        time_of_day=dt_time.fromisoformat(context.user_data.get('time')),
        days_of_week=context.user_data.get('days', [0,1,2,3,4,5,6]),
        user_timezone=context.user_data.get('timezone', 'UTC')
    )
    if error:
        await update.message.reply_text(error)
        return

    # Create reminder with validated data
    await create_reminder_in_db(
        user_id=user_id,
        message=message.text,
        time=context.user_data.get('time'),
        days=frequency.days_of_week,
        timezone=frequency.user_timezone
    )

    await update.message.reply_text(
        f"✅ Reminder created!\n"
        f"Message: {message.text}\n"
        f"Time: {context.user_data.get('time')}\n"
        f"Timezone: {frequency.user_timezone}"
    )
```

### 3. Onboarding Handler

**File:** `src/handlers/onboarding.py`

```python
from telegram import Update
from telegram.ext import ContextTypes
from src.validators import TimeInput, safe_validate

async def handle_timezone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Validate timezone during onboarding"""
    user_id = str(update.effective_user.id)
    user_input = update.message.text.strip()

    # Validate timezone
    from datetime import time as dt_time
    time_val, error = safe_validate(
        TimeInput,
        time_value=dt_time(12, 0),  # Dummy time for validation
        timezone=user_input
    )

    if error:
        await update.message.reply_text(
            error + "\n\n" +
            "Example valid timezones:\n"
            "• Europe/Stockholm\n"
            "• America/New_York\n"
            "• Asia/Tokyo\n\n"
            "Please try again:"
        )
        return

    # Save validated timezone
    await save_user_timezone(user_id, user_input)
    await update.message.reply_text(
        f"✅ Timezone set to {user_input}"
    )
```

### 4. General Message Handler

**File:** `src/handlers/message_handler.py`

```python
from telegram import Update
from telegram.ext import ContextTypes
from src.validators import MessageInput, safe_validate

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Validate and process general text messages"""

    # Validate message
    message, error = safe_validate(
        MessageInput,
        text=update.message.text
    )

    if error:
        await update.message.reply_text(error)
        return

    # Process validated message
    await process_user_message(message.text)
```

## Error Handling Best Practices

### Use safe_validate() for User-Friendly Errors

```python
# Good: User-friendly error messages
nutrition, error = safe_validate(
    NutritionValues,
    calories=data['calories'],
    protein=data['protein'],
    carbs=data['carbs'],
    fat=data['fat']
)
if error:
    await update.message.reply_text(error)  # Already formatted
    return
```

### Handle Validation Errors Gracefully

```python
try:
    reminder = Reminder(
        user_id=user_id,
        reminder_type="simple",
        message="Take medication",
        schedule=schedule
    )
except ValidationError as e:
    error_msg = format_validation_error(e)
    await update.message.reply_text(error_msg)
    logger.warning(f"Validation failed: {e}")
    return
```

### Provide Correction Hints

```python
if error:
    # Don't just show error - help user fix it
    if "too long" in error.lower():
        char_count = len(user_input)
        await update.message.reply_text(
            f"{error}\n\n"
            f"Your message is {char_count} characters. "
            f"Please shorten it to 4000 characters or less."
        )
    else:
        await update.message.reply_text(error)
    return
```

## Testing Your Integration

### Unit Test Example

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.handlers.food_photo import handle_food_photo

@pytest.mark.asyncio
async def test_food_photo_with_invalid_caption():
    """Test that invalid captions are rejected"""
    update = MagicMock()
    update.message.caption = "x" * 4001  # Too long
    update.message.reply_text = AsyncMock()

    context = MagicMock()

    await handle_food_photo(update, context)

    # Should have sent error message
    update.message.reply_text.assert_called_once()
    error_msg = update.message.reply_text.call_args[0][0]
    assert "❌" in error_msg
    assert "4000" in error_msg
```

### Integration Test Example

```python
@pytest.mark.asyncio
async def test_create_reminder_with_validation():
    """Test complete reminder creation with validation"""
    # Setup
    user_id = "test_user"

    # Test creating reminder at valid time
    update = create_mock_update(user_id)
    context = create_mock_context({
        'reminder_message': 'Take medication',
        'time': '08:00',
        'days': [0, 1, 2, 3, 4],  # Weekdays
        'timezone': 'Europe/Stockholm'
    })

    await create_reminder(update, context)

    # Should succeed
    update.message.reply_text.assert_called_once()
    response = update.message.reply_text.call_args[0][0]
    assert "✅" in response
```

## Common Validation Scenarios

### 1. Validating User Input from Conversation

```python
# In conversation handler
async def ask_for_calories(update, context):
    await update.message.reply_text("How many calories?")
    return CALORIES_STATE

async def receive_calories(update, context):
    try:
        calories = int(update.message.text)
        nutrition, error = safe_validate(
            NutritionValues,
            calories=calories,
            protein=0,  # Will fill later
            carbs=0,
            fat=0
        )
        if error:
            await update.message.reply_text(
                f"{error}\n\nPlease enter a value between 0 and 5000:"
            )
            return CALORIES_STATE

        context.user_data['calories'] = calories
        return NEXT_STATE
    except ValueError:
        await update.message.reply_text("Please enter a number:")
        return CALORIES_STATE
```

### 2. Validating API Request Data

```python
from fastapi import HTTPException
from src.validators import NutritionValues

@app.post("/api/v1/food")
async def create_food_entry(
    calories: int,
    protein: float,
    carbs: float,
    fat: float
):
    """API endpoint with validation"""
    nutrition, error = safe_validate(
        NutritionValues,
        calories=calories,
        protein=protein,
        carbs=carbs,
        fat=fat
    )

    if error:
        raise HTTPException(
            status_code=422,
            detail=error
        )

    # Process validated nutrition
    ...
```

### 3. Validating Legacy Data

```python
from src.models.food import FoodItem

def load_food_from_db(db_row):
    """Load food item with lenient validation for legacy data"""
    try:
        return FoodItem(**db_row)
    except ValidationError as e:
        logger.warning(f"Legacy data validation failed: {e}")
        # Sanitize and retry
        sanitized = {
            'name': db_row.get('name', 'Unknown'),
            'quantity': db_row.get('quantity', '1 serving'),
            'calories': max(0, min(5000, db_row.get('calories', 0))),
            'macros': {
                'protein': max(0, min(300, db_row.get('protein', 0))),
                'carbs': max(0, min(500, db_row.get('carbs', 0))),
                'fat': max(0, min(200, db_row.get('fat', 0)))
            }
        }
        return FoodItem(**sanitized)
```

## Validation Configuration

### Adjusting Operating Hours

Edit `src/validators.py`:

```python
class ReminderFrequency(BaseModel):
    # Change these constants
    MIN_HOUR: ClassVar[int] = 6   # Change to 5 for 5 AM
    MAX_HOUR: ClassVar[int] = 22  # Change to 23 for 11 PM
```

### Adjusting Reminder Limits

Edit `src/validators.py`:

```python
class ReminderLimit:
    MAX_REMINDERS: ClassVar[int] = 10  # Change to 15 for 15 max
```

### Adjusting Nutrition Ranges

Edit `src/validators.py`:

```python
class NutritionValues(BaseModel):
    calories: int = Field(ge=0, le=5000)  # Change le=10000 for higher limit
    protein: float = Field(ge=0, le=300)  # Adjust as needed
    carbs: float = Field(ge=0, le=500)
    fat: float = Field(ge=0, le=200)
```

## Monitoring and Logging

### Log Validation Failures

All validators automatically log warnings when validation fails:

```python
logger.warning(f"Validation failed for {model_class.__name__}: {error_msg}")
```

### Track Validation Metrics

```python
from src.validators import safe_validate

# Track validation failures
validation_failures = {}

nutrition, error = safe_validate(NutritionValues, **data)
if error:
    validation_failures['nutrition'] = validation_failures.get('nutrition', 0) + 1
    logger.info(f"Validation metrics: {validation_failures}")
```

## Migration Guide

### Step 1: Update Imports

```python
# Old
from src.models.food import FoodItem

# New (add validators)
from src.models.food import FoodItem
from src.validators import NutritionValues, safe_validate
```

### Step 2: Add Validation Before Database Operations

```python
# Old (no validation)
await save_food_entry(calories, protein, carbs, fat)

# New (with validation)
nutrition, error = safe_validate(
    NutritionValues,
    calories=calories,
    protein=protein,
    carbs=carbs,
    fat=fat
)
if error:
    await handle_error(error)
    return

await save_food_entry(nutrition.calories, nutrition.protein, ...)
```

### Step 3: Update Tests

```python
# Old
def test_create_food():
    food = create_food(calories=500, ...)

# New (handle validation)
def test_create_food():
    nutrition, error = safe_validate(NutritionValues, calories=500, ...)
    assert nutrition is not None
    assert error is None
```

## Summary

The validation layer provides:
- ✅ **Consistent validation** across all input points
- ✅ **User-friendly error messages** with emojis
- ✅ **Type safety** with Pydantic models
- ✅ **Easy integration** with existing handlers
- ✅ **Backward compatibility** with legacy data
- ✅ **Comprehensive testing** support

For more details, see:
- `src/validators.py` - Validator implementations
- `tests/test_validators.py` - Comprehensive test suite
- `src/models/food.py` - Enhanced food models
- `src/models/reminder.py` - Enhanced reminder models
