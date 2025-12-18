"""Timezone detection and management utilities"""
import re
from pathlib import Path
from timezonefinder import TimezoneFinder
import logging

logger = logging.getLogger(__name__)

# Timezone suggestions based on language code
LANGUAGE_TIMEZONE_MAP = {
    'sv': ['Europe/Stockholm', 'Europe/Helsinki'],
    'en': ['America/New_York', 'America/Los_Angeles', 'Europe/London', 'Australia/Sydney'],
    'es': ['Europe/Madrid', 'America/Mexico_City', 'America/Argentina/Buenos_Aires'],
    'de': ['Europe/Berlin', 'Europe/Zurich'],
    'fr': ['Europe/Paris', 'America/Montreal'],
    'pt': ['Europe/Lisbon', 'America/Sao_Paulo'],
    'it': ['Europe/Rome'],
    'no': ['Europe/Oslo'],
    'da': ['Europe/Copenhagen'],
    'fi': ['Europe/Helsinki'],
    'nl': ['Europe/Amsterdam'],
    'pl': ['Europe/Warsaw'],
    'ru': ['Europe/Moscow'],
    'ja': ['Asia/Tokyo'],
    'zh': ['Asia/Shanghai', 'Asia/Hong_Kong'],
    'ko': ['Asia/Seoul'],
}


def get_timezone_from_coordinates(latitude: float, longitude: float) -> str:
    """Get timezone from GPS coordinates"""
    try:
        tf = TimezoneFinder()
        timezone = tf.timezone_at(lat=latitude, lng=longitude)
        if timezone:
            logger.info(f"Detected timezone: {timezone}")
            return timezone
        return "UTC"
    except Exception as e:
        logger.error(f"Error detecting timezone: {e}")
        return "UTC"


def suggest_timezones_for_language(language_code: str) -> list[str]:
    """Suggest timezones based on language code"""
    return LANGUAGE_TIMEZONE_MAP.get(language_code.lower(), ['UTC'])


def update_timezone_in_profile(user_id: str, timezone: str) -> bool:
    """Update timezone in user's profile.md"""
    try:
        profile_path = Path(f"data/{user_id}/profile.md")

        if not profile_path.exists():
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            profile_path.write_text(f"""# User Profile

## Notes
- Timezone: {timezone}
""")
            logger.info(f"Created profile with timezone {timezone}")
            return True

        content = profile_path.read_text()
        timezone_pattern = r'- Timezone:.*'
        
        if re.search(timezone_pattern, content):
            new_content = re.sub(timezone_pattern, f'- Timezone: {timezone}', content)
        else:
            if '## Notes' in content:
                new_content = re.sub(r'(## Notes\s*\n)', f'\\1- Timezone: {timezone}\n', content)
            else:
                new_content = content + f"\n## Notes\n- Timezone: {timezone}\n"

        profile_path.write_text(new_content)
        logger.info(f"Updated timezone to {timezone}")
        return True

    except Exception as e:
        logger.error(f"Error updating timezone: {e}")
        return False


def get_timezone_from_profile(user_id: str) -> str | None:
    """Get timezone from user's profile.md"""
    try:
        profile_path = Path(f"data/{user_id}/profile.md")
        if not profile_path.exists():
            return None

        content = profile_path.read_text()
        match = re.search(r'- Timezone:\s*([^\n]+)', content)
        return match.group(1).strip() if match else None

    except Exception as e:
        logger.error(f"Error reading timezone: {e}")
        return None
