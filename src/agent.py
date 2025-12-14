"""PydanticAI agent for adaptive health coaching"""
import logging
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4
from datetime import datetime

from pydantic_ai import Agent
from pydantic import BaseModel, Field

from src.config import AGENT_MODEL
from src.models.user import UserPreferences
from src.models.tracking import TrackingCategory, TrackingEntry, TrackingField, TrackingSchedule
from src.db.queries import (
    create_tracking_category,
    save_tracking_entry,
    get_tracking_categories,
)
from src.memory.file_manager import MemoryFileManager
from src.memory.system_prompt import generate_system_prompt

logger = logging.getLogger(__name__)


# Agent dependencies (injected at runtime)
@dataclass
class AgentDeps:
    """Dependencies for agent tools"""

    telegram_id: str
    memory_manager: MemoryFileManager
    user_memory: dict  # Loaded from markdown files
    reminder_manager: object = None  # ReminderManager instance (optional)


# Tool response models
class ProfileUpdateResult(BaseModel):
    """Result of profile update"""

    success: bool
    message: str
    field: str
    value: str


class PreferenceSaveResult(BaseModel):
    """Result of preference save"""

    success: bool
    message: str
    preference: str
    value: str


class TrackingCategoryResult(BaseModel):
    """Result of tracking category creation"""

    success: bool
    message: str
    category_name: str
    category_id: Optional[str] = None


class TrackingEntryResult(BaseModel):
    """Result of tracking entry log"""

    success: bool
    message: str
    category: str
    data: dict


class ReminderScheduleResult(BaseModel):
    """Result of reminder scheduling"""

    success: bool
    message: str
    reminder_time: str
    reminder_message: str


# Initialize agent with model from config
agent = Agent(
    model=AGENT_MODEL,
    system_prompt="",  # Will be dynamically set per conversation
    deps_type=AgentDeps,
)


@agent.tool
async def update_profile(
    ctx, field: str, value: str
) -> ProfileUpdateResult:
    """
    Update user profile field (name, age, height_cm, current_weight_kg, target_weight_kg, goal_type)

    Args:
        field: Profile field to update (name, age, height_cm, etc.)
        value: New value for the field

    Returns:
        ProfileUpdateResult with success status and message
    """
    deps: AgentDeps = ctx.deps

    try:
        # Validate field
        valid_fields = [
            "name",
            "age",
            "height_cm",
            "current_weight_kg",
            "target_weight_kg",
            "goal_type",
        ]
        if field not in valid_fields:
            return ProfileUpdateResult(
                success=False,
                message=f"Invalid field. Valid fields: {', '.join(valid_fields)}",
                field=field,
                value=value,
            )

        # Update profile in memory file
        await deps.memory_manager.update_profile(deps.telegram_id, field, value)

        logger.info(f"Updated profile for {deps.telegram_id}: {field}={value}")

        return ProfileUpdateResult(
            success=True,
            message=f"Profile updated: {field} set to {value}",
            field=field,
            value=value,
        )

    except Exception as e:
        logger.error(f"Failed to update profile: {e}")
        return ProfileUpdateResult(
            success=False,
            message=f"Failed to update profile: {str(e)}",
            field=field,
            value=value,
        )


@agent.tool
async def save_preference(
    ctx, preference: str, value: str
) -> PreferenceSaveResult:
    """
    Save user preference (brevity, tone, humor, coaching_style, wants_daily_summary, wants_proactive_checkins)

    Args:
        preference: Preference to save (brevity, tone, etc.)
        value: New value for the preference

    Returns:
        PreferenceSaveResult with success status and message
    """
    deps: AgentDeps = ctx.deps

    try:
        # Validate preference
        valid_prefs = [
            "brevity",
            "tone",
            "humor",
            "coaching_style",
            "wants_daily_summary",
            "wants_proactive_checkins",
        ]
        if preference not in valid_prefs:
            return PreferenceSaveResult(
                success=False,
                message=f"Invalid preference. Valid: {', '.join(valid_prefs)}",
                preference=preference,
                value=value,
            )

        # Update preferences in memory file
        await deps.memory_manager.update_preferences(
            deps.telegram_id, preference, value
        )

        logger.info(f"Updated preference for {deps.telegram_id}: {preference}={value}")

        return PreferenceSaveResult(
            success=True,
            message=f"Preference updated: {preference} set to {value}",
            preference=preference,
            value=value,
        )

    except Exception as e:
        logger.error(f"Failed to save preference: {e}")
        return PreferenceSaveResult(
            success=False,
            message=f"Failed to save preference: {str(e)}",
            preference=preference,
            value=value,
        )


@agent.tool
async def create_new_tracking_category(
    ctx, name: str, field_name: str, field_type: str, schedule_type: Optional[str] = None
) -> TrackingCategoryResult:
    """
    Create a new tracking category for custom metrics (sleep, mood, workouts, etc.)

    Args:
        name: Category name (e.g., "Sleep Quality", "Workout")
        field_name: Name of the field to track (e.g., "hours", "intensity")
        field_type: Type of field (number, text, rating)
        schedule_type: Optional schedule (daily, weekly, as_needed)

    Returns:
        TrackingCategoryResult with success status and category ID
    """
    deps: AgentDeps = ctx.deps

    try:
        # Create field definition
        field_def = TrackingField(
            type=field_type, label=field_name, required=True
        )

        # Create schedule if specified
        schedule = None
        if schedule_type:
            schedule = TrackingSchedule(
                type=schedule_type if schedule_type != "as_needed" else "custom",
                time="08:00",
                message=f"Time to log your {name}!"
            )

        # Create tracking category
        category_id = str(uuid4())
        category = TrackingCategory(
            id=category_id,
            user_id=deps.telegram_id,
            name=name,
            fields={field_name: field_def},
            schedule=schedule,
            active=True,
        )

        # Save to database
        await create_tracking_category(category)

        logger.info(f"Created tracking category: {name} for user {deps.telegram_id}")

        return TrackingCategoryResult(
            success=True,
            message=f"Created tracking category: {name}",
            category_name=name,
            category_id=category_id,
        )

    except Exception as e:
        logger.error(f"Failed to create tracking category: {e}")
        return TrackingCategoryResult(
            success=False,
            message=f"Failed to create category: {str(e)}",
            category_name=name,
        )


@agent.tool
async def log_tracking_entry(
    ctx, category_name: str, data: dict, notes: Optional[str] = None
) -> TrackingEntryResult:
    """
    Log a tracking entry for an existing category

    Args:
        category_name: Name of the tracking category
        data: Dict of field_name -> value
        notes: Optional notes

    Returns:
        TrackingEntryResult with success status
    """
    deps: AgentDeps = ctx.deps

    try:
        # Find category by name
        categories = await get_tracking_categories(deps.telegram_id, active_only=True)
        category = next((c for c in categories if c["name"] == category_name), None)

        if not category:
            return TrackingEntryResult(
                success=False,
                message=f"Tracking category '{category_name}' not found",
                category=category_name,
                data=data,
            )

        # Create tracking entry
        entry = TrackingEntry(
            id=str(uuid4()),
            user_id=deps.telegram_id,
            category_id=category["id"],
            timestamp=datetime.now(),
            data=data,
            notes=notes,
        )

        # Save to database
        await save_tracking_entry(entry)

        logger.info(
            f"Logged tracking entry: {category_name} for user {deps.telegram_id}"
        )

        return TrackingEntryResult(
            success=True,
            message=f"Logged {category_name} entry",
            category=category_name,
            data=data,
        )

    except Exception as e:
        logger.error(f"Failed to log tracking entry: {e}")
        return TrackingEntryResult(
            success=False,
            message=f"Failed to log entry: {str(e)}",
            category=category_name,
            data=data,
        )


@agent.tool
async def schedule_reminder(
    ctx, reminder_time: str, message: str
) -> ReminderScheduleResult:
    """
    Schedule a daily reminder at a specific time

    Args:
        reminder_time: Time in "HH:MM" format (24-hour, user's local time)
        message: Reminder message to send

    Returns:
        ReminderScheduleResult with success status
    """
    deps: AgentDeps = ctx.deps

    try:
        # Check if reminder_manager is available
        if not deps.reminder_manager:
            return ReminderScheduleResult(
                success=False,
                message="Reminder system not available",
                reminder_time=reminder_time,
                reminder_message=message,
            )

        # Get user's timezone from preferences
        user_memory = deps.user_memory
        prefs_content = user_memory.get("preferences", "")

        # Parse timezone from preferences (default to UTC)
        user_timezone = "UTC"
        for line in prefs_content.split("\n"):
            if "timezone:" in line.lower() or "timezone" in line.lower():
                parts = line.split(":")
                if len(parts) >= 2:
                    user_timezone = parts[-1].strip()
                    break

        # Schedule the reminder
        await deps.reminder_manager.schedule_custom_reminder(
            user_id=deps.telegram_id,
            reminder_time=reminder_time,
            message=message,
            reminder_type="daily",
            user_timezone=user_timezone,
        )

        logger.info(
            f"Scheduled reminder for {deps.telegram_id}: {reminder_time} {user_timezone}"
        )

        return ReminderScheduleResult(
            success=True,
            message=f"Reminder scheduled for {reminder_time} ({user_timezone})",
            reminder_time=reminder_time,
            reminder_message=message,
        )

    except Exception as e:
        logger.error(f"Failed to schedule reminder: {e}", exc_info=True)
        return ReminderScheduleResult(
            success=False,
            message=f"Failed to schedule reminder: {str(e)}",
            reminder_time=reminder_time,
            reminder_message=message,
        )


async def get_agent_response(
    telegram_id: str, user_message: str, memory_manager: MemoryFileManager, reminder_manager=None
) -> str:
    """
    Get agent response with dynamic system prompt and tools

    Args:
        telegram_id: User's Telegram ID
        user_message: User's message
        memory_manager: Memory file manager instance

    Returns:
        Agent's response string
    """
    try:
        # Load user memory from markdown files
        user_memory = await memory_manager.load_user_memory(telegram_id)

        # Generate dynamic system prompt
        system_prompt = generate_system_prompt(user_memory)

        # Create dependencies
        deps = AgentDeps(
            telegram_id=telegram_id,
            memory_manager=memory_manager,
            user_memory=user_memory,
            reminder_manager=reminder_manager,
        )

        # Create agent instance with dynamic system prompt
        # PydanticAI requires system_prompt at agent creation, not in run()
        dynamic_agent = Agent(
            model=AGENT_MODEL,
            system_prompt=system_prompt,
            deps_type=AgentDeps,
        )

        # Register tools on the dynamic agent
        dynamic_agent.tool(update_profile)
        dynamic_agent.tool(save_preference)
        dynamic_agent.tool(create_new_tracking_category)
        dynamic_agent.tool(log_tracking_entry)
        dynamic_agent.tool(schedule_reminder)

        # Run agent
        result = await dynamic_agent.run(user_message, deps=deps)

        return result.output

    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        return f"Sorry, I encountered an error: {str(e)}"
