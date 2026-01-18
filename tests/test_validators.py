"""
Comprehensive tests for Pydantic validation layer

Tests all validators in src/validators.py to ensure proper input validation
across the health agent system.
"""

import pytest
from datetime import date, time as dt_time, timedelta
from pydantic import ValidationError

from src.validators import (
    MessageInput,
    NutritionValues,
    DateInput,
    TimeInput,
    ReminderFrequency,
    ReminderLimit,
    format_validation_error,
    safe_validate,
)


# ============================================================================
# MESSAGE INPUT TESTS
# ============================================================================

class TestMessageInput:
    """Test message validation"""

    def test_valid_message(self):
        """Test valid message passes validation"""
        msg = MessageInput(text="Hello world")
        assert msg.text == "Hello world"

    def test_valid_message_with_emojis(self):
        """Test message with emojis (UTF-8)"""
        msg = MessageInput(text="Hello 👋 world 🌍")
        assert "👋" in msg.text
        assert "🌍" in msg.text

    def test_empty_message_fails(self):
        """Test empty message is rejected"""
        with pytest.raises(ValidationError, match="at least 1 character"):
            MessageInput(text="")

    def test_whitespace_only_fails(self):
        """Test whitespace-only message is rejected"""
        with pytest.raises(ValidationError, match="cannot be only whitespace"):
            MessageInput(text="   ")

    def test_too_long_message_fails(self):
        """Test message exceeding 4000 chars is rejected"""
        long_text = "x" * 4001
        with pytest.raises(ValidationError, match="at most 4000 characters"):
            MessageInput(text=long_text)

    def test_max_length_message_succeeds(self):
        """Test message at exactly 4000 chars passes"""
        max_text = "x" * 4000
        msg = MessageInput(text=max_text)
        assert len(msg.text) == 4000

    def test_whitespace_stripped(self):
        """Test leading/trailing whitespace is trimmed"""
        msg = MessageInput(text="  hello world  ")
        assert msg.text == "hello world"

    def test_newlines_preserved(self):
        """Test newlines are preserved in message"""
        msg = MessageInput(text="Line 1\nLine 2\nLine 3")
        assert "\n" in msg.text
        assert "Line 1" in msg.text

    def test_special_characters(self):
        """Test special characters are allowed"""
        msg = MessageInput(text="Test @#$%^&*() symbols")
        assert "@#$%^&*()" in msg.text


# ============================================================================
# NUTRITION VALUES TESTS
# ============================================================================

class TestNutritionValues:
    """Test nutrition validation"""

    def test_valid_nutrition(self):
        """Test valid nutrition values pass"""
        nutrition = NutritionValues(
            calories=500,
            protein=30,
            carbs=50,
            fat=20
        )
        assert nutrition.calories == 500
        assert nutrition.protein == 30.0
        assert nutrition.carbs == 50.0
        assert nutrition.fat == 20.0

    def test_zero_values_valid(self):
        """Test zero values are valid"""
        nutrition = NutritionValues(
            calories=0,
            protein=0,
            carbs=0,
            fat=0
        )
        assert nutrition.calories == 0

    def test_negative_calories_fails(self):
        """Test negative calories are rejected"""
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            NutritionValues(calories=-100, protein=0, carbs=0, fat=0)

    def test_negative_protein_fails(self):
        """Test negative protein is rejected"""
        with pytest.raises(ValidationError, match="Protein cannot be negative"):
            NutritionValues(calories=100, protein=-10, carbs=0, fat=0)

    def test_negative_carbs_fails(self):
        """Test negative carbs are rejected"""
        with pytest.raises(ValidationError, match="Carbs cannot be negative"):
            NutritionValues(calories=100, protein=0, carbs=-10, fat=0)

    def test_negative_fat_fails(self):
        """Test negative fat is rejected"""
        with pytest.raises(ValidationError, match="Fat cannot be negative"):
            NutritionValues(calories=100, protein=0, carbs=0, fat=-10)

    def test_excessive_calories_fails(self):
        """Test calories above 5000 are rejected"""
        with pytest.raises(ValidationError, match="less than or equal to 5000"):
            NutritionValues(calories=6000, protein=0, carbs=0, fat=0)

    def test_excessive_protein_fails(self):
        """Test protein above 300g is rejected"""
        with pytest.raises(ValidationError, match="less than or equal to 300"):
            NutritionValues(calories=1000, protein=400, carbs=0, fat=0)

    def test_excessive_carbs_fails(self):
        """Test carbs above 500g are rejected"""
        with pytest.raises(ValidationError, match="less than or equal to 500"):
            NutritionValues(calories=2000, protein=0, carbs=600, fat=0)

    def test_excessive_fat_fails(self):
        """Test fat above 200g is rejected"""
        with pytest.raises(ValidationError, match="less than or equal to 200"):
            NutritionValues(calories=2000, protein=0, carbs=0, fat=250)

    def test_macro_consistency_valid(self):
        """Test macros matching calories (within tolerance)"""
        # 30*4 + 50*4 + 20*9 = 500 calories (exact match)
        nutrition = NutritionValues(
            calories=500,
            protein=30,
            carbs=50,
            fat=20
        )
        assert nutrition.calories == 500

    def test_macro_consistency_within_tolerance(self):
        """Test macros slightly off but within 20% tolerance"""
        # 30*4 + 50*4 + 20*9 = 500, but calories=520 (4% off)
        nutrition = NutritionValues(
            calories=520,
            protein=30,
            carbs=50,
            fat=20
        )
        assert nutrition.calories == 520

    def test_macro_consistency_fails_large_mismatch(self):
        """Test macros way off total calories fails"""
        # 50*4 + 50*4 + 50*9 = 850 cal, but calories=100 (way too low)
        with pytest.raises(ValidationError, match="don't match total calories"):
            NutritionValues(
                calories=100,
                protein=50,
                carbs=50,
                fat=50
            )

    def test_macro_consistency_skip_zero_calories(self):
        """Test macro consistency check skipped for zero calories"""
        nutrition = NutritionValues(
            calories=0,
            protein=0,
            carbs=0,
            fat=0
        )
        assert nutrition.calories == 0

    def test_boundary_values(self):
        """Test boundary values are accepted"""
        nutrition = NutritionValues(
            calories=5000,  # Max
            protein=300,    # Max
            carbs=500,      # Max
            fat=200         # Max
        )
        assert nutrition.calories == 5000


# ============================================================================
# DATE INPUT TESTS
# ============================================================================

class TestDateInput:
    """Test date validation"""

    def test_valid_date_today(self):
        """Test today's date is valid"""
        today = date.today()
        date_input = DateInput(date_value=today)
        assert date_input.date_value == today

    def test_valid_date_yesterday(self):
        """Test yesterday's date is valid"""
        yesterday = date.today() - timedelta(days=1)
        date_input = DateInput(date_value=yesterday)
        assert date_input.date_value == yesterday

    def test_future_date_fails(self):
        """Test future date is rejected"""
        future = date.today() + timedelta(days=1)
        with pytest.raises(ValidationError, match="cannot be in the future"):
            DateInput(date_value=future)

    def test_far_future_fails(self):
        """Test far future date is rejected"""
        far_future = date.today() + timedelta(days=365)
        with pytest.raises(ValidationError, match="cannot be in the future"):
            DateInput(date_value=far_future)

    def test_very_old_date_fails(self):
        """Test date before 2020 is rejected"""
        old_date = date(2019, 12, 31)
        with pytest.raises(ValidationError, match="must be after"):
            DateInput(date_value=old_date)

    def test_minimum_valid_date(self):
        """Test minimum date (2020-01-01) is valid"""
        min_date = date(2020, 1, 1)
        date_input = DateInput(date_value=min_date)
        assert date_input.date_value == min_date

    def test_date_one_year_ago(self):
        """Test date one year ago is valid"""
        one_year_ago = date.today() - timedelta(days=365)
        date_input = DateInput(date_value=one_year_ago)
        assert date_input.date_value == one_year_ago


# ============================================================================
# TIME INPUT TESTS
# ============================================================================

class TestTimeInput:
    """Test time validation"""

    def test_valid_time_utc(self):
        """Test valid time with UTC timezone"""
        time_input = TimeInput(
            time_value=dt_time(12, 0),
            timezone="UTC"
        )
        assert time_input.time_value == dt_time(12, 0)
        assert time_input.timezone == "UTC"

    def test_valid_timezone_stockholm(self):
        """Test valid European timezone"""
        time_input = TimeInput(
            time_value=dt_time(10, 30),
            timezone="Europe/Stockholm"
        )
        assert time_input.timezone == "Europe/Stockholm"

    def test_valid_timezone_new_york(self):
        """Test valid American timezone"""
        time_input = TimeInput(
            time_value=dt_time(15, 45),
            timezone="America/New_York"
        )
        assert time_input.timezone == "America/New_York"

    def test_invalid_timezone_fails(self):
        """Test invalid timezone is rejected"""
        with pytest.raises(ValidationError, match="Invalid timezone"):
            TimeInput(
                time_value=dt_time(12, 0),
                timezone="Invalid/Zone"
            )

    def test_invalid_timezone_random_fails(self):
        """Test random string as timezone fails"""
        with pytest.raises(ValidationError, match="Invalid timezone"):
            TimeInput(
                time_value=dt_time(12, 0),
                timezone="RandomString"
            )

    def test_default_timezone_utc(self):
        """Test default timezone is UTC"""
        time_input = TimeInput(time_value=dt_time(12, 0))
        assert time_input.timezone == "UTC"


# ============================================================================
# REMINDER FREQUENCY TESTS
# ============================================================================

class TestReminderFrequency:
    """Test reminder frequency validation"""

    def test_valid_frequency_daily(self):
        """Test valid daily reminder"""
        freq = ReminderFrequency(
            interval_minutes=60,
            time_of_day=dt_time(10, 0),
            days_of_week=[0, 1, 2, 3, 4],  # Mon-Fri
            user_timezone="UTC"
        )
        assert freq.interval_minutes == 60
        assert freq.time_of_day == dt_time(10, 0)

    def test_valid_frequency_minimum_interval(self):
        """Test minimum interval (15 min) is valid"""
        freq = ReminderFrequency(
            interval_minutes=15,
            time_of_day=dt_time(10, 0),
            days_of_week=[0]
        )
        assert freq.interval_minutes == 15

    def test_valid_frequency_maximum_interval(self):
        """Test maximum interval (24hr = 1440 min) is valid"""
        freq = ReminderFrequency(
            interval_minutes=1440,
            time_of_day=dt_time(8, 0),
            days_of_week=[0]
        )
        assert freq.interval_minutes == 1440

    def test_interval_too_short_fails(self):
        """Test interval below 15 min is rejected"""
        with pytest.raises(ValidationError, match="greater than or equal to 15"):
            ReminderFrequency(
                interval_minutes=10,
                time_of_day=dt_time(10, 0),
                days_of_week=[0]
            )

    def test_interval_too_long_fails(self):
        """Test interval above 24hr is rejected"""
        with pytest.raises(ValidationError, match="less than or equal to 1440"):
            ReminderFrequency(
                interval_minutes=1500,
                time_of_day=dt_time(10, 0),
                days_of_week=[0]
            )

    def test_time_at_6am_valid(self):
        """Test time at 6 AM (minimum) is valid"""
        freq = ReminderFrequency(
            interval_minutes=60,
            time_of_day=dt_time(6, 0),
            days_of_week=[0]
        )
        assert freq.time_of_day == dt_time(6, 0)

    def test_time_at_9pm_valid(self):
        """Test time at 9 PM is valid (before 10 PM limit)"""
        freq = ReminderFrequency(
            interval_minutes=60,
            time_of_day=dt_time(21, 0),
            days_of_week=[0]
        )
        assert freq.time_of_day == dt_time(21, 0)

    def test_time_before_6am_fails(self):
        """Test time before 6 AM is rejected"""
        with pytest.raises(ValidationError, match="6AM and 10PM"):
            ReminderFrequency(
                interval_minutes=60,
                time_of_day=dt_time(5, 59),
                days_of_week=[0]
            )

    def test_time_at_10pm_fails(self):
        """Test time at 10 PM (limit) is rejected"""
        with pytest.raises(ValidationError, match="6AM and 10PM"):
            ReminderFrequency(
                interval_minutes=60,
                time_of_day=dt_time(22, 0),
                days_of_week=[0]
            )

    def test_time_after_10pm_fails(self):
        """Test time after 10 PM is rejected"""
        with pytest.raises(ValidationError, match="6AM and 10PM"):
            ReminderFrequency(
                interval_minutes=60,
                time_of_day=dt_time(23, 0),
                days_of_week=[0]
            )

    def test_valid_days_all_week(self):
        """Test all days of week are valid"""
        freq = ReminderFrequency(
            interval_minutes=60,
            time_of_day=dt_time(10, 0),
            days_of_week=[0, 1, 2, 3, 4, 5, 6]  # Mon-Sun
        )
        assert len(freq.days_of_week) == 7

    def test_valid_days_weekdays_only(self):
        """Test weekdays only selection"""
        freq = ReminderFrequency(
            interval_minutes=60,
            time_of_day=dt_time(10, 0),
            days_of_week=[0, 1, 2, 3, 4]  # Mon-Fri
        )
        assert freq.days_of_week == [0, 1, 2, 3, 4]

    def test_empty_days_valid(self):
        """Test empty days list is valid (one-time reminder)"""
        freq = ReminderFrequency(
            interval_minutes=60,
            time_of_day=dt_time(10, 0),
            days_of_week=[]
        )
        assert freq.days_of_week == []

    def test_invalid_day_negative_fails(self):
        """Test negative day number is rejected"""
        with pytest.raises(ValidationError, match="Days must be 0-6"):
            ReminderFrequency(
                interval_minutes=60,
                time_of_day=dt_time(10, 0),
                days_of_week=[-1, 0]
            )

    def test_invalid_day_seven_fails(self):
        """Test day 7 is rejected"""
        with pytest.raises(ValidationError, match="Days must be 0-6"):
            ReminderFrequency(
                interval_minutes=60,
                time_of_day=dt_time(10, 0),
                days_of_week=[0, 7]
            )

    def test_invalid_timezone_fails(self):
        """Test invalid timezone is rejected"""
        with pytest.raises(ValidationError, match="Invalid timezone"):
            ReminderFrequency(
                interval_minutes=60,
                time_of_day=dt_time(10, 0),
                days_of_week=[0],
                user_timezone="BadTimezone"
            )

    def test_valid_timezone_stockholm(self):
        """Test Stockholm timezone is valid"""
        freq = ReminderFrequency(
            interval_minutes=60,
            time_of_day=dt_time(10, 0),
            days_of_week=[0],
            user_timezone="Europe/Stockholm"
        )
        assert freq.user_timezone == "Europe/Stockholm"


# ============================================================================
# REMINDER LIMIT TESTS
# ============================================================================

class TestReminderLimit:
    """Test reminder limit validation"""

    @pytest.mark.asyncio
    async def test_check_limit_constants(self):
        """Test limit constant is set correctly"""
        assert ReminderLimit.MAX_REMINDERS == 10


# ============================================================================
# UTILITY FUNCTION TESTS
# ============================================================================

class TestUtilityFunctions:
    """Test utility helper functions"""

    def test_format_validation_error(self):
        """Test ValidationError formatting"""
        try:
            MessageInput(text="")
        except ValidationError as e:
            msg = format_validation_error(e)
            assert "❌" in msg
            assert "Invalid" in msg

    def test_format_validation_error_non_pydantic(self):
        """Test non-Pydantic error formatting"""
        error = ValueError("Test error")
        msg = format_validation_error(error)
        assert "❌ Error: Test error" == msg

    def test_safe_validate_success(self):
        """Test safe_validate with valid data"""
        instance, error = safe_validate(
            MessageInput,
            text="Valid message"
        )
        assert instance is not None
        assert error is None
        assert instance.text == "Valid message"

    def test_safe_validate_failure(self):
        """Test safe_validate with invalid data"""
        instance, error = safe_validate(
            MessageInput,
            text=""
        )
        assert instance is None
        assert error is not None
        assert "❌" in error

    def test_safe_validate_nutrition_success(self):
        """Test safe_validate with nutrition data"""
        instance, error = safe_validate(
            NutritionValues,
            calories=500,
            protein=30,
            carbs=50,
            fat=20
        )
        assert instance is not None
        assert error is None

    def test_safe_validate_nutrition_failure(self):
        """Test safe_validate with invalid nutrition"""
        instance, error = safe_validate(
            NutritionValues,
            calories=-100,
            protein=0,
            carbs=0,
            fat=0
        )
        assert instance is None
        assert error is not None
        assert "❌" in error


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestValidatorIntegration:
    """Test validators work together"""

    def test_create_complete_reminder(self):
        """Test creating a complete reminder with all validations"""
        message, msg_err = safe_validate(MessageInput, text="Take your medication")
        assert message is not None

        freq, freq_err = safe_validate(
            ReminderFrequency,
            interval_minutes=1440,  # Daily
            time_of_day=dt_time(8, 0),
            days_of_week=[0, 1, 2, 3, 4, 5, 6],
            user_timezone="Europe/Stockholm"
        )
        assert freq is not None

    def test_create_complete_nutrition_entry(self):
        """Test creating a complete nutrition entry"""
        nutrition, err = safe_validate(
            NutritionValues,
            calories=650,
            protein=45,
            carbs=60,
            fat=25
        )
        assert nutrition is not None

        date_val, date_err = safe_validate(
            DateInput,
            date_value=date.today()
        )
        assert date_val is not None

        notes, notes_err = safe_validate(
            MessageInput,
            text="Lunch at the office"
        )
        assert notes is not None
