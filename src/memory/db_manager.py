"""PostgreSQL-based memory manager

This module replaces the file-based MemoryFileManager with database-backed storage.
All profile and preference data is now stored in PostgreSQL user_profiles table.
"""
import logging
from typing import Optional
from src.db.queries.user import (
    get_user_profile,
    update_user_profile,
    create_user_profile as db_create_user_profile,
    get_user_profile_field,
    set_user_profile_field,
    get_user_preferences,
    update_user_preference,
)

logger = logging.getLogger(__name__)


class DatabaseMemoryManager:
    """Manage user memory in PostgreSQL database"""

    async def load_user_memory(self, telegram_id: str) -> dict:
        """Load profile and preferences from database

        Returns dict with markdown-formatted strings for backward compatibility:
        {
            "profile": "markdown formatted profile",
            "preferences": "markdown formatted preferences"
        }
        """
        profile_data = await get_user_profile(telegram_id)

        if not profile_data:
            # Create default profile if doesn't exist
            await self.create_user_profile(telegram_id)
            profile_data = await get_user_profile(telegram_id)

        # Format as markdown for backward compatibility with system_prompt.py
        profile_md = await self.format_profile_as_markdown(profile_data['profile_data'])
        preferences_md = await self.format_preferences_as_markdown(profile_data['profile_data'])

        return {
            "profile": profile_md,
            "preferences": preferences_md
        }

    async def create_user_profile(self, telegram_id: str, timezone: str = "UTC") -> None:
        """Initialize default profile for new user"""
        await db_create_user_profile(telegram_id, timezone)
        logger.info(f"Created database profile for user {telegram_id}")

    async def update_profile(self, telegram_id: str, field: str, value: str) -> None:
        """Update profile field with audit logging

        Args:
            telegram_id: User's Telegram ID
            field: Field name (e.g., 'name', 'age', 'goal_type')
            value: New value for field
        """
        await set_user_profile_field(telegram_id, field, value, updated_by="user")
        logger.info(f"Updated profile field {field} for user {telegram_id}")

    async def update_preferences(self, telegram_id: str, preference: str, value: str) -> None:
        """Update preference with audit logging

        Args:
            telegram_id: User's Telegram ID
            preference: Preference name (e.g., 'brevity', 'tone')
            value: New value for preference
        """
        await update_user_preference(telegram_id, preference, value, updated_by="user")
        logger.info(f"Updated preference {preference} for user {telegram_id}")

    async def format_profile_as_markdown(self, profile_data: dict) -> str:
        """Format profile data from database as markdown string

        Maintains compatibility with existing system prompt formatting.
        """
        if not profile_data:
            return "# User Profile\n\nNo profile data recorded yet."

        lines = ["# User Profile\n"]

        # Basic info
        if 'name' in profile_data:
            lines.append(f"- **Name**: {profile_data['name']}")
        if 'age' in profile_data:
            lines.append(f"- **Age**: {profile_data['age']}")
        if 'height_cm' in profile_data:
            lines.append(f"- **Height**: {profile_data['height_cm']} cm")
        if 'current_weight_kg' in profile_data:
            lines.append(f"- **Current Weight**: {profile_data['current_weight_kg']} kg")
        if 'target_weight_kg' in profile_data:
            lines.append(f"- **Target Weight**: {profile_data['target_weight_kg']} kg")

        # Goals
        if 'goal_type' in profile_data:
            lines.append(f"\n## Goals\n- **Goal Type**: {profile_data['goal_type']}")

        # Health info
        health_section = []
        if 'allergies' in profile_data and profile_data['allergies']:
            allergies_str = ', '.join(profile_data['allergies'])
            health_section.append(f"- **Allergies**: {allergies_str}")
        if 'dietary_preferences' in profile_data and profile_data['dietary_preferences']:
            diet_str = ', '.join(profile_data['dietary_preferences'])
            health_section.append(f"- **Dietary Preferences**: {diet_str}")
        if 'health_conditions' in profile_data and profile_data['health_conditions']:
            conditions_str = ', '.join(profile_data['health_conditions'])
            health_section.append(f"- **Health Conditions**: {conditions_str}")
        if 'medications' in profile_data and profile_data['medications']:
            meds_str = ', '.join(profile_data['medications'])
            health_section.append(f"- **Medications**: {meds_str}")

        if health_section:
            lines.append("\n## Health Information")
            lines.extend(health_section)

        # Preferences
        if 'preferred_language' in profile_data:
            lines.append(f"\n- **Language**: {profile_data['preferred_language']}")
        if 'coaching_style' in profile_data:
            lines.append(f"- **Coaching Style**: {profile_data['coaching_style']}")

        return '\n'.join(lines)

    async def format_preferences_as_markdown(self, profile_data: dict) -> str:
        """Format communication preferences from database as markdown string

        Maintains compatibility with existing system prompt formatting.
        """
        if not profile_data or 'communication_preferences' not in profile_data:
            return "# Communication Preferences\n\nNo preferences set yet."

        prefs = profile_data['communication_preferences']
        lines = ["# Communication Preferences\n"]

        if 'brevity' in prefs:
            lines.append(f"- **Brevity**: {prefs['brevity']}  # brief, medium, detailed")
        if 'tone' in prefs:
            lines.append(f"- **Tone**: {prefs['tone']}  # friendly, formal, casual")
        if 'use_humor' in prefs:
            use_humor = "yes" if prefs['use_humor'] else "no"
            lines.append(f"- **Use Humor**: {use_humor}")
        if 'proactive_checkins' in prefs:
            checkins = "yes" if prefs['proactive_checkins'] else "no"
            lines.append(f"- **Proactive Check-ins**: {checkins}")
        if 'daily_summary' in prefs:
            summary = "yes" if prefs['daily_summary'] else "no"
            lines.append(f"- **Daily Summary**: {summary}")

        return '\n'.join(lines)

    async def get_timezone(self, telegram_id: str) -> str:
        """Get user's timezone from database

        Returns:
            Timezone string (e.g., 'America/New_York', 'UTC')
        """
        profile_data = await get_user_profile(telegram_id)
        if profile_data:
            return profile_data['timezone']
        return 'UTC'

    async def set_timezone(self, telegram_id: str, timezone: str) -> None:
        """Set user's timezone in database

        Args:
            telegram_id: User's Telegram ID
            timezone: IANA timezone string (e.g., 'America/New_York')
        """
        profile_data = await get_user_profile(telegram_id)
        if profile_data:
            await update_user_profile(telegram_id, profile_data['profile_data'], timezone)
            logger.info(f"Updated timezone for user {telegram_id} to {timezone}")


# Global instance
db_memory_manager = DatabaseMemoryManager()
