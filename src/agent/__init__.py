"""PydanticAI agent for adaptive health coaching"""
import logging
import re
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4
from datetime import datetime

from pydantic_ai import Agent, ModelMessagesTypeAdapter
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
    save_dynamic_tool,
    get_tool_by_name,
    create_tool_approval_request,
)
from src.memory.file_manager import MemoryFileManager
from src.memory.system_prompt import generate_system_prompt
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


class FoodSummaryResult(BaseModel):
    """Result of food summary query"""

    success: bool
    message: str
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    entry_count: int


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


async def get_agent_response(
    telegram_id: str,
    user_message: str,
    memory_manager: MemoryFileManager,
    reminder_manager=None,
    message_history: list = None,
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

    Returns:
        Agent's response string
    """
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
        dynamic_agent.tool(get_daily_food_summary)
        dynamic_agent.tool(create_dynamic_tool)

        # Register dynamically loaded tools
        tool_manager.register_tools_on_agent(dynamic_agent)

        # Run agent with message history for context (converted to ModelMessage objects)
        result = await dynamic_agent.run(
            user_message, deps=deps, message_history=converted_history
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
                fallback_agent.tool(create_new_tracking_category)
                fallback_agent.tool(log_tracking_entry)
                fallback_agent.tool(schedule_reminder)
                fallback_agent.tool(get_daily_food_summary)
                fallback_agent.tool(create_dynamic_tool)

                # Register dynamically loaded tools
                tool_manager.register_tools_on_agent(fallback_agent)

                # Run with fallback model (converted history)
                result = await fallback_agent.run(
                    user_message, deps=deps, message_history=converted_history
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
