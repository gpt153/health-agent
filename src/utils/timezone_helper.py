"""Timezone detection and handling utilities"""
import logging
from typing import Optional
from zoneinfo import ZoneInfo, available_timezones

logger = logging.getLogger(__name__)


def detect_timezone_from_telegram(user_data: dict) -> str:
    """
    Attempt to detect timezone from Telegram user data

    Telegram doesn't directly provide timezone, but we can try:
    1. Language code (rough estimate)
    2. Ask user to send location (not implemented)

    Args:
        user_data: User data from Telegram update

    Returns:
        IANA timezone string (defaults to "UTC" if detection fails)
    """
    # Try language code mapping (very rough approximation)
    language_code = user_data.get("language_code", "").lower()

    # Common language -> timezone mappings (approximation only!)
    LANGUAGE_TIMEZONE_MAP = {
        "en": "America/New_York",  # US English (East Coast)
        "es": "America/Mexico_City",  # Spanish (Mexico)
        "pt": "America/Sao_Paulo",  # Portuguese (Brazil)
        "fr": "Europe/Paris",  # French
        "de": "Europe/Berlin",  # German
        "it": "Europe/Rome",  # Italian
        "ru": "Europe/Moscow",  # Russian
        "ja": "Asia/Tokyo",  # Japanese
        "zh": "Asia/Shanghai",  # Chinese
        "ko": "Asia/Seoul",  # Korean
        "ar": "Asia/Dubai",  # Arabic
        "hi": "Asia/Kolkata",  # Hindi (India)
        "tr": "Europe/Istanbul",  # Turkish
    }

    detected_tz = LANGUAGE_TIMEZONE_MAP.get(language_code, "UTC")

    logger.info(
        f"Detected timezone from language '{language_code}': {detected_tz} (approximation)"
    )

    return detected_tz


def validate_timezone(timezone_str: str) -> bool:
    """
    Validate if a timezone string is a valid IANA timezone

    Args:
        timezone_str: IANA timezone string (e.g., "America/New_York")

    Returns:
        True if valid, False otherwise
    """
    try:
        ZoneInfo(timezone_str)
        return True
    except Exception:
        return False


def get_common_timezones() -> list[str]:
    """
    Get list of commonly used timezones for user selection

    Returns:
        List of IANA timezone strings
    """
    return [
        "UTC",
        # Americas
        "America/New_York",  # EST/EDT
        "America/Chicago",  # CST/CDT
        "America/Denver",  # MST/MDT
        "America/Los_Angeles",  # PST/PDT
        "America/Toronto",  # Canada EST
        "America/Vancouver",  # Canada PST
        "America/Mexico_City",
        "America/Sao_Paulo",  # Brazil
        "America/Buenos_Aires",  # Argentina
        # Europe
        "Europe/London",  # GMT/BST
        "Europe/Paris",  # CET/CEST
        "Europe/Berlin",
        "Europe/Rome",
        "Europe/Madrid",
        "Europe/Moscow",
        "Europe/Istanbul",
        # Asia
        "Asia/Dubai",
        "Asia/Kolkata",  # India
        "Asia/Shanghai",  # China
        "Asia/Tokyo",  # Japan
        "Asia/Seoul",  # South Korea
        "Asia/Singapore",
        "Asia/Hong_Kong",
        "Asia/Bangkok",
        # Oceania
        "Australia/Sydney",
        "Australia/Melbourne",
        "Pacific/Auckland",  # New Zealand
        # Africa
        "Africa/Cairo",
        "Africa/Johannesburg",
        "Africa/Lagos",
    ]


def find_timezone_by_city(city_name: str) -> Optional[str]:
    """
    Find timezone by city name (fuzzy match)

    Args:
        city_name: City name (e.g., "New York", "London", "Tokyo")

    Returns:
        IANA timezone string or None if not found
    """
    city_lower = city_name.lower().replace(" ", "_")

    # Search in available timezones
    for tz in available_timezones():
        if city_lower in tz.lower():
            return tz

    # Common city name mappings
    CITY_MAPPINGS = {
        "nyc": "America/New_York",
        "la": "America/Los_Angeles",
        "sf": "America/Los_Angeles",
        "seattle": "America/Los_Angeles",
        "chicago": "America/Chicago",
        "london": "Europe/London",
        "paris": "Europe/Paris",
        "berlin": "Europe/Berlin",
        "tokyo": "Asia/Tokyo",
        "beijing": "Asia/Shanghai",
        "shanghai": "Asia/Shanghai",
        "sydney": "Australia/Sydney",
        "melbourne": "Australia/Melbourne",
        "dubai": "Asia/Dubai",
        "mumbai": "Asia/Kolkata",
        "delhi": "Asia/Kolkata",
        "moscow": "Europe/Moscow",
    }

    return CITY_MAPPINGS.get(city_lower)


def format_timezone_for_display(timezone_str: str) -> str:
    """
    Format timezone string for user-friendly display

    Args:
        timezone_str: IANA timezone string

    Returns:
        Formatted string (e.g., "America/New_York (EST/EDT)")
    """
    try:
        tz = ZoneInfo(timezone_str)
        # Get current UTC offset
        from datetime import datetime

        now = datetime.now(tz)
        offset = now.strftime("%z")
        offset_formatted = f"{offset[:3]}:{offset[3:]}"

        return f"{timezone_str} (UTC{offset_formatted})"
    except Exception:
        return timezone_str
