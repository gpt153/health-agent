"""
Standardized Date/Time Handling Utilities

This module provides centralized functions for date/time operations to ensure:
1. All DB timestamps stored in UTC
2. All user-facing times displayed in user's timezone
3. All user input parsed assuming user's timezone
4. Consistent date/time handling across the application

CRITICAL RULES:
- Always store datetimes in DB as UTC (use to_utc())
- Always display to users in their timezone (use to_user_timezone())
- Always parse user input in their timezone (use parse_user_datetime())
- Never mix naive and aware datetimes
"""

import logging
from datetime import datetime, date, time, timedelta
from typing import Optional, Union
from zoneinfo import ZoneInfo
import pytz

from src.utils.timezone_helper import get_timezone_from_profile

logger = logging.getLogger(__name__)

# Default timezone if user hasn't set one
DEFAULT_TIMEZONE = "UTC"


def get_user_timezone(user_id: str) -> ZoneInfo:
    """
    Get user's timezone from profile, or return default

    Args:
        user_id: User's Telegram ID

    Returns:
        ZoneInfo object for user's timezone
    """
    tz_str = get_timezone_from_profile(user_id)
    if not tz_str:
        tz_str = DEFAULT_TIMEZONE
        logger.debug(f"No timezone set for user {user_id}, using {DEFAULT_TIMEZONE}")

    try:
        return ZoneInfo(tz_str)
    except Exception as e:
        logger.error(f"Invalid timezone '{tz_str}' for user {user_id}: {e}")
        return ZoneInfo(DEFAULT_TIMEZONE)


def now_utc() -> datetime:
    """
    Get current datetime in UTC (timezone-aware)

    Returns:
        Current datetime in UTC with timezone info
    """
    return datetime.now(ZoneInfo("UTC"))


def now_user_timezone(user_id: str) -> datetime:
    """
    Get current datetime in user's timezone

    Args:
        user_id: User's Telegram ID

    Returns:
        Current datetime in user's timezone
    """
    user_tz = get_user_timezone(user_id)
    return datetime.now(user_tz)


def today_user_timezone(user_id: str) -> date:
    """
    Get today's date in user's timezone

    Args:
        user_id: User's Telegram ID

    Returns:
        Today's date in user's timezone
    """
    return now_user_timezone(user_id).date()


def to_utc(dt: datetime, user_id: Optional[str] = None) -> datetime:
    """
    Convert datetime to UTC for database storage

    Args:
        dt: Datetime to convert (can be naive or aware)
        user_id: User's Telegram ID (required if dt is naive)

    Returns:
        Timezone-aware datetime in UTC

    Raises:
        ValueError: If dt is naive and user_id is not provided
    """
    if dt.tzinfo is None:
        # Naive datetime - assume user's timezone
        if not user_id:
            raise ValueError("user_id required for naive datetime conversion to UTC")

        user_tz = get_user_timezone(user_id)
        dt = dt.replace(tzinfo=user_tz)
        logger.debug(f"Converted naive datetime to {user_tz}: {dt}")

    # Convert to UTC
    utc_dt = dt.astimezone(ZoneInfo("UTC"))
    return utc_dt


def to_user_timezone(dt: datetime, user_id: str) -> datetime:
    """
    Convert datetime from UTC to user's timezone for display

    Args:
        dt: Datetime in UTC (should be timezone-aware)
        user_id: User's Telegram ID

    Returns:
        Datetime in user's timezone
    """
    if dt.tzinfo is None:
        # Assume UTC if naive
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        logger.warning(f"Received naive datetime, assuming UTC: {dt}")

    user_tz = get_user_timezone(user_id)
    return dt.astimezone(user_tz)


def parse_user_time(time_str: str) -> time:
    """
    Parse time string (HH:MM format) to time object

    Args:
        time_str: Time string in HH:MM format (e.g., "14:30")

    Returns:
        time object

    Raises:
        ValueError: If time_str is not in HH:MM format
    """
    try:
        hour, minute = map(int, time_str.split(":"))
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError(f"Invalid time: {time_str}")
        return time(hour, minute)
    except Exception as e:
        raise ValueError(f"Invalid time format '{time_str}'. Expected HH:MM") from e


def parse_user_date(date_str: str) -> date:
    """
    Parse date string to date object

    Supports formats:
    - YYYY-MM-DD (ISO format)
    - MM/DD/YYYY
    - DD/MM/YYYY

    Args:
        date_str: Date string

    Returns:
        date object

    Raises:
        ValueError: If date_str format is not recognized
    """
    # Try ISO format first
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        pass

    # Try MM/DD/YYYY
    try:
        return datetime.strptime(date_str, "%m/%d/%Y").date()
    except ValueError:
        pass

    # Try DD/MM/YYYY
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").date()
    except ValueError:
        raise ValueError(f"Invalid date format '{date_str}'. Expected YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY")


def parse_user_datetime(
    dt_str: str,
    user_id: str,
    format: str = "%Y-%m-%d %H:%M"
) -> datetime:
    """
    Parse datetime string assuming user's timezone

    Args:
        dt_str: Datetime string
        user_id: User's Telegram ID
        format: strptime format string (default: YYYY-MM-DD HH:MM)

    Returns:
        Timezone-aware datetime in user's timezone

    Raises:
        ValueError: If dt_str doesn't match format
    """
    try:
        naive_dt = datetime.strptime(dt_str, format)
        user_tz = get_user_timezone(user_id)
        aware_dt = naive_dt.replace(tzinfo=user_tz)
        return aware_dt
    except Exception as e:
        raise ValueError(f"Invalid datetime format '{dt_str}'. Expected format: {format}") from e


def combine_date_time_user_tz(
    date_obj: date,
    time_obj: time,
    user_id: str
) -> datetime:
    """
    Combine date and time into datetime in user's timezone

    Args:
        date_obj: Date
        time_obj: Time
        user_id: User's Telegram ID

    Returns:
        Timezone-aware datetime in user's timezone
    """
    user_tz = get_user_timezone(user_id)
    naive_dt = datetime.combine(date_obj, time_obj)
    aware_dt = naive_dt.replace(tzinfo=user_tz)
    return aware_dt


def format_datetime_user_tz(
    dt: datetime,
    user_id: str,
    format: str = "%Y-%m-%d %H:%M"
) -> str:
    """
    Format datetime for display to user in their timezone

    Args:
        dt: Datetime (should be timezone-aware, assumed UTC if naive)
        user_id: User's Telegram ID
        format: strftime format string (default: YYYY-MM-DD HH:MM)

    Returns:
        Formatted datetime string in user's timezone
    """
    user_dt = to_user_timezone(dt, user_id)
    return user_dt.strftime(format)


def format_time_user_friendly(dt: datetime, user_id: str) -> str:
    """
    Format datetime in a user-friendly way (e.g., "Today at 14:30", "Yesterday at 09:00")

    Args:
        dt: Datetime (assumed UTC if naive)
        user_id: User's Telegram ID

    Returns:
        User-friendly formatted string
    """
    user_dt = to_user_timezone(dt, user_id)
    now = now_user_timezone(user_id)
    today = now.date()
    dt_date = user_dt.date()

    time_str = user_dt.strftime("%H:%M")

    if dt_date == today:
        return f"Today at {time_str}"
    elif dt_date == today - timedelta(days=1):
        return f"Yesterday at {time_str}"
    elif dt_date == today + timedelta(days=1):
        return f"Tomorrow at {time_str}"
    elif (today - dt_date).days <= 7:
        # Within last week
        day_name = user_dt.strftime("%A")
        return f"{day_name} at {time_str}"
    else:
        # Older than a week
        return user_dt.strftime("%b %d at %H:%M")


def is_same_day_user_tz(dt1: datetime, dt2: datetime, user_id: str) -> bool:
    """
    Check if two datetimes are on the same day in user's timezone

    Args:
        dt1: First datetime
        dt2: Second datetime
        user_id: User's Telegram ID

    Returns:
        True if same day, False otherwise
    """
    user_dt1 = to_user_timezone(dt1, user_id)
    user_dt2 = to_user_timezone(dt2, user_id)
    return user_dt1.date() == user_dt2.date()


def get_day_start_utc(date_obj: date, user_id: str) -> datetime:
    """
    Get the start of a day (00:00) in UTC for a given date in user's timezone

    Args:
        date_obj: Date in user's timezone
        user_id: User's Telegram ID

    Returns:
        Datetime at start of day (00:00) in UTC
    """
    user_tz = get_user_timezone(user_id)
    day_start = datetime.combine(date_obj, time.min)
    day_start = day_start.replace(tzinfo=user_tz)
    return to_utc(day_start)


def get_day_end_utc(date_obj: date, user_id: str) -> datetime:
    """
    Get the end of a day (23:59:59) in UTC for a given date in user's timezone

    Args:
        date_obj: Date in user's timezone
        user_id: User's Telegram ID

    Returns:
        Datetime at end of day (23:59:59) in UTC
    """
    user_tz = get_user_timezone(user_id)
    day_end = datetime.combine(date_obj, time.max)
    day_end = day_end.replace(tzinfo=user_tz)
    return to_utc(day_end)


def get_next_occurrence(
    time_obj: time,
    user_id: str,
    from_dt: Optional[datetime] = None
) -> datetime:
    """
    Get the next occurrence of a time in user's timezone

    Args:
        time_obj: Time to find next occurrence of
        user_id: User's Telegram ID
        from_dt: Start datetime (defaults to now)

    Returns:
        Datetime of next occurrence in UTC
    """
    if from_dt is None:
        from_dt = now_user_timezone(user_id)
    else:
        from_dt = to_user_timezone(from_dt, user_id)

    # Combine with today's date
    next_occurrence = datetime.combine(from_dt.date(), time_obj)
    next_occurrence = next_occurrence.replace(tzinfo=from_dt.tzinfo)

    # If time has already passed today, move to tomorrow
    if next_occurrence <= from_dt:
        next_occurrence += timedelta(days=1)

    return to_utc(next_occurrence)


def seconds_until(target_dt: datetime, user_id: Optional[str] = None) -> int:
    """
    Calculate seconds until a target datetime

    Args:
        target_dt: Target datetime (assumed UTC if naive)
        user_id: Optional user ID for logging

    Returns:
        Number of seconds until target (can be negative if in past)
    """
    now = now_utc()
    if target_dt.tzinfo is None:
        target_dt = target_dt.replace(tzinfo=ZoneInfo("UTC"))

    delta = target_dt - now
    return int(delta.total_seconds())


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensure datetime is in UTC (for database queries)

    Args:
        dt: Datetime (can be None, naive, or aware)

    Returns:
        Datetime in UTC, or None if input was None
    """
    if dt is None:
        return None

    if dt.tzinfo is None:
        # Assume UTC for naive datetimes
        logger.warning(f"Received naive datetime, assuming UTC: {dt}")
        return dt.replace(tzinfo=ZoneInfo("UTC"))

    return dt.astimezone(ZoneInfo("UTC"))
