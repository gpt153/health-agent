# Implementation Plan: Pydantic Input Validation Layer (Issue #69)

**Epic:** 007 - Phase 2.4 High-Priority Refactoring
**Priority:** HIGH
**Estimated Time:** 3 hours
**Status:** Planning Complete

---

## Overview

Create a centralized Pydantic validation layer (`src/validators.py`) to enforce input constraints across all user inputs in the health agent. This will prevent invalid data from reaching the database and ensure consistency in data validation.

## Requirements Analysis

### 1. Message Input Validation
- **Max length:** 4000 characters (Telegram limit)
- **Required fields:** Enforce non-empty strings where needed
- **Encoding:** Validate UTF-8 encoding
- **Use cases:**
  - Reminder messages
  - Custom notes
  - User text input during onboarding
  - Food descriptions/captions

### 2. Nutrition Value Validation
- **No negative values:** All nutrition values must be >= 0
- **Reasonable ranges:**
  - Calories: 0-5000 kcal (single meal/day limit)
  - Protein: 0-300g (realistic daily limit)
  - Carbs: 0-500g (realistic daily limit)
  - Fat: 0-200g (realistic daily limit)
- **Macro consistency:** Validate that macros roughly match calories (4-4-9 rule)

### 3. Date Validation
- **No future dates:** For food logging, sleep tracking, etc.
- **Valid range:** Not before 2020-01-01, not after today
- **Timezone awareness:** Handle timezone conversions properly

### 4. Reminder Frequency Validation
- **Time intervals:** 15min - 24hr
- **Operating hours:** 6AM - 10PM (configurable per user timezone)
- **Daily limit:** Max 10 reminders per day per user
- **Valid days:** 0-6 (Monday-Sunday)

---

## Current State Analysis

### Existing Validation
The codebase already has validation logic scattered across multiple files:

1. **`src/utils/nutrition_validation.py`** (419 lines)
   - Validates nutrition estimates against USDA ranges
   - Checks reasonableness of calorie/macro values
   - Food quantity parsing

2. **`src/utils/reasonableness_rules.py`** (295 lines)
   - Category-based calorie ranges
   - Protein ranges by food type
   - Food categorization logic

3. **`src/agent/nutrition_validator.py`** (292 lines)
   - Cross-model validation (OpenAI vs Anthropic)
   - USDA comparison
   - Multi-agent validation orchestration

4. **`src/models/*.py`** files
   - Pydantic models exist for: Food, Reminder, Tracking, Sleep, User, etc.
   - Currently have minimal field-level validation

### Current Pydantic Usage
- Pydantic **v2.0+** is already installed
- `@field_validator` decorators are mentioned in the issue but not yet used
- Models use basic type hints but lack constraints

---

## Implementation Strategy

### Phase 1: Create `src/validators.py` (90 minutes)

Create a new centralized validation module with these Pydantic models:

#### 1.1 Message Input Validators
```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional

class MessageInput(BaseModel):
    """Validate message/text input"""
    text: str = Field(..., min_length=1, max_length=4000)

    @field_validator('text')
    @classmethod
    def validate_encoding(cls, v: str) -> str:
        """Ensure valid UTF-8 encoding"""
        try:
            v.encode('utf-8')
        except UnicodeEncodeError:
            raise ValueError("Invalid UTF-8 encoding")
        return v.strip()
```

#### 1.2 Nutrition Value Validators
```python
class NutritionValues(BaseModel):
    """Validate nutrition values"""
    calories: int = Field(ge=0, le=5000)
    protein: float = Field(ge=0, le=300)
    carbs: float = Field(ge=0, le=500)
    fat: float = Field(ge=0, le=200)

    @field_validator('calories', 'protein', 'carbs', 'fat')
    @classmethod
    def no_negatives(cls, v):
        """Ensure no negative values"""
        if v < 0:
            raise ValueError("Nutrition values cannot be negative")
        return v

    @field_validator('calories')
    @classmethod
    def macro_consistency_check(cls, v, info):
        """Check if macros roughly match calories (within 20%)"""
        if info.data:
            protein = info.data.get('protein', 0)
            carbs = info.data.get('carbs', 0)
            fat = info.data.get('fat', 0)

            macro_cal = (protein * 4) + (carbs * 4) + (fat * 9)

            if v > 0 and abs(macro_cal - v) > v * 0.20:
                raise ValueError(
                    f"Macros ({macro_cal:.0f} cal) don't match total calories ({v})"
                )
        return v
```

#### 1.3 Date/Time Validators
```python
from datetime import date, datetime, time as dt_time, timedelta
import pytz

class DateInput(BaseModel):
    """Validate date inputs"""
    date_value: date

    @field_validator('date_value')
    @classmethod
    def no_future_dates(cls, v: date) -> date:
        """Prevent future dates for logging"""
        if v > date.today():
            raise ValueError("Date cannot be in the future")
        return v

    @field_validator('date_value')
    @classmethod
    def reasonable_range(cls, v: date) -> date:
        """Ensure date is in reasonable range"""
        min_date = date(2020, 1, 1)
        if v < min_date:
            raise ValueError(f"Date must be after {min_date}")
        return v


class TimeInput(BaseModel):
    """Validate time inputs for reminders"""
    time_value: dt_time
    timezone: str = "UTC"

    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Ensure valid IANA timezone"""
        try:
            pytz.timezone(v)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"Invalid timezone: {v}")
        return v
```

#### 1.4 Reminder Frequency Validators
```python
class ReminderFrequency(BaseModel):
    """Validate reminder frequency settings"""
    interval_minutes: int = Field(ge=15, le=1440)  # 15min to 24hr
    time_of_day: dt_time
    days_of_week: list[int] = Field(default_factory=list)
    user_timezone: str = "UTC"

    @field_validator('time_of_day')
    @classmethod
    def validate_operating_hours(cls, v: dt_time) -> dt_time:
        """Ensure reminder is within 6AM-10PM"""
        if v.hour < 6 or v.hour >= 22:
            raise ValueError("Reminders must be between 6AM and 10PM")
        return v

    @field_validator('days_of_week')
    @classmethod
    def validate_days(cls, v: list[int]) -> list[int]:
        """Ensure days are 0-6 (Mon-Sun)"""
        if any(day < 0 or day > 6 for day in v):
            raise ValueError("Days must be 0-6 (Monday=0, Sunday=6)")
        return v


class ReminderLimit(BaseModel):
    """Validate reminder count limits"""
    user_id: str

    @classmethod
    async def check_daily_limit(cls, user_id: str) -> None:
        """Ensure user hasn't exceeded 10 reminders/day"""
        from src.db.queries import count_active_reminders

        count = await count_active_reminders(user_id)
        if count >= 10:
            raise ValueError(
                "Maximum 10 active reminders allowed. "
                "Please delete some before adding more."
            )
```

---

### Phase 2: Integration with Input Handlers (60 minutes)

#### 2.1 Food Photo Handler Integration
**File:** `src/handlers/food_photo.py` (currently empty, needs implementation)

```python
from src.validators import NutritionValues, MessageInput, DateInput

async def handle_food_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle food photo with validated caption"""
    # Validate caption if provided
    if update.message.caption:
        try:
            caption_validated = MessageInput(text=update.message.caption)
        except ValidationError as e:
            await update.message.reply_text(
                f"❌ Invalid caption: {e.errors()[0]['msg']}"
            )
            return

    # ... existing food photo processing ...

    # Validate nutrition values from AI
    try:
        nutrition = NutritionValues(
            calories=ai_result.total_calories,
            protein=ai_result.total_macros.protein,
            carbs=ai_result.total_macros.carbs,
            fat=ai_result.total_macros.fat
        )
    except ValidationError as e:
        logger.warning(f"AI returned invalid nutrition: {e}")
        # Fall back to reasonable defaults or ask user to clarify
```

#### 2.2 Reminder Handler Integration
**File:** `src/handlers/reminders.py`

Currently has 622 lines. Need to add validation before creating reminders:

```python
from src.validators import MessageInput, ReminderFrequency, ReminderLimit

async def create_reminder_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create reminder with validation"""
    user_id = str(update.effective_user.id)

    # Check reminder limit
    try:
        await ReminderLimit.check_daily_limit(user_id)
    except ValidationError as e:
        await update.message.reply_text(str(e))
        return

    # Validate message
    try:
        message_validated = MessageInput(text=reminder_message)
    except ValidationError as e:
        await update.message.reply_text(
            f"❌ Invalid reminder message: {e.errors()[0]['msg']}"
        )
        return

    # Validate frequency
    try:
        frequency = ReminderFrequency(
            interval_minutes=interval,
            time_of_day=scheduled_time,
            days_of_week=days,
            user_timezone=user_tz
        )
    except ValidationError as e:
        await update.message.reply_text(
            f"❌ Invalid reminder schedule: {e.errors()[0]['msg']}"
        )
        return
```

#### 2.3 Onboarding Handler Integration
**File:** `src/handlers/onboarding.py` (848 lines)

Validate user input during onboarding flow:

```python
from src.validators import MessageInput, TimeInput

async def handle_timezone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Validate timezone during onboarding"""
    user_input = update.message.text.strip()

    try:
        time_validated = TimeInput(
            time_value=datetime.now().time(),
            timezone=user_input
        )
    except ValidationError:
        await update.message.reply_text(
            "❌ Invalid timezone. Please provide a valid IANA timezone "
            "(e.g., 'Europe/Stockholm', 'America/New_York')"
        )
        return

    # Store validated timezone
    await save_user_timezone(user_id, user_input)
```

#### 2.4 Message Handler Integration
**File:** `src/handlers/message_handler.py` (currently empty)

Validate general message input:

```python
from src.validators import MessageInput

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Validate and process text messages"""
    try:
        message = MessageInput(text=update.message.text)
    except ValidationError as e:
        await update.message.reply_text(
            f"❌ Message error: {e.errors()[0]['msg']}"
        )
        return

    # Process validated message
    await process_message(message.text)
```

---

### Phase 3: Update Existing Models (30 minutes)

#### 3.1 Enhance `src/models/food.py`
Add validators to existing `FoodMacros` and `FoodItem` models:

```python
from pydantic import field_validator

class FoodMacros(BaseModel):
    """Macronutrient breakdown with validation"""
    protein: float = Field(ge=0, le=300)
    carbs: float = Field(ge=0, le=500)
    fat: float = Field(ge=0, le=200)

    @field_validator('protein', 'carbs', 'fat')
    @classmethod
    def no_negatives(cls, v):
        if v < 0:
            raise ValueError("Macros cannot be negative")
        return v


class FoodItem(BaseModel):
    """Individual food item with validation"""
    name: str = Field(min_length=1, max_length=200)
    quantity: str = Field(min_length=1, max_length=100)
    calories: int = Field(ge=0, le=5000)
    macros: FoodMacros

    @field_validator('calories')
    @classmethod
    def reasonable_calories(cls, v, info):
        """Warn if calories seem unreasonable"""
        if v > 3000:
            logger.warning(f"Very high calories detected: {v}")
        return v
```

#### 3.2 Enhance `src/models/reminder.py`
Add validators to `ReminderSchedule`:

```python
from pydantic import field_validator

class ReminderSchedule(BaseModel):
    """Reminder schedule with validation"""
    type: str
    time: str
    timezone: str = "UTC"
    days: list[int] = Field(default_factory=lambda: list(range(7)))
    date: Optional[str] = None

    @field_validator('time')
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Ensure HH:MM format"""
        try:
            dt_time.fromisoformat(v)
        except ValueError:
            raise ValueError("Time must be in HH:MM format")
        return v

    @field_validator('days')
    @classmethod
    def validate_days(cls, v: list[int]) -> list[int]:
        """Ensure days are 0-6"""
        if any(day < 0 or day > 6 for day in v):
            raise ValueError("Days must be 0-6 (Monday=0, Sunday=6)")
        return v

    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Ensure valid IANA timezone"""
        try:
            pytz.timezone(v)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"Invalid timezone: {v}")
        return v
```

---

### Phase 4: Testing (40 minutes)

#### 4.1 Create `tests/test_validators.py`

```python
import pytest
from datetime import date, time as dt_time
from pydantic import ValidationError
from src.validators import (
    MessageInput,
    NutritionValues,
    DateInput,
    TimeInput,
    ReminderFrequency
)


class TestMessageInput:
    """Test message validation"""

    def test_valid_message(self):
        msg = MessageInput(text="Hello world")
        assert msg.text == "Hello world"

    def test_empty_message_fails(self):
        with pytest.raises(ValidationError):
            MessageInput(text="")

    def test_too_long_message_fails(self):
        long_text = "x" * 4001
        with pytest.raises(ValidationError):
            MessageInput(text=long_text)

    def test_max_length_message_succeeds(self):
        max_text = "x" * 4000
        msg = MessageInput(text=max_text)
        assert len(msg.text) == 4000

    def test_whitespace_stripped(self):
        msg = MessageInput(text="  hello  ")
        assert msg.text == "hello"


class TestNutritionValues:
    """Test nutrition validation"""

    def test_valid_nutrition(self):
        nutrition = NutritionValues(
            calories=500,
            protein=30,
            carbs=50,
            fat=20
        )
        assert nutrition.calories == 500

    def test_negative_calories_fails(self):
        with pytest.raises(ValidationError):
            NutritionValues(calories=-100, protein=0, carbs=0, fat=0)

    def test_negative_protein_fails(self):
        with pytest.raises(ValidationError):
            NutritionValues(calories=100, protein=-10, carbs=0, fat=0)

    def test_excessive_calories_fails(self):
        with pytest.raises(ValidationError):
            NutritionValues(calories=6000, protein=0, carbs=0, fat=0)

    def test_excessive_protein_fails(self):
        with pytest.raises(ValidationError):
            NutritionValues(calories=100, protein=400, carbs=0, fat=0)

    def test_macro_consistency_check(self):
        """Test that macros roughly match calories"""
        # Valid: 30*4 + 50*4 + 20*9 = 500 calories
        nutrition = NutritionValues(
            calories=500,
            protein=30,
            carbs=50,
            fat=20
        )
        assert nutrition.calories == 500

        # Invalid: macros don't match calories
        with pytest.raises(ValidationError, match="don't match total calories"):
            NutritionValues(
                calories=100,  # Way too low for these macros
                protein=50,
                carbs=50,
                fat=50
            )


class TestDateInput:
    """Test date validation"""

    def test_valid_date(self):
        today = date.today()
        date_input = DateInput(date_value=today)
        assert date_input.date_value == today

    def test_future_date_fails(self):
        from datetime import timedelta
        future = date.today() + timedelta(days=1)

        with pytest.raises(ValidationError, match="cannot be in the future"):
            DateInput(date_value=future)

    def test_very_old_date_fails(self):
        old_date = date(2019, 1, 1)

        with pytest.raises(ValidationError, match="must be after"):
            DateInput(date_value=old_date)

    def test_minimum_valid_date(self):
        min_date = date(2020, 1, 1)
        date_input = DateInput(date_value=min_date)
        assert date_input.date_value == min_date


class TestTimeInput:
    """Test time validation"""

    def test_valid_timezone(self):
        time_input = TimeInput(
            time_value=dt_time(12, 0),
            timezone="Europe/Stockholm"
        )
        assert time_input.timezone == "Europe/Stockholm"

    def test_invalid_timezone_fails(self):
        with pytest.raises(ValidationError, match="Invalid timezone"):
            TimeInput(
                time_value=dt_time(12, 0),
                timezone="Invalid/Zone"
            )


class TestReminderFrequency:
    """Test reminder frequency validation"""

    def test_valid_frequency(self):
        freq = ReminderFrequency(
            interval_minutes=30,
            time_of_day=dt_time(10, 0),
            days_of_week=[0, 1, 2, 3, 4],  # Mon-Fri
            user_timezone="UTC"
        )
        assert freq.interval_minutes == 30

    def test_interval_too_short_fails(self):
        with pytest.raises(ValidationError):
            ReminderFrequency(
                interval_minutes=10,  # Too short (min is 15)
                time_of_day=dt_time(10, 0),
                days_of_week=[0]
            )

    def test_interval_too_long_fails(self):
        with pytest.raises(ValidationError):
            ReminderFrequency(
                interval_minutes=1500,  # Too long (max is 1440 = 24hr)
                time_of_day=dt_time(10, 0),
                days_of_week=[0]
            )

    def test_time_before_6am_fails(self):
        with pytest.raises(ValidationError, match="6AM and 10PM"):
            ReminderFrequency(
                interval_minutes=60,
                time_of_day=dt_time(5, 0),  # Too early
                days_of_week=[0]
            )

    def test_time_after_10pm_fails(self):
        with pytest.raises(ValidationError, match="6AM and 10PM"):
            ReminderFrequency(
                interval_minutes=60,
                time_of_day=dt_time(22, 0),  # Too late
                days_of_week=[0]
            )

    def test_invalid_day_fails(self):
        with pytest.raises(ValidationError, match="Days must be 0-6"):
            ReminderFrequency(
                interval_minutes=60,
                time_of_day=dt_time(10, 0),
                days_of_week=[0, 7]  # 7 is invalid
            )
```

#### 4.2 Integration Tests
**File:** `tests/integration/test_validation_integration.py`

```python
import pytest
from telegram import Update
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_food_photo_with_invalid_caption():
    """Test that invalid captions are rejected"""
    # Mock update with excessively long caption
    update = MagicMock(spec=Update)
    update.message.caption = "x" * 4001  # Too long

    # Should reject and send error message
    # ... test implementation


@pytest.mark.asyncio
async def test_reminder_with_invalid_time():
    """Test that invalid reminder times are rejected"""
    # Try to create reminder at 3AM (before 6AM limit)
    # Should reject with appropriate error
    # ... test implementation
```

---

## Implementation Checklist

### Core Validators (`src/validators.py`)
- [ ] Create file structure with imports
- [ ] `MessageInput` validator (max 4000 chars, encoding check)
- [ ] `NutritionValues` validator (ranges, no negatives, macro consistency)
- [ ] `DateInput` validator (no future, reasonable range)
- [ ] `TimeInput` validator (timezone validation)
- [ ] `ReminderFrequency` validator (intervals, operating hours, days)
- [ ] `ReminderLimit` async validator (max 10/day)
- [ ] Documentation and type hints

### Model Enhancements
- [ ] Update `src/models/food.py` - add validators to `FoodMacros`, `FoodItem`
- [ ] Update `src/models/reminder.py` - add validators to `ReminderSchedule`
- [ ] Ensure backward compatibility with existing data

### Handler Integration
- [ ] `src/handlers/food_photo.py` - validate captions and nutrition
- [ ] `src/handlers/reminders.py` - validate messages, frequency, limits
- [ ] `src/handlers/onboarding.py` - validate timezone, user input
- [ ] `src/handlers/message_handler.py` - validate general text input
- [ ] Add user-friendly error messages for all validation failures

### Testing
- [ ] `tests/test_validators.py` - Unit tests for all validators
- [ ] `tests/integration/test_validation_integration.py` - Handler integration tests
- [ ] Test edge cases (boundary values, encoding issues, etc.)
- [ ] Test error message clarity

### Validation & Deployment
- [ ] Run full test suite: `pytest`
- [ ] Run type checking: `mypy src/validators.py`
- [ ] Run linter: `ruff check src/validators.py`
- [ ] Manual testing with Telegram bot
- [ ] Update documentation

---

## Error Handling Strategy

All validation errors should provide **user-friendly messages**:

❌ Bad: `ValidationError: 1 validation error for NutritionValues`
✅ Good: `❌ Invalid calories: Value must be between 0 and 5000`

Implement helper function:
```python
def format_validation_error(e: ValidationError) -> str:
    """Format Pydantic validation error for user display"""
    errors = e.errors()
    if errors:
        first_error = errors[0]
        field = first_error['loc'][0]
        msg = first_error['msg']
        return f"❌ Invalid {field}: {msg}"
    return "❌ Invalid input"
```

---

## Backward Compatibility

**Important:** Existing data in the database may not meet new validation rules.

Strategy:
1. **New data:** Validate strictly
2. **Existing data:** Validate on read with warnings, not errors
3. **Migration:** Optional background task to flag invalid existing data

```python
class FoodItemWithLegacy(FoodItem):
    """Extended model that handles legacy data"""

    @classmethod
    def from_db(cls, data: dict):
        """Load from DB with lenient validation for legacy data"""
        try:
            return cls(**data)
        except ValidationError as e:
            logger.warning(f"Legacy data validation failed: {e}")
            # Return with defaults or sanitized values
            return cls(**sanitize_legacy_data(data))
```

---

## Integration Points

### 1. Database Layer
- No changes required - validation happens before DB insertion
- Existing queries remain unchanged

### 2. API Layer (`src/api/routes.py`)
- Add validation to API request bodies
- Return 422 Unprocessable Entity for validation errors

```python
@app.post("/api/v1/food")
async def create_food_entry(nutrition: NutritionValues):
    """API endpoint with automatic Pydantic validation"""
    # FastAPI automatically validates request body
    # Returns 422 if validation fails
    pass
```

### 3. Telegram Handlers
- Catch `ValidationError` exceptions
- Send user-friendly error messages
- Provide correction hints

---

## Performance Considerations

- **Validation overhead:** Minimal (<1ms per validation)
- **Database impact:** None (validation before DB)
- **User experience:** Immediate feedback on invalid input

---

## Success Criteria

✅ All user inputs validated before processing
✅ Clear, actionable error messages
✅ No invalid data reaches database
✅ Existing functionality preserved
✅ Test coverage >90% for validators
✅ Documentation complete

---

## Files to Create/Modify

### New Files
1. `src/validators.py` (~300 lines)
2. `tests/test_validators.py` (~400 lines)
3. `tests/integration/test_validation_integration.py` (~200 lines)

### Modified Files
1. `src/models/food.py` (+30 lines)
2. `src/models/reminder.py` (+40 lines)
3. `src/handlers/food_photo.py` (+50 lines, currently empty)
4. `src/handlers/reminders.py` (+60 lines)
5. `src/handlers/onboarding.py` (+40 lines)
6. `src/handlers/message_handler.py` (+30 lines, currently empty)

**Total:** ~1,150 lines of new/modified code

---

## Timeline

1. **Hour 1:** Create `src/validators.py` with all validators
2. **Hour 2:** Integrate with handlers and update models
3. **Hour 3:** Write tests, run validation, fix issues

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing functionality | High | Comprehensive testing, backward compatibility layer |
| User confusion from error messages | Medium | User-friendly messages, provide examples |
| Performance degradation | Low | Validation is fast, add benchmarks if needed |
| Incomplete handler coverage | Medium | Audit all input points, add TODO comments |

---

## Dependencies

- ✅ `pydantic>=2.0.0` - Already installed
- ✅ `pytz>=2024.1` - Already installed (for timezone validation)
- ✅ `pytest>=8.0.0` - Already installed

**No new dependencies required.**

---

## Post-Implementation

### Monitoring
- Log validation failures for analysis
- Track most common validation errors
- Adjust ranges if needed based on real usage

### Future Enhancements
- Add custom validators for specific food types
- Implement smart suggestions when validation fails
- Add validation for file uploads (image size, format)

---

## Summary

This implementation creates a robust, centralized validation layer using Pydantic that:

1. **Prevents invalid data** from entering the system
2. **Provides clear feedback** to users
3. **Maintains consistency** across all input points
4. **Enables future enhancements** through a solid foundation

The validation layer integrates seamlessly with existing code while adding a critical safety net for data integrity.

**Estimated LOC:** ~1,150 lines
**Estimated Time:** 3 hours
**Priority:** HIGH (Phase 2.4 Epic 007)

---

**Plan Status:** ✅ Complete - Ready for Implementation
