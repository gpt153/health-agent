"""Unit tests for Datetime Helpers (src/utils/datetime_helpers.py)"""
import pytest
from datetime import datetime, date, timezone, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch

from src.utils.datetime_helpers import (
    now_utc,
    today_in_timezone,
    parse_time_string,
    is_same_day,
    days_between,
    add_days_to_date,
    format_relative_time,
)


# ============================================================================
# UTC Time Tests
# ============================================================================

def test_now_utc_returns_utc_time():
    """Test that now_utc returns UTC datetime"""
    result = now_utc()

    assert result.tzinfo == timezone.utc
    assert isinstance(result, datetime)


def test_now_utc_is_current():
    """Test that now_utc returns current time (within 1 second)"""
    before = datetime.now(timezone.utc)
    result = now_utc()
    after = datetime.now(timezone.utc)

    assert before <= result <= after


# ============================================================================
# Timezone Conversion Tests
# ============================================================================

def test_today_in_timezone_utc():
    """Test getting today's date in UTC"""
    result = today_in_timezone("UTC")

    assert isinstance(result, date)


def test_today_in_timezone_eastern():
    """Test getting today's date in Eastern time"""
    result = today_in_timezone("America/New_York")

    assert isinstance(result, date)


def test_today_in_timezone_different_from_utc():
    """Test that timezone can affect date"""
    # At certain hours, dates differ between timezones
    utc_date = today_in_timezone("UTC")
    tokyo_date = today_in_timezone("Asia/Tokyo")

    # Should be valid dates (might be same or differ by 1 day)
    assert isinstance(utc_date, date)
    assert isinstance(tokyo_date, date)
    assert abs((tokyo_date - utc_date).days) <= 1


# ============================================================================
# Time Parsing Tests
# ============================================================================

def test_parse_time_string_valid_24h():
    """Test parsing valid 24-hour time string"""
    result = parse_time_string("14:30")

    assert result.hour == 14
    assert result.minute == 30


def test_parse_time_string_midnight():
    """Test parsing midnight"""
    result = parse_time_string("00:00")

    assert result.hour == 0
    assert result.minute == 0


def test_parse_time_string_end_of_day():
    """Test parsing 23:59"""
    result = parse_time_string("23:59")

    assert result.hour == 23
    assert result.minute == 59


def test_parse_time_string_with_seconds():
    """Test parsing time with seconds"""
    result = parse_time_string("14:30:45")

    assert result.hour == 14
    assert result.minute == 30
    assert result.second == 45


def test_parse_time_string_single_digit():
    """Test parsing time with single digit hour"""
    result = parse_time_string("9:05")

    assert result.hour == 9
    assert result.minute == 5


def test_parse_time_string_invalid():
    """Test parsing invalid time string raises error"""
    with pytest.raises((ValueError, Exception)):
        parse_time_string("25:00")  # Invalid hour


def test_parse_time_string_invalid_format():
    """Test parsing invalid format raises error"""
    with pytest.raises((ValueError, Exception)):
        parse_time_string("not a time")


# ============================================================================
# Date Comparison Tests
# ============================================================================

def test_is_same_day_true():
    """Test is_same_day returns True for same date"""
    dt1 = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    dt2 = datetime(2024, 1, 15, 18, 30, 0, tzinfo=timezone.utc)

    assert is_same_day(dt1, dt2) is True


def test_is_same_day_false():
    """Test is_same_day returns False for different dates"""
    dt1 = datetime(2024, 1, 15, 23, 59, 0, tzinfo=timezone.utc)
    dt2 = datetime(2024, 1, 16, 0, 1, 0, tzinfo=timezone.utc)

    assert is_same_day(dt1, dt2) is False


def test_is_same_day_date_objects():
    """Test is_same_day with date objects"""
    date1 = date(2024, 1, 15)
    date2 = date(2024, 1, 15)

    assert is_same_day(date1, date2) is True


def test_is_same_day_mixed_types():
    """Test is_same_day with mixed datetime and date"""
    dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    d = date(2024, 1, 15)

    assert is_same_day(dt, d) is True


# ============================================================================
# Date Arithmetic Tests
# ============================================================================

def test_days_between_positive():
    """Test days between returns positive difference"""
    date1 = date(2024, 1, 10)
    date2 = date(2024, 1, 15)

    result = days_between(date1, date2)

    assert result == 5


def test_days_between_negative():
    """Test days between with reversed dates"""
    date1 = date(2024, 1, 15)
    date2 = date(2024, 1, 10)

    result = days_between(date1, date2)

    assert result == -5


def test_days_between_zero():
    """Test days between same dates"""
    date1 = date(2024, 1, 15)
    date2 = date(2024, 1, 15)

    result = days_between(date1, date2)

    assert result == 0


def test_days_between_leap_year():
    """Test days between across leap year boundary"""
    date1 = date(2024, 2, 28)
    date2 = date(2024, 3, 1)

    result = days_between(date1, date2)

    assert result == 2  # 2024 is a leap year


def test_add_days_to_date_positive():
    """Test adding positive days"""
    start_date = date(2024, 1, 15)

    result = add_days_to_date(start_date, 10)

    assert result == date(2024, 1, 25)


def test_add_days_to_date_negative():
    """Test subtracting days"""
    start_date = date(2024, 1, 15)

    result = add_days_to_date(start_date, -10)

    assert result == date(2024, 1, 5)


def test_add_days_to_date_zero():
    """Test adding zero days"""
    start_date = date(2024, 1, 15)

    result = add_days_to_date(start_date, 0)

    assert result == start_date


def test_add_days_to_date_month_boundary():
    """Test adding days across month boundary"""
    start_date = date(2024, 1, 28)

    result = add_days_to_date(start_date, 5)

    assert result == date(2024, 2, 2)


def test_add_days_to_date_year_boundary():
    """Test adding days across year boundary"""
    start_date = date(2023, 12, 28)

    result = add_days_to_date(start_date, 5)

    assert result == date(2024, 1, 2)


# ============================================================================
# Relative Time Formatting Tests
# ============================================================================

def test_format_relative_time_just_now():
    """Test formatting time that just happened"""
    now = datetime.now(timezone.utc)
    recent = now - timedelta(seconds=30)

    result = format_relative_time(recent)

    assert "just now" in result.lower() or "seconds" in result.lower()


def test_format_relative_time_minutes_ago():
    """Test formatting time minutes ago"""
    now = datetime.now(timezone.utc)
    recent = now - timedelta(minutes=5)

    result = format_relative_time(recent)

    assert "minute" in result.lower()


def test_format_relative_time_hours_ago():
    """Test formatting time hours ago"""
    now = datetime.now(timezone.utc)
    recent = now - timedelta(hours=3)

    result = format_relative_time(recent)

    assert "hour" in result.lower()


def test_format_relative_time_days_ago():
    """Test formatting time days ago"""
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=2)

    result = format_relative_time(past)

    assert "day" in result.lower()


def test_format_relative_time_weeks_ago():
    """Test formatting time weeks ago"""
    now = datetime.now(timezone.utc)
    past = now - timedelta(weeks=2)

    result = format_relative_time(past)

    assert "week" in result.lower() or "day" in result.lower()


# ============================================================================
# Edge Cases and Timezone Tests
# ============================================================================

def test_timezone_dst_transition():
    """Test handling DST transition"""
    # Spring forward (DST starts)
    eastern = ZoneInfo("America/New_York")

    # Date just before DST
    before_dst = datetime(2024, 3, 10, 1, 0, 0, tzinfo=eastern)

    # Date just after DST
    after_dst = datetime(2024, 3, 10, 3, 0, 0, tzinfo=eastern)

    # Should handle gracefully
    assert before_dst.tzinfo == eastern
    assert after_dst.tzinfo == eastern


def test_parse_time_string_edge_cases():
    """Test parsing edge case time strings"""
    # Midnight
    assert parse_time_string("00:00").hour == 0

    # One minute before midnight
    assert parse_time_string("23:59").hour == 23

    # Noon
    assert parse_time_string("12:00").hour == 12


def test_days_between_large_difference():
    """Test days between with large time difference"""
    date1 = date(2000, 1, 1)
    date2 = date(2024, 1, 1)

    result = days_between(date1, date2)

    # Should handle large differences
    assert result > 8000  # Approximately 24 years


def test_add_days_to_date_large_number():
    """Test adding large number of days"""
    start_date = date(2024, 1, 1)

    result = add_days_to_date(start_date, 365)

    assert result == date(2025, 1, 1)


# ============================================================================
# Timezone Name Handling Tests
# ============================================================================

@pytest.mark.parametrize("tz_name", [
    "UTC",
    "America/New_York",
    "Europe/London",
    "Asia/Tokyo",
    "Australia/Sydney",
    "America/Los_Angeles",
])
def test_today_in_various_timezones(tz_name):
    """Test getting today's date in various timezones"""
    result = today_in_timezone(tz_name)

    assert isinstance(result, date)


def test_invalid_timezone_name():
    """Test handling invalid timezone name"""
    with pytest.raises((ValueError, Exception)):
        today_in_timezone("Invalid/Timezone")


# ============================================================================
# Date Parsing Edge Cases
# ============================================================================

def test_leap_year_feb_29():
    """Test handling Feb 29 in leap year"""
    leap_date = date(2024, 2, 29)

    # Should be valid
    assert leap_date.month == 2
    assert leap_date.day == 29


def test_add_days_across_leap_day():
    """Test adding days across leap day"""
    start = date(2024, 2, 28)
    result = add_days_to_date(start, 2)

    assert result == date(2024, 3, 1)


# ============================================================================
# Time Comparison Edge Cases
# ============================================================================

def test_is_same_day_with_none():
    """Test is_same_day with None value"""
    dt = datetime.now(timezone.utc)

    with pytest.raises((TypeError, AttributeError)):
        is_same_day(dt, None)


def test_days_between_with_datetimes():
    """Test days_between with datetime objects"""
    dt1 = datetime(2024, 1, 10, 8, 0, 0, tzinfo=timezone.utc)
    dt2 = datetime(2024, 1, 15, 20, 0, 0, tzinfo=timezone.utc)

    result = days_between(dt1, dt2)

    assert result == 5  # Should ignore time component
