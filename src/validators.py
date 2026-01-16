"""
Centralized Pydantic Input Validation Layer

Provides validation for all user inputs across the health agent to ensure
data integrity and prevent invalid data from reaching the database.

Validation Categories:
1. Message Input - Max 4000 chars, encoding validation
2. Nutrition Values - Range checks, no negatives, macro consistency
3. Date/Time Validation - No future dates, reasonable ranges
4. Reminder Frequency - Interval limits, operating hours, daily limits
"""

import logging
from datetime import date, datetime, time as dt_time, timedelta
from typing import Optional, ClassVar
from pydantic import BaseModel, Field, field_validator, model_validator
import pytz

logger = logging.getLogger(__name__)


# ============================================================================
# MESSAGE INPUT VALIDATION
# ============================================================================

class MessageInput(BaseModel):
    """
    Validate text message input (reminders, notes, captions, etc.)

    Constraints:
    - Min length: 1 character
    - Max length: 4000 characters (Telegram limit)
    - Valid UTF-8 encoding
    - Whitespace is trimmed
    """
    text: str = Field(..., min_length=1, max_length=4000, description="Message text")

    @field_validator('text')
    @classmethod
    def validate_encoding(cls, v: str) -> str:
        """Ensure valid UTF-8 encoding and trim whitespace"""
        if not v:
            raise ValueError("Message cannot be empty")

        try:
            # Verify UTF-8 encoding
            v.encode('utf-8')
        except UnicodeEncodeError as e:
            raise ValueError(f"Invalid UTF-8 encoding: {e}")

        # Trim whitespace
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Message cannot be only whitespace")

        return trimmed

    @field_validator('text')
    @classmethod
    def check_length(cls, v: str) -> str:
        """Additional length validation with helpful messages"""
        if len(v) > 4000:
            raise ValueError(
                f"Message too long ({len(v)} characters). "
                f"Maximum is 4000 characters (Telegram limit)."
            )
        return v


# ============================================================================
# NUTRITION VALUE VALIDATION
# ============================================================================

class NutritionValues(BaseModel):
    """
    Validate nutrition values for food entries

    Constraints:
    - Calories: 0-5000 kcal (realistic single meal/day limit)
    - Protein: 0-300g (realistic daily limit)
    - Carbs: 0-500g (realistic daily limit)
    - Fat: 0-200g (realistic daily limit)
    - No negative values allowed
    - Macro consistency check (4-4-9 rule within 20% tolerance)
    """
    calories: int = Field(ge=0, le=5000, description="Calories in kcal")
    protein: float = Field(ge=0, le=300, description="Protein in grams")
    carbs: float = Field(ge=0, le=500, description="Carbohydrates in grams")
    fat: float = Field(ge=0, le=200, description="Fat in grams")

    @field_validator('calories', 'protein', 'carbs', 'fat')
    @classmethod
    def no_negatives(cls, v: float, info) -> float:
        """Ensure no negative nutrition values"""
        if v < 0:
            field_name = info.field_name
            raise ValueError(f"{field_name.capitalize()} cannot be negative")
        return v

    @model_validator(mode='after')
    def macro_consistency_check(self) -> 'NutritionValues':
        """
        Validate that macros roughly match calories using 4-4-9 rule
        (Protein: 4 cal/g, Carbs: 4 cal/g, Fat: 9 cal/g)

        Allows 20% tolerance for rounding, fiber, alcohol, etc.
        """
        if self.calories == 0:
            return self  # Skip check for zero calories

        # Calculate calories from macros
        macro_calories = (
            (self.protein * 4) +
            (self.carbs * 4) +
            (self.fat * 9)
        )

        # Check if within 20% tolerance
        difference = abs(macro_calories - self.calories)
        tolerance = self.calories * 0.20

        if difference > tolerance:
            raise ValueError(
                f"Macros ({macro_calories:.0f} cal from P:{self.protein}g "
                f"C:{self.carbs}g F:{self.fat}g) don't match total calories "
                f"({self.calories} cal). Difference: {difference:.0f} cal "
                f"(>{tolerance:.0f} cal tolerance)."
            )

        return self

    @field_validator('calories')
    @classmethod
    def reasonable_calories(cls, v: int) -> int:
        """Log warning for unusually high calories"""
        if v > 3000:
            logger.warning(
                f"Very high calorie value detected: {v} kcal. "
                f"Please verify this is correct."
            )
        return v


# ============================================================================
# DATE/TIME VALIDATION
# ============================================================================

class DateInput(BaseModel):
    """
    Validate date inputs for logging (food, sleep, etc.)

    Constraints:
    - No future dates (can't log something that hasn't happened)
    - Must be after 2020-01-01 (reasonable minimum)
    - Must be on or before today
    """
    date_value: date = Field(..., description="Date for logging")

    # Class variable for minimum date
    MIN_DATE: ClassVar[date] = date(2020, 1, 1)

    @field_validator('date_value')
    @classmethod
    def no_future_dates(cls, v: date) -> date:
        """Prevent future dates for historical logging"""
        today = date.today()
        if v > today:
            raise ValueError(
                f"Date cannot be in the future. "
                f"Provided: {v}, Today: {today}"
            )
        return v

    @field_validator('date_value')
    @classmethod
    def reasonable_range(cls, v: date) -> date:
        """Ensure date is in reasonable range"""
        if v < cls.MIN_DATE:
            raise ValueError(
                f"Date must be after {cls.MIN_DATE}. "
                f"Provided: {v}"
            )
        return v


class TimeInput(BaseModel):
    """
    Validate time inputs with timezone awareness

    Constraints:
    - Valid IANA timezone string
    - Time must be valid (HH:MM format)
    """
    time_value: dt_time = Field(..., description="Time of day")
    timezone: str = Field(default="UTC", description="IANA timezone")

    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Ensure valid IANA timezone"""
        try:
            pytz.timezone(v)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(
                f"Invalid timezone: '{v}'. "
                f"Please use IANA timezone (e.g., 'Europe/Stockholm', 'America/New_York')"
            )
        return v


# ============================================================================
# REMINDER FREQUENCY VALIDATION
# ============================================================================

class ReminderFrequency(BaseModel):
    """
    Validate reminder frequency and scheduling

    Constraints:
    - Interval: 15 minutes to 24 hours (1440 minutes)
    - Operating hours: 6AM to 10PM (configurable per user)
    - Days of week: 0-6 (Monday=0, Sunday=6)
    - Timezone aware
    """
    interval_minutes: int = Field(
        ge=15,
        le=1440,
        description="Interval between reminders in minutes"
    )
    time_of_day: dt_time = Field(..., description="Time to send reminder")
    days_of_week: list[int] = Field(
        default_factory=list,
        description="Days of week (0=Mon, 6=Sun)"
    )
    user_timezone: str = Field(default="UTC", description="User's timezone")

    # Class variables for operating hours
    MIN_HOUR: ClassVar[int] = 6  # 6 AM
    MAX_HOUR: ClassVar[int] = 22  # 10 PM

    @field_validator('time_of_day')
    @classmethod
    def validate_operating_hours(cls, v: dt_time) -> dt_time:
        """Ensure reminder is within 6AM-10PM operating hours"""
        if v.hour < cls.MIN_HOUR or v.hour >= cls.MAX_HOUR:
            raise ValueError(
                f"Reminders must be scheduled between "
                f"{cls.MIN_HOUR}:00 AM and {cls.MAX_HOUR}:00 PM. "
                f"Provided: {v.strftime('%H:%M')}"
            )
        return v

    @field_validator('days_of_week')
    @classmethod
    def validate_days(cls, v: list[int]) -> list[int]:
        """Ensure days are 0-6 (Monday-Sunday)"""
        if not v:
            return v  # Empty list is valid (one-time reminder)

        for day in v:
            if day < 0 or day > 6:
                raise ValueError(
                    f"Invalid day: {day}. Days must be 0-6 "
                    f"(Monday=0, Sunday=6)"
                )
        return v

    @field_validator('user_timezone')
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Ensure valid IANA timezone"""
        try:
            pytz.timezone(v)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(
                f"Invalid timezone: '{v}'. "
                f"Please use IANA timezone (e.g., 'Europe/Stockholm')"
            )
        return v


class ReminderLimit:
    """
    Async validator for reminder count limits

    Constraint:
    - Maximum 10 active reminders per user per day
    """

    MAX_REMINDERS: ClassVar[int] = 10

    @classmethod
    async def check_daily_limit(cls, user_id: str) -> None:
        """
        Ensure user hasn't exceeded maximum active reminders

        Args:
            user_id: User's Telegram ID

        Raises:
            ValueError: If user has reached the limit
        """
        from src.db.queries import count_active_reminders

        try:
            count = await count_active_reminders(user_id)
        except Exception as e:
            logger.error(f"Failed to check reminder limit: {e}")
            # Don't block on DB errors
            return

        if count >= cls.MAX_REMINDERS:
            raise ValueError(
                f"Maximum {cls.MAX_REMINDERS} active reminders allowed. "
                f"You currently have {count} active reminders. "
                f"Please delete some before adding more."
            )

        logger.debug(f"User {user_id} has {count}/{cls.MAX_REMINDERS} reminders")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def format_validation_error(e: Exception) -> str:
    """
    Format Pydantic validation error for user-friendly display

    Args:
        e: ValidationError from Pydantic

    Returns:
        User-friendly error message with emoji
    """
    from pydantic import ValidationError

    if not isinstance(e, ValidationError):
        return f"❌ Error: {str(e)}"

    errors = e.errors()
    if not errors:
        return "❌ Validation failed"

    # Get first error for simplicity
    first_error = errors[0]
    field = first_error.get('loc', ['input'])[0]
    msg = first_error.get('msg', 'Invalid value')

    # Handle nested field names
    if isinstance(field, str):
        field_name = field.replace('_', ' ').title()
    else:
        field_name = 'Input'

    return f"❌ Invalid {field_name}: {msg}"


def safe_validate(model_class: type[BaseModel], **data) -> tuple[Optional[BaseModel], Optional[str]]:
    """
    Safely validate data and return (validated_model, error_message)

    Args:
        model_class: Pydantic model class
        **data: Data to validate

    Returns:
        Tuple of (validated_instance, error_message)
        - If valid: (instance, None)
        - If invalid: (None, user_friendly_error)
    """
    try:
        instance = model_class(**data)
        return instance, None
    except Exception as e:
        error_msg = format_validation_error(e)
        logger.warning(f"Validation failed for {model_class.__name__}: {error_msg}")
        return None, error_msg


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    """Example usage and validation tests"""

    print("=" * 60)
    print("PYDANTIC VALIDATION LAYER - EXAMPLES")
    print("=" * 60)

    # Test 1: Valid message
    print("\n1. Valid Message:")
    msg, err = safe_validate(MessageInput, text="Hello, this is a valid message!")
    print(f"   Result: {msg.text if msg else err}")

    # Test 2: Invalid message (too long)
    print("\n2. Too Long Message:")
    long_text = "x" * 4001
    msg, err = safe_validate(MessageInput, text=long_text)
    print(f"   Result: {err}")

    # Test 3: Valid nutrition
    print("\n3. Valid Nutrition:")
    nutrition, err = safe_validate(
        NutritionValues,
        calories=500,
        protein=30,
        carbs=50,
        fat=20
    )
    print(f"   Result: {nutrition.calories if nutrition else err} kcal")

    # Test 4: Invalid nutrition (macros don't match)
    print("\n4. Invalid Nutrition (macro mismatch):")
    nutrition, err = safe_validate(
        NutritionValues,
        calories=100,  # Too low for macros
        protein=50,
        carbs=50,
        fat=50
    )
    print(f"   Result: {err}")

    # Test 5: Valid date
    print("\n5. Valid Date:")
    date_input, err = safe_validate(DateInput, date_value=date.today())
    print(f"   Result: {date_input.date_value if date_input else err}")

    # Test 6: Invalid date (future)
    print("\n6. Future Date:")
    future = date.today() + timedelta(days=1)
    date_input, err = safe_validate(DateInput, date_value=future)
    print(f"   Result: {err}")

    # Test 7: Valid reminder frequency
    print("\n7. Valid Reminder Frequency:")
    freq, err = safe_validate(
        ReminderFrequency,
        interval_minutes=30,
        time_of_day=dt_time(10, 0),
        days_of_week=[0, 1, 2, 3, 4],  # Mon-Fri
        user_timezone="Europe/Stockholm"
    )
    print(f"   Result: {freq.time_of_day if freq else err}")

    # Test 8: Invalid reminder (outside operating hours)
    print("\n8. Invalid Reminder Time (too early):")
    freq, err = safe_validate(
        ReminderFrequency,
        interval_minutes=60,
        time_of_day=dt_time(5, 0),  # 5 AM (before 6 AM limit)
        days_of_week=[0]
    )
    print(f"   Result: {err}")

    print("\n" + "=" * 60)
    print("VALIDATION EXAMPLES COMPLETE")
    print("=" * 60)
