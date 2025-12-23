"""PydanticAI agent for adaptive health coaching"""
import logging
import re
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4
from datetime import datetime

from pydantic_ai import Agent, ModelMessagesTypeAdapter, RunContext
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart
from pydantic import BaseModel, Field

from src.config import AGENT_MODEL
from src.models.user import UserPreferences
from src.models.tracking import TrackingCategory, TrackingEntry, TrackingField, TrackingSchedule
from src.db.queries import (
    create_tracking_category,
    save_tracking_entry,
    get_tracking_categories,
    get_food_entries_by_date,
    update_food_entry,
    save_dynamic_tool,
    get_tool_by_name,
    create_tool_approval_request,
    create_user,
    user_exists,
    generate_adaptive_suggestions,
)
from src.memory.file_manager import MemoryFileManager
from src.memory.system_prompt import generate_system_prompt
from src.utils.datetime_helpers import now_utc, today_user_timezone
from src.agent.dynamic_tools import (
    validate_tool_code,
    classify_tool_type,
    tool_manager,
    CodeValidationError
)

logger = logging.getLogger(__name__)


# Agent dependencies (injected at runtime)
@dataclass
class AgentDeps:
    """Dependencies for agent tools"""

    telegram_id: str
    memory_manager: MemoryFileManager
    user_memory: dict  # Loaded from markdown files
    reminder_manager: object = None  # ReminderManager instance (optional)
    bot_application: object = None  # Telegram bot application for notifications (optional)


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


class RemindersListResult(BaseModel):
    """Result of getting user's reminders"""

    success: bool
    message: str
    reminders: list[dict]


class ReminderStatisticsResult(BaseModel):
    """Result of getting reminder statistics"""

    success: bool
    message: str
    formatted_stats: Optional[str] = None
    analytics: Optional[dict] = None


class ReminderOperationResult(BaseModel):
    """Result of reminder delete/update operation"""

    success: bool
    message: str
    reminder_id: Optional[str] = None


class CleanupResult(BaseModel):
    """Result of cleanup operation"""

    success: bool
    message: str
    checked: int = 0
    deactivated: int = 0
    groups: int = 0


class FoodSummaryResult(BaseModel):
    """Result of food summary query"""

    success: bool
    message: str
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    entry_count: int


class FoodEntryUpdateResult(BaseModel):
    """Result of food entry update/correction"""

    success: bool
    message: str
    entry_id: Optional[str] = None
    old_calories: Optional[float] = None
    new_calories: Optional[float] = None
    correction_note: Optional[str] = None


class RememberFactResult(BaseModel):
    """Result of explicit fact remembering"""

    success: bool
    message: str
    fact: str
    category: str


class VisualPatternResult(BaseModel):
    """Result of visual pattern save"""

    success: bool
    message: str
    item_name: str


class UserInfoResult(BaseModel):
    """Result of saving user information"""

    success: bool
    message: str
    category: str


class AddUserResult(BaseModel):
    """Result of adding a new user"""

    success: bool
    message: str
    user_id: str


class InviteCodeResult(BaseModel):
    """Result of generating invite code"""

    success: bool
    message: str
    code: Optional[str] = None


class AdaptiveSuggestionsResult(BaseModel):
    """Result of adaptive suggestions"""

    success: bool
    message: str
    suggestions: list[dict]
    reminder_name: str


class AchievementsResult(BaseModel):
    """Result of viewing achievements"""

    success: bool
    message: str
    unlocked_count: int
    total_count: int


class DynamicToolCreationResult(BaseModel):
    """Result of dynamic tool creation"""

    success: bool
    message: str
    tool_name: str
    tool_type: str  # 'read' or 'write'
    requires_approval: bool
    approval_id: Optional[str] = None


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

        # Create tracking entry with UTC timestamp
        entry = TrackingEntry(
            id=str(uuid4()),
            user_id=deps.telegram_id,
            category_id=category["id"],
            timestamp=now_utc(),
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

        # Smart detection: determine if tracking should be enabled
        from src.agent.reminder_utils import should_enable_tracking

        enable_tracking, detection_reason = should_enable_tracking(message)

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

        # Check for duplicate reminders before creating
        from src.db.queries import get_active_reminders
        existing_reminders = await get_active_reminders(deps.telegram_id)

        for existing in existing_reminders:
            existing_schedule = existing.get("schedule", {})
            if isinstance(existing_schedule, str):
                existing_schedule = json.loads(existing_schedule)

            existing_time = existing_schedule.get("time")
            existing_tz = existing_schedule.get("timezone", "UTC")
            existing_msg = existing.get("message", "")

            # Check for exact duplicate
            if (existing_msg == message and
                existing_time == reminder_time and
                existing_tz == user_timezone):

                return ReminderScheduleResult(
                    success=False,
                    message=(
                        f"⚠️ You already have this reminder scheduled!\n\n"
                        f"📝 Message: {message}\n"
                        f"⏰ Time: {reminder_time} {user_timezone}\n\n"
                        f"If you want to modify it, ask me to delete it first, "
                        f"then create a new one."
                    ),
                    reminder_time=reminder_time,
                    reminder_message=message,
                )

        # Save reminder to database for persistence
        from src.models.reminder import Reminder, ReminderSchedule
        from src.db.queries import create_reminder
        from uuid import uuid4

        reminder_id = str(uuid4())
        reminder_obj = Reminder(
            id=reminder_id,
            user_id=deps.telegram_id,
            reminder_type="daily",
            message=message,
            schedule=ReminderSchedule(
                type="daily",
                time=reminder_time,
                timezone=user_timezone
            ),
            active=True,
            enable_completion_tracking=enable_tracking,
            streak_motivation=enable_tracking
        )

        # Save to database first
        await create_reminder(reminder_obj)

        # Log feature usage
        from src.db.queries import log_feature_usage
        await log_feature_usage(deps.telegram_id, "reminders")

        # Then schedule in JobQueue
        await deps.reminder_manager.schedule_custom_reminder(
            user_id=deps.telegram_id,
            reminder_time=reminder_time,
            message=message,
            reminder_type="daily",
            user_timezone=user_timezone,
            reminder_id=reminder_id
        )

        # Build response message
        response_message = f"Reminder scheduled for {reminder_time} ({user_timezone})"

        if enable_tracking:
            response_message += "\n\n✅ **Completion tracking enabled**"
            if detection_reason:
                response_message += f"\n💡 {detection_reason}"
            response_message += "\n\nYou'll see a 'Done' button to mark completion, track streaks, and view statistics!"

        logger.info(
            f"Scheduled and saved reminder for {deps.telegram_id}: {reminder_time} {user_timezone} "
            f"(tracking={enable_tracking})"
        )

        return ReminderScheduleResult(
            success=True,
            message=response_message,
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


@agent.tool
async def get_user_reminders(ctx) -> RemindersListResult:
    """
    Get all active reminders for the current user

    Returns:
        RemindersListResult with list of active reminders
    """
    deps: AgentDeps = ctx.deps

    try:
        from src.db.queries import get_active_reminders

        reminders = await get_active_reminders(deps.telegram_id)

        if not reminders:
            return RemindersListResult(
                success=True,
                message="You have no active reminders",
                reminders=[]
            )

        # Format reminders for display
        reminder_list = []
        for r in reminders:
            schedule = r.get('schedule', {})
            reminder_list.append({
                'id': r.get('id'),
                'message': r.get('message'),
                'time': schedule.get('time'),
                'type': r.get('reminder_type'),
                'timezone': schedule.get('timezone', 'UTC')
            })

        count = len(reminders)
        return RemindersListResult(
            success=True,
            message=f"You have {count} active reminder{'s' if count > 1 else ''}",
            reminders=reminder_list
        )

    except Exception as e:
        logger.error(f"Error getting reminders: {e}", exc_info=True)
        return RemindersListResult(
            success=False,
            message=f"Error: {str(e)}",
            reminders=[]
        )


@agent.tool
async def get_reminder_statistics(
    ctx,
    reminder_description: str,
    period: str = "month",
    show_day_patterns: bool = False
) -> ReminderStatisticsResult:
    """
    Get completion statistics for a specific reminder

    Args:
        reminder_description: Description or part of reminder message (e.g., "vitamin D", "medication")
        period: Time period to analyze - "week" (7 days), "month" (30 days), "all" (60 days)
        show_day_patterns: Whether to include day-of-week breakdown

    Returns:
        ReminderStatisticsResult with formatted statistics
    """
    deps: AgentDeps = ctx.deps

    try:
        from src.db.queries import (
            get_active_reminders,
            get_reminder_analytics,
            analyze_day_of_week_patterns
        )
        from src.utils.reminder_formatters import (
            format_reminder_statistics,
            format_day_of_week_patterns
        )

        # Find reminder by description
        reminders = await get_active_reminders(deps.telegram_id)

        if not reminders:
            return ReminderStatisticsResult(
                success=False,
                message="You have no active reminders. Create one first!",
                formatted_stats=None,
                analytics=None
            )

        # Find matching reminder (case-insensitive partial match)
        description_lower = reminder_description.lower()
        matching_reminder = None

        for r in reminders:
            message = r.get('message', '').lower()
            if description_lower in message:
                matching_reminder = r
                break

        if not matching_reminder:
            # If no match, list available reminders
            reminder_list = "\n".join([f"• {r.get('message')}" for r in reminders[:5]])
            return ReminderStatisticsResult(
                success=False,
                message=f"No reminder found matching '{reminder_description}'.\n\nYour reminders:\n{reminder_list}",
                formatted_stats=None,
                analytics=None
            )

        # Map period to days
        period_days = {
            "week": 7,
            "month": 30,
            "all": 60
        }.get(period.lower(), 30)

        # Get analytics
        reminder_id = matching_reminder['id']
        reminder_message = matching_reminder['message']

        analytics = await get_reminder_analytics(
            user_id=deps.telegram_id,
            reminder_id=str(reminder_id),
            days=period_days
        )

        if "error" in analytics:
            return ReminderStatisticsResult(
                success=False,
                message=analytics["error"],
                formatted_stats=None,
                analytics=None
            )

        # Format statistics
        formatted_stats = format_reminder_statistics(analytics, reminder_message)

        # Add day patterns if requested
        if show_day_patterns:
            patterns = await analyze_day_of_week_patterns(
                user_id=deps.telegram_id,
                reminder_id=str(reminder_id),
                days=period_days
            )
            pattern_formatted = format_day_of_week_patterns(patterns, reminder_message)
            formatted_stats += f"\n\n{pattern_formatted}"

        return ReminderStatisticsResult(
            success=True,
            message=formatted_stats,
            formatted_stats=formatted_stats,
            analytics=analytics
        )

    except Exception as e:
        logger.error(f"Error getting reminder statistics: {e}", exc_info=True)
        return ReminderStatisticsResult(
            success=False,
            message=f"Error retrieving statistics: {str(e)}",
            formatted_stats=None,
            analytics=None
        )


@agent.tool
async def compare_all_reminders(ctx, period: str = "month") -> ReminderStatisticsResult:
    """
    Compare completion rates across all tracked reminders

    Args:
        period: Time period to analyze - "week" (7 days), "month" (30 days), "all" (60 days)

    Returns:
        ReminderStatisticsResult with comparison table
    """
    deps: AgentDeps = ctx.deps

    try:
        from src.db.queries import get_multi_reminder_comparison
        from src.utils.reminder_formatters import format_multi_reminder_comparison

        # Map period to days
        period_days = {
            "week": 7,
            "month": 30,
            "all": 60
        }.get(period.lower(), 30)

        # Get comparison data
        comparisons = await get_multi_reminder_comparison(
            user_id=deps.telegram_id,
            days=period_days
        )

        # Format for display
        formatted_stats = format_multi_reminder_comparison(comparisons)

        return ReminderStatisticsResult(
            success=True,
            message=formatted_stats,
            formatted_stats=formatted_stats,
            analytics={"comparisons": comparisons, "period_days": period_days}
        )

    except Exception as e:
        logger.error(f"Error comparing reminders: {e}", exc_info=True)
        return ReminderStatisticsResult(
            success=False,
            message=f"Error comparing reminders: {str(e)}",
            formatted_stats=None,
            analytics=None
        )


@agent.tool
async def suggest_reminder_optimizations(
    ctx,
    reminder_description: str
) -> AdaptiveSuggestionsResult:
    """
    Get personalized suggestions for improving reminder completion

    Analyzes user's completion patterns and suggests optimizations like:
    - Adjusting reminder time to match actual completion patterns
    - Adding support for difficult days (e.g., Thursday struggles)
    - Splitting schedule (different times for weekdays vs weekends)

    Args:
        reminder_description: Description of reminder (e.g., "vitamin D", "medication")

    Returns:
        AdaptiveSuggestionsResult with list of actionable suggestions
    """
    deps: AgentDeps = ctx.deps

    try:
        # Find reminder by description
        from src.db.queries import get_active_reminders
        from src.utils.reminder_formatters import format_adaptive_suggestions

        reminders = await get_active_reminders(deps.telegram_id)

        # Find matching reminder
        matching_reminder = None
        for reminder in reminders:
            if reminder_description.lower() in reminder['message'].lower():
                matching_reminder = reminder
                break

        if not matching_reminder:
            return AdaptiveSuggestionsResult(
                success=False,
                message=f"Could not find a reminder matching '{reminder_description}'",
                suggestions=[],
                reminder_name=reminder_description
            )

        # Generate suggestions
        suggestions = await generate_adaptive_suggestions(
            deps.telegram_id,
            matching_reminder['id']
        )

        if not suggestions:
            return AdaptiveSuggestionsResult(
                success=True,
                message=f"✅ Your '{matching_reminder['message']}' reminder is working great! No optimizations needed right now.",
                suggestions=[],
                reminder_name=matching_reminder['message']
            )

        # Format suggestions for display
        formatted_message = format_adaptive_suggestions(
            suggestions,
            matching_reminder['message']
        )

        return AdaptiveSuggestionsResult(
            success=True,
            message=formatted_message,
            suggestions=suggestions,
            reminder_name=matching_reminder['message']
        )

    except Exception as e:
        logger.error(f"Error generating suggestions: {e}", exc_info=True)
        return AdaptiveSuggestionsResult(
            success=False,
            message=f"Error analyzing reminder patterns: {str(e)}",
            suggestions=[],
            reminder_name=reminder_description
        )


@agent.tool
async def delete_reminder(ctx, reminder_id: str) -> ReminderOperationResult:
    """
    Delete a reminder by its ID

    Args:
        reminder_id: The UUID of the reminder to delete

    Returns:
        ReminderOperationResult with success status
    """
    deps: AgentDeps = ctx.deps

    try:
        from src.db.queries import delete_reminder as db_delete_reminder
        from src.db.queries import get_reminder_by_id

        # Get reminder details for confirmation message
        reminder = await get_reminder_by_id(reminder_id)

        if not reminder:
            return ReminderOperationResult(
                success=False,
                message=f"❌ Reminder not found: {reminder_id}",
                reminder_id=reminder_id
            )

        # Security: Verify it belongs to this user
        if reminder["user_id"] != deps.telegram_id:
            return ReminderOperationResult(
                success=False,
                message="❌ You can only delete your own reminders",
                reminder_id=reminder_id
            )

        # Delete from database
        deleted = await db_delete_reminder(reminder_id, deps.telegram_id)

        if not deleted:
            return ReminderOperationResult(
                success=False,
                message=f"❌ Failed to delete reminder {reminder_id}",
                reminder_id=reminder_id
            )

        # Cancel from job queue
        if deps.reminder_manager:
            await deps.reminder_manager.cancel_reminder_by_id(reminder_id)

        # Format confirmation
        schedule = reminder.get("schedule", {})
        if isinstance(schedule, str):
            schedule = json.loads(schedule)

        message_text = reminder.get("message", "")
        time_str = schedule.get("time", "")
        tz_str = schedule.get("timezone", "UTC")

        return ReminderOperationResult(
            success=True,
            message=(
                f"✅ Deleted reminder:\n\n"
                f"📝 {message_text}\n"
                f"⏰ {time_str} {tz_str}"
            ),
            reminder_id=reminder_id
        )

    except Exception as e:
        logger.error(f"Error deleting reminder: {e}", exc_info=True)
        return ReminderOperationResult(
            success=False,
            message=f"❌ Error: {str(e)}",
            reminder_id=reminder_id
        )


@agent.tool
async def update_reminder(
    ctx,
    reminder_id: str,
    new_time: Optional[str] = None,
    new_message: Optional[str] = None
) -> ReminderOperationResult:
    """
    Update an existing reminder's time or message

    Args:
        reminder_id: The UUID of the reminder to update
        new_time: New time in "HH:MM" format (optional)
        new_message: New reminder message (optional)

    Returns:
        ReminderOperationResult with success status
    """
    deps: AgentDeps = ctx.deps

    try:
        from src.db.queries import (
            update_reminder as db_update_reminder,
            get_reminder_by_id
        )

        # Validate at least one field to update
        if new_time is None and new_message is None:
            return ReminderOperationResult(
                success=False,
                message="❌ Please specify what to update (time or message)",
                reminder_id=reminder_id
            )

        # Get current reminder
        reminder = await get_reminder_by_id(reminder_id)

        if not reminder:
            return ReminderOperationResult(
                success=False,
                message=f"❌ Reminder not found: {reminder_id}",
                reminder_id=reminder_id
            )

        # Security check
        if reminder["user_id"] != deps.telegram_id:
            return ReminderOperationResult(
                success=False,
                message="❌ You can only update your own reminders",
                reminder_id=reminder_id
            )

        # Update in database
        updated = await db_update_reminder(
            reminder_id=reminder_id,
            user_id=deps.telegram_id,
            new_time=new_time,
            new_message=new_message
        )

        if not updated:
            return ReminderOperationResult(
                success=False,
                message=f"❌ Failed to update reminder {reminder_id}",
                reminder_id=reminder_id
            )

        # Reschedule in job queue
        if deps.reminder_manager:
            # Cancel old job
            await deps.reminder_manager.cancel_reminder_by_id(reminder_id)

            # Parse updated schedule
            updated_schedule = updated["schedule"]
            if isinstance(updated_schedule, str):
                updated_schedule = json.loads(updated_schedule)

            # Schedule new job
            await deps.reminder_manager.schedule_custom_reminder(
                user_id=deps.telegram_id,
                reminder_time=updated_schedule.get("time"),
                message=updated["message"],
                reminder_type="daily",
                user_timezone=updated_schedule.get("timezone", "UTC"),
                reminder_id=reminder_id,
                days=updated_schedule.get("days", list(range(7)))
            )

        # Format confirmation
        changes = []
        if new_time:
            changes.append(f"⏰ Time: {new_time}")
        if new_message:
            changes.append(f"📝 Message: {new_message}")

        return ReminderOperationResult(
            success=True,
            message=(
                f"✅ Updated reminder:\n\n"
                + "\n".join(changes)
            ),
            reminder_id=reminder_id
        )

    except Exception as e:
        logger.error(f"Error updating reminder: {e}", exc_info=True)
        return ReminderOperationResult(
            success=False,
            message=f"❌ Error: {str(e)}",
            reminder_id=reminder_id
        )


@agent.tool
async def cleanup_duplicate_reminders(ctx) -> CleanupResult:
    """
    Find and remove duplicate reminders for the current user

    Keeps the oldest reminder when duplicates are found (same message, time, timezone).

    Returns:
        CleanupResult with counts of duplicates found and removed
    """
    deps: AgentDeps = ctx.deps

    try:
        from src.db.queries import (
            find_duplicate_reminders,
            deactivate_duplicate_reminders
        )

        # Find duplicates for this user
        duplicates = await find_duplicate_reminders(user_id=deps.telegram_id)

        if not duplicates:
            return CleanupResult(
                success=True,
                message="✅ No duplicate reminders found! Your reminders are clean.",
                checked=0,
                deactivated=0,
                groups=0
            )

        # Deactivate duplicates
        result = await deactivate_duplicate_reminders(user_id=deps.telegram_id)

        # Cancel jobs for deactivated reminders
        if deps.reminder_manager:
            for dup in duplicates:
                # Get the remove_ids and cancel their jobs
                remove_ids = dup.get("remove_ids", [])
                for rid in remove_ids:
                    await deps.reminder_manager.cancel_reminder_by_id(str(rid))

        # Format result message
        message = (
            f"✅ **Cleanup Complete**\n\n"
            f"📊 Found {result['groups']} groups with duplicates\n"
            f"🗑️ Removed {result['deactivated']} duplicate reminders\n"
            f"✅ Kept {result['groups']} original reminders\n\n"
            f"Your reminders are now clean! "
            f"You should only receive one notification per reminder."
        )

        return CleanupResult(
            success=True,
            message=message,
            checked=result["checked"],
            deactivated=result["deactivated"],
            groups=result["groups"]
        )

    except Exception as e:
        logger.error(f"Error cleaning up duplicates: {e}", exc_info=True)
        return CleanupResult(
            success=False,
            message=f"❌ Error during cleanup: {str(e)}",
            checked=0,
            deactivated=0,
            groups=0
        )


@agent.tool
async def get_user_achievements_display(ctx) -> AchievementsResult:
    """
    Display all unlocked achievements and progress

    Shows:
    - Total achievements unlocked
    - Achievements grouped by category (consistency, milestones, recovery, exploration)
    - Locked achievements preview (what's still available to unlock)
    - Badge tier indicators (bronze, silver, gold, platinum)

    Returns:
        AchievementsResult with formatted achievement display
    """
    deps: AgentDeps = ctx.deps

    try:
        from src.utils.achievement_checker import format_user_achievements_display
        from src.db.queries import get_all_achievements

        # Get formatted display
        formatted_message = await format_user_achievements_display(deps.telegram_id)

        # Get counts
        from src.db.queries import get_user_achievements
        unlocked = await get_user_achievements(deps.telegram_id)
        all_achievements = await get_all_achievements()

        return AchievementsResult(
            success=True,
            message=formatted_message,
            unlocked_count=len(unlocked),
            total_count=len(all_achievements)
        )

    except Exception as e:
        logger.error(f"Error displaying achievements: {e}", exc_info=True)
        return AchievementsResult(
            success=False,
            message=f"Error loading achievements: {str(e)}",
            unlocked_count=0,
            total_count=0
        )


@agent.tool
async def get_daily_food_summary(
    ctx, date: Optional[str] = None
) -> FoodSummaryResult:
    """
    Get summary of food intake for a specific date (calories and macros)

    Args:
        date: Date in "YYYY-MM-DD" format (defaults to today)

    Returns:
        FoodSummaryResult with total calories, macros, and entry count
    """
    deps: AgentDeps = ctx.deps

    try:
        # Get food entries for the specified date (or today)
        entries = await get_food_entries_by_date(
            user_id=deps.telegram_id,
            start_date=date,
            end_date=date
        )

        if not entries:
            return FoodSummaryResult(
                success=True,
                message="No food entries found for this date",
                total_calories=0.0,
                total_protein=0.0,
                total_carbs=0.0,
                total_fat=0.0,
                entry_count=0,
            )

        # Calculate totals from all entries
        total_calories = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0

        for entry in entries:
            total_calories += entry.get("total_calories", 0) or 0

            # Parse macros from JSONB field
            macros = entry.get("total_macros", {})
            if isinstance(macros, str):
                import json
                macros = json.loads(macros)

            total_protein += macros.get("protein", 0) or 0
            total_carbs += macros.get("carbs", 0) or 0
            total_fat += macros.get("fat", 0) or 0

        logger.info(
            f"Food summary for {deps.telegram_id}: {total_calories} cal, {len(entries)} entries"
        )

        return FoodSummaryResult(
            success=True,
            message=f"Found {len(entries)} food entries",
            total_calories=total_calories,
            total_protein=total_protein,
            total_carbs=total_carbs,
            total_fat=total_fat,
            entry_count=len(entries),
        )

    except Exception as e:
        logger.error(f"Failed to get food summary: {e}", exc_info=True)
        return FoodSummaryResult(
            success=False,
            message=f"Failed to retrieve food summary: {str(e)}",
            total_calories=0.0,
            total_protein=0.0,
            total_carbs=0.0,
            total_fat=0.0,
            entry_count=0,
        )


@agent.tool
async def update_food_entry_tool(
    ctx,
    entry_id: str,
    new_total_calories: Optional[int] = None,
    new_protein: Optional[float] = None,
    new_carbs: Optional[float] = None,
    new_fat: Optional[float] = None,
    correction_note: str = None
) -> FoodEntryUpdateResult:
    """
    Update/correct an existing food entry when user provides corrections

    Use this tool when:
    - User says "that's wrong, it should be X"
    - User corrects calorie or macro values
    - User provides more accurate estimates
    - Any time user wants to fix previously logged food data

    CRITICAL: Use this tool to ensure corrections persist after /clear!

    Args:
        entry_id: UUID of the food entry to update (get from get_daily_food_summary)
        new_total_calories: Corrected total calories (optional)
        new_protein: Corrected protein in grams (optional)
        new_carbs: Corrected carbs in grams (optional)
        new_fat: Corrected fat in grams (optional)
        correction_note: Why the correction was made (e.g., "User corrected pizza portion")

    Returns:
        FoodEntryUpdateResult with old/new values
    """
    deps: AgentDeps = ctx.deps

    try:
        # Build macros dict if any macro values provided
        new_macros = None
        if any([new_protein is not None, new_carbs is not None, new_fat is not None]):
            # Get current entry to fill in missing values (use user's timezone for date)
            today = today_user_timezone(deps.telegram_id)
            entries = await get_food_entries_by_date(
                user_id=deps.telegram_id,
                start_date=today.strftime("%Y-%m-%d"),
                end_date=today.strftime("%Y-%m-%d")
            )

            # Find the entry by ID
            current_entry = None
            for entry in entries:
                if str(entry.get("id")) == entry_id:
                    current_entry = entry
                    break

            if current_entry:
                current_macros = current_entry.get("total_macros", {})
                if isinstance(current_macros, str):
                    import json
                    current_macros = json.loads(current_macros)

                new_macros = {
                    "protein": new_protein if new_protein is not None else current_macros.get("protein", 0),
                    "carbs": new_carbs if new_carbs is not None else current_macros.get("carbs", 0),
                    "fat": new_fat if new_fat is not None else current_macros.get("fat", 0),
                }

        # Update the entry
        result = await update_food_entry(
            entry_id=entry_id,
            user_id=deps.telegram_id,
            total_calories=new_total_calories,
            total_macros=new_macros,
            correction_note=correction_note or "User corrected food entry",
            corrected_by="user"
        )

        if result.get("success"):
            old_cal = result["old_values"].get("total_calories", 0)
            new_cal = result["new_values"].get("total_calories", 0)

            logger.info(
                f"Food entry updated: {entry_id} from {old_cal} to {new_cal} kcal"
            )

            return FoodEntryUpdateResult(
                success=True,
                message=f"Updated food entry: {old_cal} → {new_cal} kcal. This correction is now permanent!",
                entry_id=entry_id,
                old_calories=float(old_cal) if old_cal else None,
                new_calories=float(new_cal) if new_cal else None,
                correction_note=correction_note
            )
        else:
            return FoodEntryUpdateResult(
                success=False,
                message=f"Failed to update: {result.get('error', 'Unknown error')}"
            )

    except Exception as e:
        logger.error(f"Failed to update food entry: {e}", exc_info=True)
        return FoodEntryUpdateResult(
            success=False,
            message=f"Error updating food entry: {str(e)}"
        )


@agent.tool
async def remember_fact(
    ctx, fact: str, category: str = "General Information"
) -> RememberFactResult:
    """
    Explicitly remember a fact with verification - GUARANTEED to persist after /clear

    Use this tool when:
    - User explicitly says "remember X"
    - User provides important information that must not be forgotten
    - User corrects you and wants it saved permanently
    - Any critical fact that needs to be 100% reliable

    This tool provides VERIFIED saving - you will know if it succeeded or failed.

    Args:
        fact: The fact to remember (be specific and complete)
        category: Category for organization (e.g., "Food Preferences", "Training Schedule")

    Returns:
        RememberFactResult with success confirmation
    """
    deps: AgentDeps = ctx.deps

    try:
        # Save to patterns file (long-term memory)
        await deps.memory_manager.save_observation(
            deps.telegram_id, category, fact
        )

        # Also save to Mem0 for semantic retrieval
        from src.memory.mem0_manager import mem0_manager
        mem0_manager.add_message(
            deps.telegram_id,
            fact,
            role="user",
            metadata={"type": "explicit_fact", "category": category}
        )

        logger.info(
            f"[REMEMBER_FACT] Saved to patterns.md and Mem0: '{fact}' in category '{category}'"
        )

        return RememberFactResult(
            success=True,
            message=f"✅ Verified: I've permanently saved this fact to your {category}. It will persist even after /clear.",
            fact=fact,
            category=category
        )

    except Exception as e:
        logger.error(f"Failed to remember fact: {e}", exc_info=True)
        return RememberFactResult(
            success=False,
            message=f"❌ Failed to save: {str(e)}. Please try again or report this issue.",
            fact=fact,
            category=category
        )


@agent.tool
async def save_user_info(
    ctx, category: str, information: str
) -> UserInfoResult:
    """
    Save ANY information the user shares to their permanent memory

    Use this tool PROACTIVELY for ALL user information, including:
    - Medical: medications, supplements, injection schedules, conditions, allergies
    - Lifestyle: sleep patterns, stress levels, energy levels, work schedule
    - Training: exercise routines, training days, recovery notes
    - Nutrition: meal timing, eating windows, dietary preferences
    - Goals: motivations, milestones, challenges
    - Observations: mood patterns, behavioral patterns, correlations
    - Life events: injuries, illnesses, life changes, travel
    - ANY other information the user shares

    IMPORTANT: Use this tool IMMEDIATELY when user shares information.
    Don't wait, don't ask permission - just save it!

    Args:
        category: Category name (e.g., "Medications", "Training Schedule", "Health Conditions")
        information: The information to save

    Returns:
        UserInfoResult with success status
    """
    deps: AgentDeps = ctx.deps

    try:
        # Save to patterns file
        await deps.memory_manager.save_observation(
            deps.telegram_id, category, information
        )

        logger.info(f"Saved user info to '{category}' for {deps.telegram_id}")

        return UserInfoResult(
            success=True,
            message=f"I've saved that to your {category} information",
            category=category,
        )

    except Exception as e:
        logger.error(f"Failed to save user info: {e}")
        return UserInfoResult(
            success=False,
            message=f"Failed to save: {str(e)}",
            category=category,
        )


@agent.tool
async def add_new_user(
    ctx, user_id: str
) -> AddUserResult:
    """
    Add a new user to the system (ADMIN ONLY)

    This tool is only available to the admin user (7376426503).
    Creates user directory, initializes files, adds to database, and updates .env

    Args:
        user_id: Telegram user ID to add (e.g., "1234567890")

    Returns:
        AddUserResult with success status
    """
    deps: AgentDeps = ctx.deps

    # Check if caller is admin
    ADMIN_USER_ID = "7376426503"
    if deps.telegram_id != ADMIN_USER_ID:
        logger.warning(f"Non-admin user {deps.telegram_id} attempted to add user")
        return AddUserResult(
            success=False,
            message="❌ Only the admin can add new users",
            user_id=user_id,
        )

    try:
        import os
        from pathlib import Path

        # Validate user_id format
        if not user_id.isdigit():
            return AddUserResult(
                success=False,
                message="❌ Invalid user ID format (must be numeric)",
                user_id=user_id,
            )

        # Check if user already exists
        if await user_exists(user_id):
            return AddUserResult(
                success=False,
                message=f"⚠️ User {user_id} already exists",
                user_id=user_id,
            )

        # 1. Create user in database
        await create_user(user_id)
        logger.info(f"Created user {user_id} in database")

        # 2. Create user files
        await deps.memory_manager.create_user_files(user_id)
        logger.info(f"Created user files for {user_id}")

        # 3. Update .env file with new user ID
        env_path = Path(".env")
        env_content = env_path.read_text()

        # Find ALLOWED_TELEGRAM_IDS line and update it
        lines = env_content.split("\n")
        updated = False
        for i, line in enumerate(lines):
            if line.startswith("ALLOWED_TELEGRAM_IDS="):
                current_ids = line.split("=", 1)[1].strip()
                if current_ids:
                    new_ids = f"{current_ids},{user_id}"
                else:
                    new_ids = user_id
                lines[i] = f"ALLOWED_TELEGRAM_IDS={new_ids}"
                updated = True
                break

        if updated:
            env_path.write_text("\n".join(lines))
            logger.info(f"Updated .env with new user {user_id}")
        else:
            logger.error("Could not find ALLOWED_TELEGRAM_IDS in .env")
            return AddUserResult(
                success=False,
                message=f"⚠️ User created but failed to update .env file",
                user_id=user_id,
            )

        return AddUserResult(
            success=True,
            message=f"✅ User {user_id} added successfully!\n\n"
                    f"📁 Files created in data/{user_id}/\n"
                    f"💾 Added to database\n"
                    f"🔐 Added to authorized users\n\n"
                    f"⚠️ Note: Bot needs restart to recognize new user in .env",
            user_id=user_id,
        )

    except Exception as e:
        logger.error(f"Failed to add user: {e}", exc_info=True)
        return AddUserResult(
            success=False,
            message=f"❌ Failed to add user: {str(e)}",
            user_id=user_id,
        )


@agent.tool
async def generate_invite_code(
    ctx,
    count: int = 1,
    tier: str = 'free',
    trial_days: int = 7,
    max_uses: Optional[int] = 1,
    is_master_code: bool = False,
    description: Optional[str] = None
) -> InviteCodeResult:
    """
    **GENERATE INVITE CODES** - Use this when user says "generate invite code", "create code", "make invite code", or similar (ADMIN ONLY)

    This tool creates invite codes that new users can redeem to activate their accounts.
    Only available to admin user (7376426503).

    Use cases:
    - "generate invite code" → Create 1 code
    - "generate 5 codes" → Create 5 codes
    - "create premium invite code" → Create code with premium tier
    - "create master code for friends" → Create unlimited-use master code

    Args:
        count: Number of codes to generate (default: 1)
        tier: Subscription tier ('free', 'basic', 'premium') (default: 'free')
        trial_days: Number of trial days (0 = no trial, default: 7)
        max_uses: Max uses per code (None = unlimited, default: 1 for single-use)
        is_master_code: If true, creates unlimited-use permanent code (ignores max_uses) (default: False)
        description: Human-readable description for master codes (e.g., "Friends & Family")

    Returns:
        InviteCodeResult with generated code(s)
    """
    deps: AgentDeps = ctx.deps

    # Check if caller is admin
    from src.utils.auth import is_admin
    is_admin_user = is_admin(deps.telegram_id)
    logger.debug(
        f"Invite code generation requested by user {deps.telegram_id} "
        f"(is_admin: {is_admin_user})"
    )

    if not is_admin_user:
        logger.warning(f"Non-admin user {deps.telegram_id} attempted to generate invite codes")
        return InviteCodeResult(
            success=False,
            message="❌ Only the admin can generate invite codes"
        )

    try:
        import random
        import string
        from src.db.queries import create_invite_code

        # Validate inputs
        if count < 1 or count > 100:
            return InviteCodeResult(
                success=False,
                message="❌ Count must be between 1 and 100"
            )

        if tier not in ['free', 'basic', 'premium']:
            return InviteCodeResult(
                success=False,
                message="❌ Tier must be 'free', 'basic', or 'premium'"
            )

        if trial_days < 0:
            return InviteCodeResult(
                success=False,
                message="❌ Trial days must be 0 or positive"
            )

        # Master code handling
        if is_master_code:
            # Force unlimited uses for master codes
            max_uses = None
            # Default description if not provided
            if description is None:
                description = f"Master Code ({tier.title()} tier)"

            logger.info(f"Admin {deps.telegram_id} creating MASTER CODE: {description}")

        # Word list for generating readable codes
        words = [
            'apple', 'beach', 'cloud', 'dance', 'eagle', 'flame', 'grape', 'house',
            'island', 'jungle', 'kite', 'lemon', 'moon', 'night', 'ocean', 'pony',
            'queen', 'river', 'salt', 'tree', 'umbrella', 'valley', 'water', 'yellow',
            'zebra', 'storm', 'pearl', 'tiger', 'frost', 'coral', 'stone', 'wind'
        ]

        # Generate codes with retry logic for collision handling
        codes = []
        max_retries = 10

        for i in range(count):
            code_created = False

            for attempt in range(max_retries):
                # Generate random 3-word code (e.g., "salt-house-pony")
                code = '-'.join(random.choices(words, k=3))

                try:
                    # Create code in database
                    await create_invite_code(
                        code=code,
                        created_by=deps.telegram_id,
                        max_uses=max_uses,
                        tier=tier,
                        trial_days=trial_days,
                        is_master_code=is_master_code,
                        description=description
                    )

                    codes.append(code)
                    if is_master_code:
                        logger.info(f"Admin {deps.telegram_id} generated MASTER CODE: {code}")
                    else:
                        logger.info(f"Admin {deps.telegram_id} generated invite code: {code}")
                    code_created = True
                    break  # Success, exit retry loop

                except Exception as e:
                    error_msg = str(e).lower()
                    # Check for unique constraint violation (collision)
                    if ("unique constraint" in error_msg or "duplicate" in error_msg) and attempt < max_retries - 1:
                        logger.debug(
                            f"Invite code collision detected for '{code}' "
                            f"(attempt {attempt + 1}/{max_retries}), retrying..."
                        )
                        continue  # Retry with new code
                    else:
                        # Other error or max retries reached
                        if attempt == max_retries - 1:
                            logger.error(
                                f"Failed to generate unique invite code after {max_retries} attempts"
                            )
                        raise

            if not code_created:
                raise Exception(f"Failed to generate invite code {i + 1} of {count}")

        # Format response
        if is_master_code:
            # Master code response format
            message = f"""✅ **Master Code Created**

🔑 **Code:** `{codes[0]}`
📝 **Description:** {description}

**Details:**
• Type: **Master Code (Unlimited Uses)**
• Tier: {tier.title()}
• Trial: {trial_days} days
• Expires: Never

⚠️ This code can be reused indefinitely. Share only with trusted friends and family."""
        elif count == 1:
            # Single regular code
            message = f"""✅ **Invite Code Generated**

📝 **Code:** `{codes[0]}`

**Details:**
• Tier: {tier.title()}
• Trial: {trial_days} days
• Max Uses: {'Unlimited' if max_uses is None else max_uses}

Share this code with new users to activate their accounts."""
        else:
            # Multiple regular codes
            codes_list = '\n'.join([f"• `{code}`" for code in codes])
            message = f"""✅ **{count} Invite Codes Generated**

**Codes:**
{codes_list}

**Details:**
• Tier: {tier.title()}
• Trial: {trial_days} days
• Max Uses per code: {'Unlimited' if max_uses is None else max_uses}

Share these codes with new users."""

        return InviteCodeResult(
            success=True,
            message=message,
            code=codes[0] if count == 1 else None
        )

    except Exception as e:
        logger.error(f"Failed to generate invite codes: {e}", exc_info=True)
        return InviteCodeResult(
            success=False,
            message=f"❌ Failed to generate codes: {str(e)}"
        )


@agent.tool
async def remember_visual_pattern(
    ctx, item_name: str, description: str
) -> VisualPatternResult:
    """
    Remember a visual pattern for food/item recognition

    Use this when the user teaches you what something looks like or corrects your identification.
    Examples: "My protein shaker", "My meal prep chicken", "My coffee mug"

    Args:
        item_name: Name of the item (e.g., "My protein shaker", "Chicken breast portion")
        description: Visual and nutritional description (e.g., "Clear bottle with white liquid, 30g protein, 150 cal")

    Returns:
        VisualPatternResult with success status
    """
    deps: AgentDeps = ctx.deps

    try:
        # Save visual pattern to user's memory
        await deps.memory_manager.add_visual_pattern(
            deps.telegram_id, item_name, description
        )

        logger.info(f"Saved visual pattern for {deps.telegram_id}: {item_name}")

        return VisualPatternResult(
            success=True,
            message=f"I'll remember that {item_name}: {description}",
            item_name=item_name,
        )

    except Exception as e:
        logger.error(f"Failed to save visual pattern: {e}")
        return VisualPatternResult(
            success=False,
            message=f"Failed to save: {str(e)}",
            item_name=item_name,
        )


@agent.tool
async def create_dynamic_tool(
    ctx,
    description: str,
    parameter_names: list[str],
    parameter_types: list[str],
    expected_return_type: str
) -> DynamicToolCreationResult:
    """
    Create a new dynamic tool by generating code from description

    This is the self-extension mechanism. When the agent needs a capability
    that doesn't exist, it calls this tool to create it.

    Args:
        description: What the tool should do (e.g., "Get total calories for this week")
        parameter_names: List of parameter names (e.g., ["user_id", "start_date"])
        parameter_types: List of parameter types (e.g., ["str", "Optional[str]"])
        expected_return_type: Return type (e.g., "FoodSummaryResult")

    Returns:
        DynamicToolCreationResult with creation status
    """
    deps: AgentDeps = ctx.deps

    try:
        # Generate tool name from description
        tool_name = re.sub(r'[^a-z0-9_]', '_', description.lower().replace(' ', '_'))
        tool_name = re.sub(r'_+', '_', tool_name)[:50]

        # Check if tool already exists
        existing = await get_tool_by_name(tool_name)
        if existing:
            return DynamicToolCreationResult(
                success=False,
                message=f"Tool '{tool_name}' already exists",
                tool_name=tool_name,
                tool_type="unknown",
                requires_approval=False
            )

        # Generate function code
        function_code = await _generate_tool_code(
            tool_name=tool_name,
            description=description,
            parameter_names=parameter_names,
            parameter_types=parameter_types,
            expected_return_type=expected_return_type
        )

        # Classify tool type
        tool_type = classify_tool_type(function_code, description)

        # Validate code
        is_valid, error_msg = validate_tool_code(function_code, tool_type)
        if not is_valid:
            return DynamicToolCreationResult(
                success=False,
                message=f"Code validation failed: {error_msg}",
                tool_name=tool_name,
                tool_type=tool_type,
                requires_approval=False
            )

        # Build schemas
        parameters_schema = {
            "type": "object",
            "properties": {
                name: {"type": ptype}
                for name, ptype in zip(parameter_names, parameter_types)
            }
        }

        return_schema = {
            "type": "object",
            "properties": {"type": expected_return_type}
        }

        # Save to database
        tool_id = await save_dynamic_tool(
            tool_name=tool_name,
            tool_type=tool_type,
            description=description,
            parameters_schema=parameters_schema,
            return_schema=return_schema,
            function_code=function_code,
            created_by="system"
        )

        # If write tool, require approval
        if tool_type == "write":
            approval_id = await create_tool_approval_request(
                tool_id=tool_id,
                requested_by=deps.telegram_id,
                request_message=f"I want to create a tool: {tool_name}. {description}. This tool will perform WRITE operations."
            )

            # Send notification to admin
            if deps.bot_application:
                try:
                    from src.config import ALLOWED_TELEGRAM_IDS
                    admin_id = ALLOWED_TELEGRAM_IDS[0] if ALLOWED_TELEGRAM_IDS else None

                    if admin_id:
                        notification_text = (
                            f"🔔 **Tool Approval Needed**\n\n"
                            f"**Tool Name:** {tool_name}\n"
                            f"**Type:** Write operation\n"
                            f"**Description:** {description}\n"
                            f"**Requested by:** User {deps.telegram_id}\n\n"
                            f"**Approval ID:** `{approval_id}`\n\n"
                            f"To approve: `/approve_tool {approval_id}`\n"
                            f"To reject: `/reject_tool {approval_id}`"
                        )

                        await deps.bot_application.bot.send_message(
                            chat_id=admin_id,
                            text=notification_text,
                            parse_mode="Markdown"
                        )
                        logger.info(f"Sent approval notification to admin {admin_id}")
                except Exception as e:
                    logger.error(f"Failed to send approval notification: {e}")

            return DynamicToolCreationResult(
                success=True,
                message=f"Tool '{tool_name}' created but requires admin approval before use",
                tool_name=tool_name,
                tool_type=tool_type,
                requires_approval=True,
                approval_id=approval_id
            )

        # Read-only tool - load immediately
        await tool_manager.load_all_tools()  # Reload tools

        return DynamicToolCreationResult(
            success=True,
            message=f"Tool '{tool_name}' created and ready to use",
            tool_name=tool_name,
            tool_type=tool_type,
            requires_approval=False
        )

    except Exception as e:
        logger.error(f"Failed to create dynamic tool: {e}", exc_info=True)
        return DynamicToolCreationResult(
            success=False,
            message=f"Failed to create tool: {str(e)}",
            tool_name=tool_name if 'tool_name' in locals() else "unknown",
            tool_type="unknown",
            requires_approval=False
        )


async def _generate_tool_code(
    tool_name: str,
    description: str,
    parameter_names: list[str],
    parameter_types: list[str],
    expected_return_type: str
) -> str:
    """
    Generate Python function code for a new tool

    For MVP, uses templates. In production, would use LLM to generate code.

    Args:
        tool_name: Name for the function
        description: What it should do
        parameter_names: List of parameter names
        parameter_types: List of parameter types
        expected_return_type: Return type

    Returns:
        Python function code as string
    """
    import re

    # Build parameter list
    params = ", ".join([
        f"{name}: {ptype}"
        for name, ptype in zip(parameter_names, parameter_types)
    ])

    # Template (simplified - in production, use LLM)
    template = f'''async def {tool_name}(ctx, {params}) -> {expected_return_type}:
    """
    {description}

    Auto-generated dynamic tool.
    """
    deps: AgentDeps = ctx.deps

    try:
        # TODO: Implement tool logic
        # This would be generated by LLM based on description

        return {expected_return_type}(
            success=True,
            message="Tool executed successfully"
        )

    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {{e}}")
        return {expected_return_type}(
            success=False,
            message=f"Failed: {{str(e)}}"
        )
'''

    return template


# ============================================
# Gamification Tools
# ============================================

from src.agent.gamification_tools import (
    get_xp_status_tool,
    get_streak_status_tool,
    get_achievement_status_tool,
    get_xp_history_tool,
    get_progress_summary_tool,
    get_daily_dashboard_tool,
    get_weekly_dashboard_tool,
    get_monthly_dashboard_tool,
    get_progress_chart_tool,
    get_motivation_profile_tool,
    browse_challenges_tool,
    start_challenge_tool,
    get_my_challenges_tool,
    XPStatusResult,
    StreakStatusResult,
    AchievementStatusResult,
    XPHistoryResult
)


@agent.tool
async def get_xp_status(ctx: RunContext) -> XPStatusResult:
    """
    **GET XP AND LEVEL STATUS** - Use when user asks about XP, level, or progress

    Shows user's current XP, level, tier (Bronze/Silver/Gold/Platinum),
    and progress toward next level.

    Example queries:
    - "What's my XP?"
    - "What level am I?"
    - "How much XP do I have?"
    - "Show my progress"
    - "Am I close to leveling up?"
    """
    return await get_xp_status_tool(ctx)


@agent.tool
async def get_streaks(ctx: RunContext) -> StreakStatusResult:
    """
    **GET CURRENT STREAKS** - Use when user asks about streaks

    Shows all active streaks (medication, nutrition, exercise, sleep, etc.)
    with current counts and best streaks.

    Example queries:
    - "What are my streaks?"
    - "Show my streaks"
    - "How long is my medication streak?"
    - "Am I on a streak?"
    - "What's my longest streak?"
    """
    return await get_streak_status_tool(ctx)


@agent.tool
async def get_achievements(ctx: RunContext) -> AchievementStatusResult:
    """
    **GET ACHIEVEMENTS** - Use when user asks about achievements or badges

    Shows unlocked achievements and progress toward locked ones.
    Also shows achievements user is close to unlocking.

    Example queries:
    - "What achievements have I unlocked?"
    - "Show my badges"
    - "What achievements can I get?"
    - "Am I close to any achievements?"
    - "Show my achievements"
    """
    return await get_achievement_status_tool(ctx)


@agent.tool
async def get_xp_history(ctx: RunContext) -> XPHistoryResult:
    """
    **GET XP HISTORY** - Use when user asks about recent XP or activity

    Shows recent XP transactions from health activities, streaks, and achievements.

    Example queries:
    - "What XP did I earn today?"
    - "Show my recent XP"
    - "How did I earn XP?"
    - "XP history"
    - "Recent activity"
    """
    return await get_xp_history_tool(ctx)


@agent.tool
async def get_progress_summary(ctx: RunContext) -> str:
    """
    **GET COMPLETE PROGRESS SUMMARY** - Use for comprehensive progress overview

    Shows XP, level, streaks, and achievements in a single summary.
    Best for when user wants a complete overview.

    Example queries:
    - "Show my progress"
    - "How am I doing?"
    - "Summary"
    - "Stats"
    - "My health journey"
    """
    return await get_progress_summary_tool(ctx)


@agent.tool
async def get_daily_dashboard(ctx: RunContext) -> str:
    """
    **GET TODAY'S HEALTH SNAPSHOT** - Use when user asks about today's progress

    Shows today's XP earned, active streaks, recent achievements, and quick stats.
    Perfect for daily check-ins.

    Example queries:
    - "How am I doing today?"
    - "Today's progress"
    - "Daily stats"
    - "Show my day"
    - "What did I do today?"
    """
    return await get_daily_dashboard_tool(ctx)


@agent.tool
async def get_weekly_dashboard(ctx: RunContext) -> str:
    """
    **GET THIS WEEK'S HEALTH OVERVIEW** - Use when user asks about weekly progress

    Shows this week's XP, activities completed, streak changes, achievements
    unlocked, and trends. Great for weekly check-ins.

    Example queries:
    - "Weekly overview"
    - "This week's progress"
    - "How was my week?"
    - "Weekly stats"
    - "Show my week"
    """
    return await get_weekly_dashboard_tool(ctx)


@agent.tool
async def get_monthly_dashboard(ctx: RunContext) -> str:
    """
    **GET COMPREHENSIVE MONTHLY REPORT** - Use when user asks about monthly progress

    Shows month's total XP, level progression, streaks, achievements, trends,
    and insights. Perfect for monthly reviews.

    Example queries:
    - "Monthly report"
    - "This month's stats"
    - "How was my month?"
    - "Monthly summary"
    - "Show my month"
    """
    return await get_monthly_dashboard_tool(ctx)


@agent.tool
async def get_progress_chart(ctx: RunContext) -> str:
    """
    **GET VISUAL PROGRESS CHART** - Use when user wants to visualize progress over time

    Displays a text-based chart showing XP earned over the last 30 days.
    Great for visualizing trends and consistency.

    Example queries:
    - "Show my progress chart"
    - "XP trend"
    - "Progress over time"
    - "Visualize my progress"
    - "How have I been doing?"
    """
    return await get_progress_chart_tool(ctx)


@agent.tool
async def get_motivation_profile(ctx: RunContext) -> str:
    """
    **GET MOTIVATION PROFILE** - Use when user asks about their motivation type or personalization

    Shows user's detected motivation profile (Achiever, Socializer, Explorer, Completionist)
    and explains how the system adapts messaging for them.

    Example queries:
    - "What's my motivation profile?"
    - "What motivates me?"
    - "Why am I getting these messages?"
    - "My personality type"
    - "How does personalization work?"
    """
    return await get_motivation_profile_tool(ctx)


@agent.tool
async def browse_challenges(ctx: RunContext, difficulty: Optional[str] = None) -> str:
    """
    **BROWSE CHALLENGES** - Use when user wants to see available challenges

    Shows all health challenges from the library, optionally filtered by difficulty.

    Example queries:
    - "What challenges are available?"
    - "Show me challenges"
    - "What can I do?"
    - "Easy challenges"
    - "Show hard challenges"
    """
    return await browse_challenges_tool(ctx, difficulty)


@agent.tool
async def start_challenge(ctx: RunContext, challenge_name: str) -> str:
    """
    **START CHALLENGE** - Use when user wants to begin a challenge

    Starts a specific challenge for the user.

    Args:
        challenge_name: Name of the challenge to start

    Example queries:
    - "Start Week Warrior"
    - "Begin the medication master challenge"
    - "I want to do the XP accumulator"
    """
    return await start_challenge_tool(ctx, challenge_name)


@agent.tool
async def get_my_challenges(ctx: RunContext) -> str:
    """
    **GET MY CHALLENGES** - Use when user asks about their challenge progress

    Shows user's active and completed challenges with progress tracking.

    Example queries:
    - "My challenges"
    - "What challenges am I doing?"
    - "Show my progress"
    - "Challenge status"
    - "How am I doing on challenges?"
    """
    return await get_my_challenges_tool(ctx)


async def get_agent_response(
    telegram_id: str,
    user_message: str,
    memory_manager: MemoryFileManager,
    reminder_manager=None,
    message_history: list = None,
    bot_application=None,
) -> str:
    """
    Get agent response with dynamic system prompt and tools
    Automatically falls back to OpenAI if Claude is overloaded

    Args:
        telegram_id: User's Telegram ID
        user_message: User's message
        memory_manager: Memory file manager instance
        reminder_manager: Reminder manager instance
        message_history: List of previous messages for context
        bot_application: Telegram bot application for notifications

    Returns:
        Agent's response string
    """
    # Load user memory from markdown files
    user_memory = await memory_manager.load_user_memory(telegram_id)

    # Check if we can extract a direct answer from patterns.md
    from src.memory.answer_extractor import extract_direct_answer
    patterns_content = user_memory.get("patterns", "")
    direct_answer = extract_direct_answer(user_message, patterns_content)

    # Add current timestamp to EVERY message so Claude always knows the time
    from datetime import datetime
    import pytz
    import re

    # Get user's timezone from profile
    profile_text = user_memory.get("profile", "")
    timezone_match = re.search(r'Timezone:\s*([^\n]+)', profile_text)
    user_timezone_str = timezone_match.group(1).strip() if timezone_match else "Europe/Stockholm"

    try:
        user_tz = pytz.timezone(user_timezone_str)
    except:
        user_tz = pytz.timezone('Europe/Stockholm')

    # Get current time in user's timezone
    user_now = datetime.now(user_tz)
    timestamp_info = f"[Current time: {user_now.strftime('%Y-%m-%d %H:%M')} {user_timezone_str}, {user_now.strftime('%A')}]"

    # If we found a direct answer, inject it into the user's message
    enhanced_message = f"{timestamp_info}\n\n{user_message}"
    if direct_answer:
        enhanced_message = f"{timestamp_info}\n\n{user_message}\n\n{direct_answer}"
        logger.info(f"[DIRECT_ANSWER] Injected answer into query")

    # Generate dynamic system prompt with Mem0 semantic search
    system_prompt = generate_system_prompt(user_memory, user_id=telegram_id, current_query=enhanced_message)

    # Create dependencies
    deps = AgentDeps(
        telegram_id=telegram_id,
        memory_manager=memory_manager,
        user_memory=user_memory,
        reminder_manager=reminder_manager,
        bot_application=bot_application,
    )

    # Convert message_history from dicts to ModelMessage objects
    converted_history = []
    if message_history:
        for msg in message_history:
            if msg.get("role") == "user":
                converted_history.append(ModelRequest.user_text_prompt(msg["content"]))
            elif msg.get("role") == "assistant":
                converted_history.append(
                    ModelResponse(
                        parts=[TextPart(content=msg["content"])],
                        model_name="assistant"
                    )
                )

    # Try with primary model (Claude) first
    try:
        logger.info(f"Attempting with primary model: {AGENT_MODEL}")
        logger.info(f"[SYSTEM_PROMPT_DEBUG] Length: {len(system_prompt)} chars")
        logger.info(f"[SYSTEM_PROMPT_DEBUG] Contains 'Training Schedule': {'Training Schedule' in system_prompt}")
        logger.info(f"[SYSTEM_PROMPT_DEBUG] Contains 'Monday, Tuesday': {'Monday, Tuesday' in system_prompt}")

        dynamic_agent = Agent(
            model=AGENT_MODEL,
            system_prompt=system_prompt,
            deps_type=AgentDeps,
        )

        # Register tools on the dynamic agent
        dynamic_agent.tool(update_profile)
        dynamic_agent.tool(save_preference)
        dynamic_agent.tool(save_user_info)
        dynamic_agent.tool(add_new_user)
        dynamic_agent.tool(generate_invite_code)
        dynamic_agent.tool(create_new_tracking_category)
        dynamic_agent.tool(log_tracking_entry)
        dynamic_agent.tool(schedule_reminder)
        dynamic_agent.tool(get_user_reminders)
        dynamic_agent.tool(get_reminder_statistics)
        dynamic_agent.tool(compare_all_reminders)
        dynamic_agent.tool(suggest_reminder_optimizations)
        dynamic_agent.tool(delete_reminder)
        dynamic_agent.tool(update_reminder)
        dynamic_agent.tool(cleanup_duplicate_reminders)
        dynamic_agent.tool(get_user_achievements_display)
        dynamic_agent.tool(get_daily_food_summary)
        dynamic_agent.tool(remember_visual_pattern)
        dynamic_agent.tool(create_dynamic_tool)
        # Gamification tools
        dynamic_agent.tool(get_xp_status)
        dynamic_agent.tool(get_streaks)
        dynamic_agent.tool(get_achievements)
        dynamic_agent.tool(get_xp_history)
        dynamic_agent.tool(get_progress_summary)
        # Dashboard tools
        dynamic_agent.tool(get_daily_dashboard)
        dynamic_agent.tool(get_weekly_dashboard)
        dynamic_agent.tool(get_monthly_dashboard)
        dynamic_agent.tool(get_progress_chart)
        # Motivation profile
        dynamic_agent.tool(get_motivation_profile)
        # Challenges
        dynamic_agent.tool(browse_challenges)
        dynamic_agent.tool(start_challenge)
        dynamic_agent.tool(get_my_challenges)

        # Register dynamically loaded tools
        tool_manager.register_tools_on_agent(dynamic_agent)

        # Run agent with message history for context (converted to ModelMessage objects)
        result = await dynamic_agent.run(
            enhanced_message, deps=deps, message_history=converted_history
        )

        return result.output

    except Exception as primary_error:
        # Check if it's an API overload/availability error
        error_str = str(primary_error).lower()
        if any(keyword in error_str for keyword in ['overload', '529', '503', 'rate_limit', 'unavailable']):
            logger.warning(f"Primary model ({AGENT_MODEL}) unavailable: {primary_error}")
            logger.info("Falling back to OpenAI GPT-4o...")

            try:
                # Fallback to OpenAI GPT-4o
                fallback_agent = Agent(
                    model="openai:gpt-4o",
                    system_prompt=system_prompt,
                    deps_type=AgentDeps,
                )

                # Register tools on fallback agent
                fallback_agent.tool(update_profile)
                fallback_agent.tool(save_preference)
                fallback_agent.tool(save_user_info)
                fallback_agent.tool(add_new_user)
                fallback_agent.tool(generate_invite_code)
                fallback_agent.tool(create_new_tracking_category)
                fallback_agent.tool(log_tracking_entry)
                fallback_agent.tool(schedule_reminder)
                fallback_agent.tool(get_user_reminders)
                fallback_agent.tool(get_reminder_statistics)
                fallback_agent.tool(compare_all_reminders)
                fallback_agent.tool(suggest_reminder_optimizations)
                fallback_agent.tool(delete_reminder)
                fallback_agent.tool(update_reminder)
                fallback_agent.tool(cleanup_duplicate_reminders)
                fallback_agent.tool(get_user_achievements_display)
                fallback_agent.tool(get_daily_food_summary)
                fallback_agent.tool(remember_visual_pattern)
                fallback_agent.tool(create_dynamic_tool)
                # Gamification tools
                fallback_agent.tool(get_xp_status)
                fallback_agent.tool(get_streaks)
                fallback_agent.tool(get_achievements)
                fallback_agent.tool(get_xp_history)
                fallback_agent.tool(get_progress_summary)
                # Dashboard tools
                fallback_agent.tool(get_daily_dashboard)
                fallback_agent.tool(get_weekly_dashboard)
                fallback_agent.tool(get_monthly_dashboard)
                fallback_agent.tool(get_progress_chart)
                # Motivation profile
                fallback_agent.tool(get_motivation_profile)
                # Challenges
                fallback_agent.tool(browse_challenges)
                fallback_agent.tool(start_challenge)
                fallback_agent.tool(get_my_challenges)

                # Register dynamically loaded tools
                tool_manager.register_tools_on_agent(fallback_agent)

                # Run with fallback model (converted history)
                result = await fallback_agent.run(
                    enhanced_message, deps=deps, message_history=converted_history
                )

                logger.info("✅ Fallback to OpenAI successful")
                return result.output

            except Exception as fallback_error:
                logger.error(f"Fallback model also failed: {fallback_error}", exc_info=True)
                return f"Sorry, both AI services are currently unavailable. Please try again in a moment."
        else:
            # Not an availability error, return the original error
            logger.error(f"Agent error (not availability issue): {primary_error}", exc_info=True)
            return f"Sorry, I encountered an error: {str(primary_error)}"
