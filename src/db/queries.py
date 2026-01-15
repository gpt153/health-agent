"""Database queries"""
import json
import logging
from typing import Optional
from uuid import UUID
from datetime import datetime
from src.db.connection import db
from src.models.user import UserProfile
from src.models.food import FoodEntry
from src.models.tracking import TrackingCategory, TrackingEntry
from src.models.reminder import Reminder
from src.models.sleep import SleepEntry
from src.models.sleep_settings import SleepQuizSettings, SleepQuizSubmission

logger = logging.getLogger(__name__)


# User operations
async def create_user(telegram_id: str) -> None:
    """Create new user in database"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO users (telegram_id) VALUES (%s) ON CONFLICT (telegram_id) DO NOTHING",
                (telegram_id,)
            )
            await conn.commit()
    logger.info(f"Created user: {telegram_id}")


async def user_exists(telegram_id: str) -> bool:
    """Check if user exists"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM users WHERE telegram_id = %s",
                (telegram_id,)
            )
            return await cur.fetchone() is not None


# Food entry operations
async def save_food_entry(entry: FoodEntry) -> None:
    """Save food entry to database"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO food_entries
                (user_id, timestamp, photo_path, foods, total_calories, total_macros, meal_type, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    entry.user_id,
                    entry.timestamp,
                    entry.photo_path,
                    json.dumps([f.model_dump() for f in entry.foods]),
                    entry.total_calories,
                    json.dumps(entry.total_macros.model_dump()),
                    entry.meal_type,
                    entry.notes
                )
            )
            await conn.commit()
    logger.info(f"Saved food entry for user {entry.user_id}")


async def update_food_entry(
    entry_id: str,
    user_id: str,
    total_calories: Optional[int] = None,
    total_macros: Optional[dict] = None,
    foods: Optional[list] = None,
    correction_note: Optional[str] = None,
    corrected_by: str = "user"
) -> dict:
    """
    Update an existing food entry with corrections

    Args:
        entry_id: UUID of the food entry to update
        user_id: Telegram user ID (for verification)
        total_calories: New total calories (optional)
        total_macros: New macros dict {protein, carbs, fat} (optional)
        foods: New foods list (optional)
        correction_note: Reason for correction
        corrected_by: 'user' or 'auto'

    Returns:
        dict with old_values, new_values, and success status
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # First, get the current entry to verify ownership and for audit
            await cur.execute(
                """
                SELECT id, user_id, total_calories, total_macros, foods
                FROM food_entries
                WHERE id = %s AND user_id = %s
                """,
                (entry_id, user_id)
            )
            current_entry = await cur.fetchone()

            if not current_entry:
                logger.warning(f"Food entry {entry_id} not found for user {user_id}")
                return {
                    "success": False,
                    "error": "Food entry not found or does not belong to user"
                }

            # Store old values for audit
            old_values = {
                "total_calories": current_entry["total_calories"],
                "total_macros": current_entry["total_macros"],
                "foods": current_entry["foods"]
            }

            # Prepare new values (use old values if not provided)
            new_calories = total_calories if total_calories is not None else current_entry["total_calories"]
            new_macros = total_macros if total_macros is not None else current_entry["total_macros"]
            new_foods = foods if foods is not None else current_entry["foods"]

            # Update the entry
            await cur.execute(
                """
                UPDATE food_entries
                SET total_calories = %s,
                    total_macros = %s,
                    foods = %s,
                    correction_note = %s,
                    corrected_by = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
                """,
                (
                    new_calories,
                    json.dumps(new_macros) if isinstance(new_macros, dict) else new_macros,
                    json.dumps(new_foods) if isinstance(new_foods, list) else new_foods,
                    correction_note,
                    corrected_by,
                    entry_id,
                    user_id
                )
            )

            # Log to audit table
            await cur.execute(
                """
                INSERT INTO food_entry_audit
                (food_entry_id, user_id, action, old_values, new_values, correction_note)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    entry_id,
                    user_id,
                    "updated",
                    json.dumps(old_values),
                    json.dumps({
                        "total_calories": new_calories,
                        "total_macros": new_macros,
                        "foods": new_foods
                    }),
                    correction_note
                )
            )

            await conn.commit()

            logger.info(
                f"Updated food entry {entry_id} for user {user_id}: "
                f"{old_values['total_calories']} -> {new_calories} kcal"
            )

            return {
                "success": True,
                "entry_id": str(entry_id),
                "old_values": old_values,
                "new_values": {
                    "total_calories": new_calories,
                    "total_macros": new_macros,
                    "foods": new_foods
                },
                "correction_note": correction_note
            }


async def get_recent_food_entries(user_id: str, limit: int = 10) -> list[dict]:
    """Get recent food entries for user"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT * FROM food_entries
                WHERE user_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (user_id, limit)
            )
            return await cur.fetchall()


# Tracking category operations
async def create_tracking_category(category: TrackingCategory) -> None:
    """Create new tracking category"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO tracking_categories (id, user_id, name, fields, schedule, active)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    category.id,
                    category.user_id,
                    category.name,
                    json.dumps({k: v.model_dump() for k, v in category.fields.items()}),
                    json.dumps(category.schedule.model_dump()) if category.schedule else None,
                    category.active
                )
            )
            await conn.commit()
    logger.info(f"Created tracking category: {category.name} for user {category.user_id}")


async def get_tracking_categories(user_id: str, active_only: bool = True) -> list[dict]:
    """Get tracking categories for user"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            query = "SELECT * FROM tracking_categories WHERE user_id = %s"
            if active_only:
                query += " AND active = true"
            await cur.execute(query, (user_id,))
            return await cur.fetchall()


async def save_tracking_entry(entry: TrackingEntry) -> None:
    """Save tracking entry"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO tracking_entries (id, user_id, category_id, timestamp, data, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    entry.id,
                    entry.user_id,
                    entry.category_id,
                    entry.timestamp,
                    json.dumps(entry.data),
                    entry.notes
                )
            )
            await conn.commit()
    logger.info(f"Saved tracking entry for user {entry.user_id}")


# Reminder operations
async def create_reminder(reminder: Reminder) -> None:
    """Create new reminder"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO reminders (id, user_id, reminder_type, message, schedule, active)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    reminder.id,
                    reminder.user_id,
                    reminder.reminder_type,
                    reminder.message,
                    json.dumps(reminder.schedule.model_dump()),
                    reminder.active
                )
            )
            await conn.commit()
    logger.info(f"Created reminder for user {reminder.user_id}")


async def get_active_reminders(user_id: str) -> list[dict]:
    """Get active reminders for user"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM reminders WHERE user_id = %s AND active = true",
                (user_id,)
            )
            return await cur.fetchall()


async def get_active_reminders_all() -> list[dict]:
    """Get all active reminders for all users"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM reminders WHERE active = true ORDER BY user_id"
            )
            return await cur.fetchall()


async def find_duplicate_reminders(user_id: Optional[str] = None) -> list[dict]:
    """
    Find duplicate reminders (same user, message, time, timezone)

    Args:
        user_id: Optional user filter, or None for all users

    Returns:
        List of dicts with duplicate info and reminder IDs to keep/remove
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            query = """
            WITH reminder_groups AS (
                SELECT
                    user_id,
                    message,
                    schedule->>'time' as time,
                    schedule->>'timezone' as timezone,
                    ARRAY_AGG(id ORDER BY created_at ASC) as reminder_ids,
                    ARRAY_AGG(created_at ORDER BY created_at ASC) as created_dates,
                    COUNT(*) as count
                FROM reminders
                WHERE active = true
            """

            if user_id:
                query += " AND user_id = %s"
                params = (user_id,)
            else:
                params = ()

            query += """
                GROUP BY user_id, message, schedule->>'time', schedule->>'timezone'
                HAVING COUNT(*) > 1
            )
            SELECT
                user_id,
                message,
                time,
                timezone,
                reminder_ids[1] as keep_id,
                reminder_ids[2:] as remove_ids,
                count as duplicate_count
            FROM reminder_groups
            ORDER BY user_id, count DESC
            """

            await cur.execute(query, params)
            return await cur.fetchall()


async def deactivate_duplicate_reminders(user_id: Optional[str] = None) -> dict:
    """
    Deactivate duplicate reminders, keeping the oldest one

    Args:
        user_id: Optional user filter, or None for all users

    Returns:
        Dict with counts of reminders checked and deactivated
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Find duplicates
            duplicates = await find_duplicate_reminders(user_id)

            if not duplicates:
                return {"checked": 0, "deactivated": 0, "groups": 0}

            # Deactivate all duplicates (except the one to keep)
            deactivated_count = 0
            for dup in duplicates:
                remove_ids = dup["remove_ids"]
                if remove_ids:
                    # Convert list to tuple for SQL IN clause
                    await cur.execute(
                        """
                        UPDATE reminders
                        SET active = false
                        WHERE id = ANY(%s)
                        """,
                        (remove_ids,)
                    )
                    deactivated_count += len(remove_ids)

            await conn.commit()

            logger.info(
                f"Deactivated {deactivated_count} duplicate reminders "
                f"across {len(duplicates)} groups"
            )

            return {
                "checked": sum(d["duplicate_count"] for d in duplicates),
                "deactivated": deactivated_count,
                "groups": len(duplicates)
            }


async def delete_reminder(reminder_id: str, user_id: str) -> bool:
    """
    Delete (deactivate) a reminder

    Args:
        reminder_id: UUID of reminder
        user_id: User ID for security check

    Returns:
        True if deleted, False if not found or unauthorized
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE reminders
                SET active = false
                WHERE id = %s AND user_id = %s AND active = true
                RETURNING id
                """,
                (reminder_id, user_id)
            )
            result = await cur.fetchone()
            await conn.commit()

            if result:
                logger.info(f"Deleted reminder {reminder_id} for user {user_id}")
                return True
            else:
                logger.warning(f"Reminder {reminder_id} not found for user {user_id}")
                return False


async def update_reminder(
    reminder_id: str,
    user_id: str,
    new_time: Optional[str] = None,
    new_message: Optional[str] = None,
    new_timezone: Optional[str] = None,
    new_days: Optional[list[int]] = None
) -> Optional[dict]:
    """
    Update a reminder's properties

    Args:
        reminder_id: UUID of reminder
        user_id: User ID for security check
        new_time: New time in "HH:MM" format (optional)
        new_message: New message text (optional)
        new_timezone: New timezone (optional)
        new_days: New days list (optional)

    Returns:
        Updated reminder dict or None if not found
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Get current reminder
            await cur.execute(
                """
                SELECT id, message, schedule
                FROM reminders
                WHERE id = %s AND user_id = %s AND active = true
                """,
                (reminder_id, user_id)
            )
            current = await cur.fetchone()

            if not current:
                return None

            # Parse current schedule
            current_schedule = current["schedule"]
            if isinstance(current_schedule, str):
                current_schedule = json.loads(current_schedule)

            # Build updated values
            updated_message = new_message if new_message is not None else current["message"]
            updated_schedule = current_schedule.copy()

            if new_time is not None:
                updated_schedule["time"] = new_time
            if new_timezone is not None:
                updated_schedule["timezone"] = new_timezone
            if new_days is not None:
                updated_schedule["days"] = new_days

            # Update database
            await cur.execute(
                """
                UPDATE reminders
                SET message = %s, schedule = %s
                WHERE id = %s AND user_id = %s
                RETURNING id, message, schedule
                """,
                (updated_message, json.dumps(updated_schedule), reminder_id, user_id)
            )
            result = await cur.fetchone()
            await conn.commit()

            if result:
                logger.info(f"Updated reminder {reminder_id} for user {user_id}")
                return result

            return None


# ==========================================
# Conversation History Functions
# ==========================================

async def save_conversation_message(
    user_id: str,
    role: str,
    content: str,
    message_type: str = "text",
    metadata: dict = None
) -> None:
    """
    Save a message to conversation history
    
    Args:
        user_id: Telegram user ID
        role: 'user' or 'assistant'
        content: Message content
        message_type: 'text', 'photo', 'reminder', 'voice', etc.
        metadata: Additional context (photo analysis, etc.)
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO conversation_history (user_id, role, content, message_type, metadata)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, role, content, message_type, json.dumps(metadata or {}))
            )
            await conn.commit()


async def get_conversation_history(
    user_id: str,
    limit: int = 20
) -> list[dict]:
    """
    Get recent conversation history for a user
    
    Args:
        user_id: Telegram user ID
        limit: Maximum number of messages to retrieve (default: 20 = 10 turns)
        
    Returns:
        List of messages in format: [{"role": "user", "content": "..."}]
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT role, content, message_type, metadata, timestamp
                FROM conversation_history
                WHERE user_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (user_id, limit)
            )
            rows = await cur.fetchall()
    
    # Reverse to get chronological order (oldest first)
    # Filter out unhelpful "I don't know" responses to keep history clean
    unhelpful_phrases = [
        "jag har ingen information",
        "i don't have that information",
        "jag vet inte",
        "i don't know",
        "jag har inte",
        "jag kan inte svara",
        "i can't answer",
        "jag vet fortfarande inte"
    ]

    messages = []
    for row in reversed(rows):
        content = row["content"].lower()

        # Skip assistant messages that are unhelpful "I don't know" responses
        if row["role"] == "assistant" and any(phrase in content for phrase in unhelpful_phrases):
            continue

        messages.append({
            "role": row["role"],
            "content": row["content"]
        })

    return messages


async def clear_conversation_history(user_id: str) -> None:
    """Clear all conversation history for a user"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM conversation_history WHERE user_id = %s",
                (user_id,)
            )
            await conn.commit()


# ==========================================
# Food Entry Retrieval Functions
# ==========================================

async def get_food_entries_by_date(
    user_id: str,
    start_date: str = None,
    end_date: str = None
) -> list[dict]:
    """
    Get food entries for a user within a date range
    
    Args:
        user_id: Telegram user ID
        start_date: Start date (YYYY-MM-DD format, defaults to today)
        end_date: End date (YYYY-MM-DD format, defaults to today)
        
    Returns:
        List of food entries with timestamp, foods, calories, macros
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            if not start_date:
                # Default to today
                await cur.execute(
                    """
                    SELECT id, timestamp, foods, total_calories, total_macros, meal_type, notes
                    FROM food_entries
                    WHERE user_id = %s AND DATE(timestamp) = CURRENT_DATE
                    ORDER BY timestamp DESC
                    """,
                    (user_id,)
                )
            else:
                await cur.execute(
                    """
                    SELECT id, timestamp, foods, total_calories, total_macros, meal_type, notes
                    FROM food_entries
                    WHERE user_id = %s 
                      AND DATE(timestamp) >= %s::date
                      AND DATE(timestamp) <= %s::date
                    ORDER BY timestamp DESC
                    """,
                    (user_id, start_date, end_date or start_date)
                )
            
            rows = await cur.fetchall()
            return [dict(row) for row in rows]


async def has_logged_food_in_window(
    user_id: str,
    window_hours: int,
    meal_type: Optional[str] = None
) -> bool:
    """
    Check if user has logged food within the specified time window

    Args:
        user_id: Telegram user ID
        window_hours: How many hours back to check (e.g., 2 means "logged food in last 2 hours")
        meal_type: Optional meal type filter (e.g., "lunch", "breakfast")

    Returns:
        True if food was logged within the time window, False otherwise
    """
    from datetime import timedelta
    from src.utils.datetime_helpers import now_utc

    cutoff_time = now_utc() - timedelta(hours=window_hours)

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            if meal_type:
                # Check for specific meal type
                await cur.execute(
                    """
                    SELECT COUNT(*) FROM food_entries
                    WHERE user_id = %s AND timestamp >= %s AND meal_type = %s
                    """,
                    (user_id, cutoff_time, meal_type)
                )
            else:
                # Check for any food log
                await cur.execute(
                    """
                    SELECT COUNT(*) FROM food_entries
                    WHERE user_id = %s AND timestamp >= %s
                    """,
                    (user_id, cutoff_time)
                )

            row = await cur.fetchone()
            count = row[0] if row else 0
            return count > 0


# ==========================================
# Dynamic Tools Functions
# ==========================================

async def save_dynamic_tool(
    tool_name: str,
    tool_type: str,
    description: str,
    parameters_schema: dict,
    return_schema: dict,
    function_code: str,
    created_by: str = "system"
) -> str:
    """
    Save a new dynamic tool to database

    Args:
        tool_name: Unique tool name (e.g., 'get_weekly_calories')
        tool_type: 'read' or 'write'
        description: Human-readable description
        parameters_schema: JSON Schema for function parameters
        return_schema: JSON Schema for return type
        function_code: Python function code as string
        created_by: Creator ID (default: 'system')

    Returns:
        Tool UUID as string
    """
    from uuid import uuid4
    tool_id = str(uuid4())

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO dynamic_tools
                (id, tool_name, tool_type, description, parameters_schema,
                 return_schema, function_code, enabled, version, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    tool_id,
                    tool_name,
                    tool_type,
                    description,
                    json.dumps(parameters_schema),
                    json.dumps(return_schema),
                    function_code,
                    True,  # enabled
                    1,     # version
                    created_by
                )
            )

            # Save initial version to history
            await cur.execute(
                """
                INSERT INTO dynamic_tool_versions
                (tool_id, version, function_code, change_summary)
                VALUES (%s, %s, %s, %s)
                """,
                (tool_id, 1, function_code, "Initial creation")
            )

            await conn.commit()

    logger.info(f"Saved dynamic tool: {tool_name} (type: {tool_type}, id: {tool_id})")
    return tool_id


async def get_all_enabled_tools() -> list[dict]:
    """Get all enabled dynamic tools"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, tool_name, tool_type, description,
                       parameters_schema, return_schema, function_code,
                       version, created_at, last_used_at, usage_count
                FROM dynamic_tools
                WHERE enabled = true
                ORDER BY tool_name
                """
            )
            return await cur.fetchall()


async def get_tool_by_name(tool_name: str) -> Optional[dict]:
    """Get specific tool by name"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT * FROM dynamic_tools
                WHERE tool_name = %s
                """,
                (tool_name,)
            )
            return await cur.fetchone()


async def update_tool_version(
    tool_id: str,
    new_function_code: str,
    change_summary: str
) -> int:
    """
    Update tool code and increment version

    Returns:
        New version number
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Get current version
            await cur.execute(
                "SELECT version FROM dynamic_tools WHERE id = %s",
                (tool_id,)
            )
            row = await cur.fetchone()
            if not row:
                raise ValueError(f"Tool {tool_id} not found")

            new_version = row["version"] + 1

            # Update tool
            await cur.execute(
                """
                UPDATE dynamic_tools
                SET function_code = %s, version = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (new_function_code, new_version, tool_id)
            )

            # Save version history
            await cur.execute(
                """
                INSERT INTO dynamic_tool_versions
                (tool_id, version, function_code, change_summary)
                VALUES (%s, %s, %s, %s)
                """,
                (tool_id, new_version, new_function_code, change_summary)
            )

            await conn.commit()

    logger.info(f"Updated tool {tool_id} to version {new_version}")
    return new_version


async def disable_tool(tool_id: str) -> None:
    """Disable a tool (soft delete)"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE dynamic_tools SET enabled = false WHERE id = %s",
                (tool_id,)
            )
            await conn.commit()
    logger.info(f"Disabled tool {tool_id}")


async def enable_tool(tool_id: str) -> None:
    """Re-enable a disabled tool"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE dynamic_tools SET enabled = true WHERE id = %s",
                (tool_id,)
            )
            await conn.commit()
    logger.info(f"Enabled tool {tool_id}")


async def log_tool_execution(
    tool_id: str,
    user_id: str,
    parameters: dict,
    result: any,
    success: bool,
    error_message: Optional[str] = None,
    execution_time_ms: int = 0
) -> None:
    """Log tool execution for audit trail"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Log execution
            await cur.execute(
                """
                INSERT INTO dynamic_tool_executions
                (tool_id, user_id, parameters, result, success,
                 error_message, execution_time_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    tool_id,
                    user_id,
                    json.dumps(parameters),
                    json.dumps(result) if success else None,
                    success,
                    error_message,
                    execution_time_ms
                )
            )

            # Update tool usage stats
            if success:
                await cur.execute(
                    """
                    UPDATE dynamic_tools
                    SET usage_count = usage_count + 1,
                        last_used_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (tool_id,)
                )
            else:
                await cur.execute(
                    """
                    UPDATE dynamic_tools
                    SET error_count = error_count + 1
                    WHERE id = %s
                    """,
                    (tool_id,)
                )

            await conn.commit()


async def create_tool_approval_request(
    tool_id: str,
    requested_by: str,
    request_message: str
) -> str:
    """Create approval request for write tool"""
    from uuid import uuid4
    approval_id = str(uuid4())

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO dynamic_tool_approvals
                (id, tool_id, requested_by, request_message, status)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (approval_id, tool_id, requested_by, request_message, "pending")
            )
            await conn.commit()

    logger.info(f"Created approval request {approval_id} for tool {tool_id}")
    return approval_id


async def approve_tool(
    approval_id: str,
    admin_user_id: str
) -> None:
    """Approve a pending tool creation"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE dynamic_tool_approvals
                SET status = 'approved',
                    admin_user_id = %s,
                    admin_response_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (admin_user_id, approval_id)
            )
            await conn.commit()
    logger.info(f"Approved tool creation request {approval_id}")


async def reject_tool(
    approval_id: str,
    admin_user_id: str
) -> None:
    """Reject a pending tool creation"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE dynamic_tool_approvals
                SET status = 'rejected',
                    admin_user_id = %s,
                    admin_response_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (admin_user_id, approval_id)
            )
            await conn.commit()
    logger.info(f"Rejected tool creation request {approval_id}")


async def get_pending_approvals() -> list[dict]:
    """Get all pending tool approval requests"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT
                    a.id as approval_id,
                    a.tool_id,
                    a.requested_by,
                    a.request_message,
                    a.created_at,
                    t.tool_name,
                    t.tool_type,
                    t.description
                FROM dynamic_tool_approvals a
                JOIN dynamic_tools t ON a.tool_id = t.id
                WHERE a.status = 'pending'
                ORDER BY a.created_at DESC
                """
            )
            return await cur.fetchall()


# Invite code operations
async def create_invite_code(
    code: str,
    created_by: str,
    max_uses: Optional[int] = None,
    tier: str = 'free',
    trial_days: int = 0,
    expires_at: Optional[datetime] = None,
    is_master_code: bool = False,
    description: Optional[str] = None
) -> str:
    """Create a new invite code (supports master codes with unlimited uses)"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO invite_codes (code, created_by, max_uses, tier, trial_days, expires_at, is_master_code, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (code, created_by, max_uses, tier, trial_days, expires_at, is_master_code, description)
            )
            result = await cur.fetchone()
            await conn.commit()

            if is_master_code:
                logger.info(f"Created MASTER CODE: {code} - {description}")
            else:
                logger.info(f"Created invite code: {code}")

            return str(result['id'])


async def validate_invite_code(code: str) -> Optional[dict]:
    """
    Validate an invite code and return its details if valid
    Returns None if code is invalid, expired, or used up
    Master codes bypass max_uses check and can be used indefinitely
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, code, max_uses, uses_count, tier, trial_days, expires_at, active, is_master_code, description
                FROM invite_codes
                WHERE code = %s
                """,
                (code,)
            )
            result = await cur.fetchone()

            if not result:
                return None

            code_id, code_str, max_uses, uses_count, tier, trial_days, expires_at, active, is_master_code, description = result

            # Check if code is active
            if not active:
                logger.warning(f"Invite code {code} is inactive")
                return None

            # Check if code has expired
            if expires_at and datetime.now() > expires_at:
                logger.warning(f"Invite code {code} has expired")
                return None

            # Check if code has remaining uses (SKIP for master codes)
            if not is_master_code:
                if max_uses is not None and uses_count >= max_uses:
                    logger.warning(f"Invite code {code} has reached max uses ({max_uses})")
                    return None
            else:
                logger.info(f"Validating MASTER CODE: {code} (unlimited uses, current count: {uses_count})")

            return {
                'id': str(code_id),
                'code': code_str,
                'tier': tier,
                'trial_days': trial_days,
                'is_master_code': is_master_code,
                'description': description
            }


async def use_invite_code(code: str, telegram_id: str) -> bool:
    """
    Mark invite code as used and activate user
    Returns True if successful, False otherwise
    Supports both regular codes and master codes (unlimited uses)
    """
    # Validate code FIRST (before incrementing)
    code_details = await validate_invite_code(code)
    if not code_details:
        return False

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Increment uses_count
            await cur.execute(
                """
                UPDATE invite_codes
                SET uses_count = uses_count + 1
                WHERE code = %s
                RETURNING uses_count, is_master_code, max_uses
                """,
                (code,)
            )
            usage_info = await cur.fetchone()

            if usage_info:
                uses_count, is_master_code, max_uses = usage_info
                if is_master_code:
                    logger.info(f"Master code {code} used (total uses: {uses_count}, unlimited)")
                else:
                    logger.info(f"Invite code {code} used ({uses_count}/{max_uses or 'unlimited'})")

            # Activate user with appropriate subscription
            trial_days = code_details['trial_days']
            tier = code_details['tier']

            if trial_days > 0:
                # Set trial subscription
                from datetime import timedelta
                end_date = datetime.now() + timedelta(days=trial_days)
                await cur.execute(
                    """
                    UPDATE users
                    SET subscription_status = 'trial',
                        subscription_tier = %s,
                        subscription_start_date = NOW(),
                        subscription_end_date = %s,
                        activated_at = NOW(),
                        invite_code_used = %s
                    WHERE telegram_id = %s
                    """,
                    (tier, end_date, code, telegram_id)
                )
            else:
                # Set active subscription (no expiry)
                await cur.execute(
                    """
                    UPDATE users
                    SET subscription_status = 'active',
                        subscription_tier = %s,
                        subscription_start_date = NOW(),
                        activated_at = NOW(),
                        invite_code_used = %s
                    WHERE telegram_id = %s
                    """,
                    (tier, code, telegram_id)
                )

            await conn.commit()
            logger.info(f"User {telegram_id} activated with code {code}")
            return True


async def get_user_subscription_status(telegram_id: str) -> Optional[dict]:
    """Get user's subscription status"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT subscription_status, subscription_tier, subscription_start_date,
                       subscription_end_date, activated_at, invite_code_used
                FROM users
                WHERE telegram_id = %s
                """,
                (telegram_id,)
            )
            result = await cur.fetchone()

            if not result:
                return None

            status, tier, start_date, end_date, activated_at, code_used = result

            return {
                'status': status,
                'tier': tier,
                'start_date': start_date,
                'end_date': end_date,
                'activated_at': activated_at,
                'invite_code_used': code_used
            }


async def get_master_codes() -> list:
    """Get all active master codes"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT code, tier, trial_days, description, uses_count, created_at, active
                FROM invite_codes
                WHERE is_master_code = true
                ORDER BY created_at DESC
                """
            )
            return await cur.fetchall()


async def deactivate_invite_code(code: str) -> bool:
    """
    Deactivate an invite code (sets active=false)
    Used to disable compromised or unwanted codes
    Returns True if successful, False if code not found
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE invite_codes
                SET active = false
                WHERE code = %s
                RETURNING id, is_master_code
                """,
                (code,)
            )
            result = await cur.fetchone()
            await conn.commit()

            if result:
                code_id, is_master = result
                code_type = "MASTER CODE" if is_master else "invite code"
                logger.warning(f"Deactivated {code_type}: {code}")
                return True
            else:
                logger.warning(f"Attempted to deactivate non-existent code: {code}")
                return False


# ==========================================
# Onboarding State Management
# ==========================================

async def get_onboarding_state(user_id: str) -> Optional[dict]:
    """Get current onboarding state for user"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT onboarding_path, current_step, step_data,
                       completed_steps, started_at, completed_at, last_interaction_at
                FROM user_onboarding_state
                WHERE user_id = %s
                """,
                (user_id,)
            )
            row = await cur.fetchone()
            return dict(row) if row else None


async def start_onboarding(user_id: str, path: str) -> None:
    """
    Initialize or update onboarding state for a user

    Args:
        user_id: Telegram user ID
        path: Onboarding path - "pending" (initial), "quick", "full", or "chat"

    Note: Only sets current_step to 'path_selection' when path is "pending".
    When path is quick/full/chat, only updates the path without resetting current_step.
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            if path == "pending":
                # Initial state: user hasn't selected a path yet
                await cur.execute(
                    """
                    INSERT INTO user_onboarding_state (user_id, onboarding_path, current_step)
                    VALUES (%s, %s, 'path_selection')
                    ON CONFLICT (user_id) DO UPDATE SET
                        onboarding_path = EXCLUDED.onboarding_path,
                        current_step = 'path_selection',
                        started_at = CURRENT_TIMESTAMP,
                        last_interaction_at = CURRENT_TIMESTAMP
                    """,
                    (user_id, path)
                )
            else:
                # User selected a path: update path but DON'T reset current_step
                await cur.execute(
                    """
                    INSERT INTO user_onboarding_state (user_id, onboarding_path, current_step)
                    VALUES (%s, %s, 'path_selection')
                    ON CONFLICT (user_id) DO UPDATE SET
                        onboarding_path = EXCLUDED.onboarding_path,
                        last_interaction_at = CURRENT_TIMESTAMP
                    """,
                    (user_id, path)
                )
            await conn.commit()
    logger.info(f"Started onboarding for {user_id} on path: {path}")


async def update_onboarding_step(
    user_id: str,
    new_step: str,
    step_data: dict = None,
    mark_complete: str = None
) -> None:
    """Update user's current onboarding step and optionally mark previous step complete"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            if mark_complete:
                # Mark previous step as complete and advance
                await cur.execute(
                    """
                    UPDATE user_onboarding_state
                    SET current_step = %s,
                        step_data = %s,
                        completed_steps = array_append(completed_steps, %s),
                        last_interaction_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                    """,
                    (new_step, json.dumps(step_data or {}), mark_complete, user_id)
                )
            else:
                # Just update current step
                await cur.execute(
                    """
                    UPDATE user_onboarding_state
                    SET current_step = %s,
                        step_data = %s,
                        last_interaction_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                    """,
                    (new_step, json.dumps(step_data or {}), user_id)
                )
            await conn.commit()
    logger.info(f"Updated onboarding step for {user_id}: {new_step}")


async def complete_onboarding(user_id: str) -> None:
    """Mark onboarding as completed"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE user_onboarding_state
                SET current_step = 'completed',
                    completed_at = CURRENT_TIMESTAMP,
                    last_interaction_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                """,
                (user_id,)
            )
            await conn.commit()
    logger.info(f"Completed onboarding for {user_id}")


async def log_feature_discovery(
    user_id: str,
    feature_name: str,
    discovery_method: str = "contextual"
) -> None:
    """Log when a user discovers a feature"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO feature_discovery_log
                (user_id, feature_name, discovery_method)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, feature_name) DO NOTHING
                """,
                (user_id, feature_name, discovery_method)
            )
            await conn.commit()
    logger.info(f"Logged feature discovery: {user_id} -> {feature_name}")


async def log_feature_usage(user_id: str, feature_name: str) -> None:
    """Log when a user actually uses a feature"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO feature_discovery_log
                (user_id, feature_name, first_used_at, usage_count, last_used_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, feature_name)
                DO UPDATE SET
                    first_used_at = COALESCE(feature_discovery_log.first_used_at, CURRENT_TIMESTAMP),
                    usage_count = feature_discovery_log.usage_count + 1,
                    last_used_at = CURRENT_TIMESTAMP
                """,
                (user_id, feature_name)
            )
            await conn.commit()
    logger.info(f"Logged feature usage: {user_id} used {feature_name}")


# Sleep entry operations
async def save_sleep_entry(entry: SleepEntry) -> None:
    """Save sleep quiz entry to database"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO sleep_entries
                (id, user_id, logged_at, bedtime, sleep_latency_minutes, wake_time,
                 total_sleep_hours, night_wakings, sleep_quality_rating, disruptions,
                 phone_usage, phone_duration_minutes, alertness_rating)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    entry.id,
                    entry.user_id,
                    entry.logged_at,
                    str(entry.bedtime),  # Convert time to string for psycopg
                    entry.sleep_latency_minutes,
                    str(entry.wake_time),  # Convert time to string for psycopg
                    entry.total_sleep_hours,
                    entry.night_wakings,
                    entry.sleep_quality_rating,
                    json.dumps(entry.disruptions),  # Convert list to JSON
                    entry.phone_usage,
                    entry.phone_duration_minutes,
                    entry.alertness_rating
                )
            )
            await conn.commit()
    logger.info(f"Saved sleep entry for user {entry.user_id}")


async def get_sleep_entries(user_id: str, days: int = 7) -> list[dict]:
    """Get recent sleep entries for user"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, logged_at, bedtime, sleep_latency_minutes, wake_time,
                       total_sleep_hours, night_wakings, sleep_quality_rating, disruptions,
                       phone_usage, phone_duration_minutes, alertness_rating
                FROM sleep_entries
                WHERE user_id = %s AND logged_at > NOW() - INTERVAL '%s days'
                ORDER BY logged_at DESC
                """,
                (user_id, days)
            )
            rows = await cur.fetchall()

            if not rows:
                return []

            # Get column names
            columns = [desc[0] for desc in cur.description]

            # Convert rows to list of dicts
            return [dict(zip(columns, row)) for row in rows]


# ==========================================
# Reminder Completion Functions
# ==========================================

async def save_reminder_completion(
    reminder_id: str,
    user_id: str,
    scheduled_time: str,
    notes: Optional[str] = None
) -> None:
    """
    Save reminder completion with actual completion timestamp

    Args:
        reminder_id: UUID of the reminder that was completed
        user_id: Telegram user ID
        scheduled_time: Original scheduled time of reminder (e.g., "08:00")
        notes: Optional notes from user
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Convert scheduled_time string to timestamp (use today's date + scheduled time)
            from datetime import datetime, time as time_type

            # Parse scheduled time (HH:MM format)
            try:
                hour, minute = map(int, scheduled_time.split(":"))
                today = datetime.now().date()
                scheduled_datetime = datetime.combine(today, time_type(hour, minute))
            except (ValueError, AttributeError):
                # If parsing fails, use current time as fallback
                scheduled_datetime = datetime.now()

            await cur.execute(
                """
                INSERT INTO reminder_completions
                (reminder_id, user_id, scheduled_time, notes)
                VALUES (%s, %s, %s, %s)
                """,
                (reminder_id, user_id, scheduled_datetime, notes)
            )
            await conn.commit()

    logger.info(f"Saved reminder completion for user {user_id}, reminder {reminder_id}")


async def get_reminder_completions(
    user_id: str,
    reminder_id: Optional[str] = None,
    days: int = 30
) -> list[dict]:
    """
    Get reminder completion history

    Args:
        user_id: Telegram user ID
        reminder_id: Optional specific reminder UUID to filter by
        days: Number of days of history to retrieve

    Returns:
        List of completion records with scheduled_time and completed_at
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            if reminder_id:
                # Get completions for specific reminder
                await cur.execute(
                    """
                    SELECT id, reminder_id, user_id, scheduled_time, completed_at, notes
                    FROM reminder_completions
                    WHERE user_id = %s AND reminder_id = %s
                    AND completed_at > NOW() - INTERVAL '%s days'
                    ORDER BY completed_at DESC
                    """,
                    (user_id, reminder_id, days)
                )
            else:
                # Get all completions for user
                await cur.execute(
                    """
                    SELECT id, reminder_id, user_id, scheduled_time, completed_at, notes
                    FROM reminder_completions
                    WHERE user_id = %s
                    AND completed_at > NOW() - INTERVAL '%s days'
                    ORDER BY completed_at DESC
                    """,
                    (user_id, days)
                )

            rows = await cur.fetchall()

            if not rows:
                return []

            # Get column names
            columns = [desc[0] for desc in cur.description]

            # Convert rows to list of dicts
            return [dict(zip(columns, row)) for row in rows]


async def has_completed_reminder_today(
    user_id: str,
    reminder_id: str
) -> bool:
    """
    Check if user has completed a specific reminder today (in user's timezone)

    Args:
        user_id: Telegram user ID
        reminder_id: Reminder UUID

    Returns:
        True if reminder was completed today, False otherwise
    """
    from src.utils.datetime_helpers import now_user_timezone

    # Get today's date in user's timezone
    now = now_user_timezone(user_id)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT COUNT(*) FROM reminder_completions
                WHERE user_id = %s AND reminder_id = %s AND completed_at >= %s
                """,
                (user_id, reminder_id, today_start)
            )

            row = await cur.fetchone()
            count = row[0] if row else 0
            return count > 0


# ==========================================
# Sleep Quiz Settings Functions
# ==========================================

async def get_sleep_quiz_settings(user_id: str) -> Optional[dict]:
    """Get sleep quiz settings for user"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT user_id, enabled, preferred_time, timezone, language_code,
                       created_at, updated_at
                FROM sleep_quiz_settings
                WHERE user_id = %s
                """,
                (user_id,)
            )
            row = await cur.fetchone()
            return dict(row) if row else None


async def save_sleep_quiz_settings(settings: SleepQuizSettings) -> None:
    """Create or update sleep quiz settings"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO sleep_quiz_settings
                (user_id, enabled, preferred_time, timezone, language_code)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    enabled = EXCLUDED.enabled,
                    preferred_time = EXCLUDED.preferred_time,
                    timezone = EXCLUDED.timezone,
                    language_code = EXCLUDED.language_code,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    settings.user_id,
                    settings.enabled,
                    str(settings.preferred_time),
                    settings.timezone,
                    settings.language_code
                )
            )
            await conn.commit()
    logger.info(f"Saved sleep quiz settings for {settings.user_id}")


async def get_all_enabled_sleep_quiz_users() -> list[dict]:
    """Get all users with sleep quiz enabled (for scheduling on startup)"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT user_id, enabled, preferred_time, timezone, language_code
                FROM sleep_quiz_settings
                WHERE enabled = true
                ORDER BY user_id
                """
            )
            return await cur.fetchall()


async def save_sleep_quiz_submission(submission: SleepQuizSubmission) -> None:
    """Record quiz submission for pattern learning"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO sleep_quiz_submissions
                (id, user_id, scheduled_time, submitted_at, response_delay_minutes)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    submission.id,
                    submission.user_id,
                    submission.scheduled_time,
                    submission.submitted_at,
                    submission.response_delay_minutes
                )
            )
            await conn.commit()
    logger.info(f"Saved submission pattern for {submission.user_id}")


async def get_submission_patterns(user_id: str, days: int = 30) -> list[dict]:
    """Get recent submission patterns for analysis"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, scheduled_time, submitted_at, response_delay_minutes
                FROM sleep_quiz_submissions
                WHERE user_id = %s
                  AND submitted_at > NOW() - INTERVAL '%s days'
                ORDER BY submitted_at DESC
                """,
                (user_id, days)
            )
            rows = await cur.fetchall()

            if not rows:
                return []

            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in rows]


# ==========================================
# Reminder Skip Functions
# ==========================================

async def save_reminder_skip(
    reminder_id: str,
    user_id: str,
    scheduled_time: str,
    reason: Optional[str] = None,
    notes: Optional[str] = None
) -> None:
    """
    Save reminder skip with reason

    Args:
        reminder_id: UUID of the reminder that was skipped
        user_id: Telegram user ID
        scheduled_time: Original scheduled time (HH:MM format)
        reason: Skip reason (sick, out_of_stock, doctor_advice, other)
        notes: Optional additional notes
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Parse scheduled time
            from datetime import datetime, time as time_type
            try:
                hour, minute = map(int, scheduled_time.split(":"))
                today = datetime.now().date()
                scheduled_datetime = datetime.combine(today, time_type(hour, minute))
            except (ValueError, AttributeError):
                scheduled_datetime = datetime.now()

            await cur.execute(
                """
                INSERT INTO reminder_skips
                (reminder_id, user_id, scheduled_time, reason, notes)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (reminder_id, user_id, scheduled_datetime, reason, notes)
            )
            await conn.commit()

    logger.info(f"Saved reminder skip for user {user_id}, reminder {reminder_id}, reason={reason}")


async def get_reminder_by_id(reminder_id: str) -> Optional[dict]:
    """
    Get reminder by UUID

    Args:
        reminder_id: Reminder UUID

    Returns:
        Reminder dict or None if not found
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM reminders WHERE id = %s",
                (reminder_id,)
            )
            row = await cur.fetchone()

            if not row:
                return None

            columns = [desc[0] for desc in cur.description]
            return dict(zip(columns, row))


# ==========================================
# Streak Calculation Functions
# ==========================================

async def calculate_current_streak(user_id: str, reminder_id: str) -> int:
    """
    Calculate current streak for a reminder

    A streak is maintained if the user completed the reminder on consecutive days.
    Missing a day (no completion AND no skip) breaks the streak.

    Args:
        user_id: Telegram user ID
        reminder_id: Reminder UUID

    Returns:
        Current streak count (days)
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Get all completions and skips, ordered by date
            await cur.execute(
                """
                WITH combined AS (
                    SELECT DATE(completed_at) as action_date, 'completed' as action_type
                    FROM reminder_completions
                    WHERE user_id = %s AND reminder_id = %s
                    UNION
                    SELECT DATE(skipped_at) as action_date, 'skipped' as action_type
                    FROM reminder_skips
                    WHERE user_id = %s AND reminder_id = %s
                )
                SELECT action_date, action_type
                FROM combined
                WHERE action_date >= CURRENT_DATE - INTERVAL '60 days'
                ORDER BY action_date DESC
                """,
                (user_id, reminder_id, user_id, reminder_id)
            )

            rows = await cur.fetchall()
            if not rows:
                return 0

            # Calculate streak from most recent backwards
            from datetime import date, timedelta

            streak = 0
            expected_date = date.today()

            for row in rows:
                action_date = row[0]

                # If we found action on expected date, increment streak
                if action_date == expected_date:
                    streak += 1
                    expected_date -= timedelta(days=1)
                elif action_date < expected_date:
                    # Gap detected - streak broken
                    break

            return streak


async def calculate_best_streak(user_id: str, reminder_id: str) -> int:
    """
    Calculate best (longest) streak for a reminder

    Args:
        user_id: Telegram user ID
        reminder_id: Reminder UUID

    Returns:
        Best streak count (days)
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Get all completion/skip dates
            await cur.execute(
                """
                WITH combined AS (
                    SELECT DATE(completed_at) as action_date
                    FROM reminder_completions
                    WHERE user_id = %s AND reminder_id = %s
                    UNION
                    SELECT DATE(skipped_at) as action_date
                    FROM reminder_skips
                    WHERE user_id = %s AND reminder_id = %s
                )
                SELECT action_date
                FROM combined
                ORDER BY action_date ASC
                """,
                (user_id, reminder_id, user_id, reminder_id)
            )

            rows = await cur.fetchall()
            if not rows:
                return 0

            # Find longest consecutive sequence
            from datetime import timedelta

            max_streak = 0
            current_streak = 1

            for i in range(1, len(rows)):
                prev_date = rows[i-1][0]
                curr_date = rows[i][0]

                # Check if consecutive days
                if (curr_date - prev_date).days == 1:
                    current_streak += 1
                    max_streak = max(max_streak, current_streak)
                else:
                    current_streak = 1

            return max(max_streak, current_streak)


# ============================================
# Reminder Analytics Functions (Week 2)
# ============================================

async def get_reminder_analytics(
    user_id: str,
    reminder_id: str,
    days: int = 30
) -> dict:
    """
    Calculate comprehensive analytics for a reminder over specified period
    
    Args:
        user_id: Telegram user ID
        reminder_id: Reminder UUID
        days: Number of days to analyze (default: 30)
    
    Returns:
        dict with:
        - completion_rate: Percentage (0-100)
        - total_expected: Days reminder was active in period
        - total_completions: Number of completions
        - total_skips: Number of skips
        - total_missed: Days with no action
        - current_streak: Current consecutive days
        - best_streak: Best streak in period
        - average_delay_minutes: Average time after scheduled
        - skip_reasons: Breakdown by reason
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Get reminder details
            await cur.execute(
                """
                SELECT schedule, created_at
                FROM reminders
                WHERE id = %s AND user_id = %s AND active = true
                """,
                (reminder_id, user_id)
            )
            reminder_row = await cur.fetchone()
            
            if not reminder_row:
                return {
                    "error": "Reminder not found or inactive"
                }
            
            schedule_json, created_at = reminder_row
            
            # Get completions in period
            await cur.execute(
                """
                SELECT 
                    DATE(completed_at) as completion_date,
                    scheduled_time,
                    completed_at
                FROM reminder_completions
                WHERE reminder_id = %s 
                  AND user_id = %s
                  AND completed_at >= CURRENT_DATE - INTERVAL '%s days'
                ORDER BY completed_at DESC
                """,
                (reminder_id, user_id, days)
            )
            completions = await cur.fetchall()
            
            # Get skips in period
            await cur.execute(
                """
                SELECT 
                    DATE(skipped_at) as skip_date,
                    reason,
                    skipped_at
                FROM reminder_skips
                WHERE reminder_id = %s 
                  AND user_id = %s
                  AND skipped_at >= CURRENT_DATE - INTERVAL '%s days'
                ORDER BY skipped_at DESC
                """,
                (reminder_id, user_id, days)
            )
            skips = await cur.fetchall()
            
            # Calculate statistics
            total_completions = len(completions)
            total_skips = len(skips)
            total_expected = days  # Simplified - assumes daily reminder
            total_actions = total_completions + total_skips
            total_missed = max(0, total_expected - total_actions)
            
            completion_rate = (total_completions / total_expected * 100) if total_expected > 0 else 0
            
            # Calculate average delay (completions only)
            delays = []
            for completion in completions:
                completion_date, scheduled_time, completed_at = completion
                # Parse scheduled time (HH:MM format)
                sched_hour, sched_min = map(int, scheduled_time.split(':'))
                scheduled_datetime = completed_at.replace(
                    hour=sched_hour, 
                    minute=sched_min, 
                    second=0, 
                    microsecond=0
                )
                delay_seconds = (completed_at - scheduled_datetime).total_seconds()
                delay_minutes = int(delay_seconds / 60)
                delays.append(delay_minutes)
            
            average_delay_minutes = int(sum(delays) / len(delays)) if delays else 0
            
            # Skip reasons breakdown
            skip_reasons = {}
            for skip in skips:
                _, reason, _ = skip
                reason = reason or 'other'
                skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
            
            # Get streaks (use existing functions)
            current_streak = await calculate_current_streak(user_id, reminder_id)
            best_streak = await calculate_best_streak(user_id, reminder_id)
            
            return {
                "completion_rate": round(completion_rate, 1),
                "total_expected": total_expected,
                "total_completions": total_completions,
                "total_skips": total_skips,
                "total_missed": total_missed,
                "current_streak": current_streak,
                "best_streak": best_streak,
                "average_delay_minutes": average_delay_minutes,
                "skip_reasons": skip_reasons,
                "period_days": days
            }


async def analyze_day_of_week_patterns(
    user_id: str,
    reminder_id: str,
    days: int = 60
) -> dict:
    """
    Analyze completion patterns by day of week
    
    Args:
        user_id: Telegram user ID
        reminder_id: Reminder UUID
        days: Days of history to analyze (default: 60 for ~8 weeks)
    
    Returns:
        dict with day names as keys (Monday-Sunday), each containing:
        - completions: Count
        - skips: Count
        - missed: Count
        - completion_rate: Percentage
        - average_delay_minutes: Average delay for this day
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Get completions by day of week
            await cur.execute(
                """
                SELECT 
                    EXTRACT(DOW FROM completed_at) as dow,
                    COUNT(*) as count,
                    AVG(
                        EXTRACT(EPOCH FROM (completed_at - 
                            (DATE(completed_at) + (scheduled_time || ':00')::time)
                        )) / 60
                    ) as avg_delay_minutes
                FROM reminder_completions
                WHERE reminder_id = %s 
                  AND user_id = %s
                  AND completed_at >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY EXTRACT(DOW FROM completed_at)
                """,
                (reminder_id, user_id, days)
            )
            completion_rows = await cur.fetchall()
            
            # Get skips by day of week
            await cur.execute(
                """
                SELECT 
                    EXTRACT(DOW FROM skipped_at) as dow,
                    COUNT(*) as count
                FROM reminder_skips
                WHERE reminder_id = %s 
                  AND user_id = %s
                  AND skipped_at >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY EXTRACT(DOW FROM skipped_at)
                """,
                (reminder_id, user_id, days)
            )
            skip_rows = await cur.fetchall()
            
            # Build day-of-week mapping
            dow_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            
            # Initialize all days
            patterns = {}
            for dow_num, dow_name in enumerate(dow_names):
                patterns[dow_name] = {
                    "completions": 0,
                    "skips": 0,
                    "missed": 0,
                    "completion_rate": 0.0,
                    "average_delay_minutes": 0
                }
            
            # Fill in completion data
            for row in completion_rows:
                dow_num = int(row[0])
                count = row[1]
                avg_delay = int(row[2]) if row[2] else 0
                
                dow_name = dow_names[dow_num]
                patterns[dow_name]["completions"] = count
                patterns[dow_name]["average_delay_minutes"] = avg_delay
            
            # Fill in skip data
            for row in skip_rows:
                dow_num = int(row[0])
                count = row[1]
                
                dow_name = dow_names[dow_num]
                patterns[dow_name]["skips"] = count
            
            # Calculate completion rates (simplified - assumes daily reminder)
            # For more accuracy, would need to count actual scheduled days
            weeks_analyzed = days / 7
            for dow_name, stats in patterns.items():
                expected_occurrences = int(weeks_analyzed)
                total_actions = stats["completions"] + stats["skips"]
                stats["missed"] = max(0, expected_occurrences - total_actions)
                
                if expected_occurrences > 0:
                    stats["completion_rate"] = round(
                        (stats["completions"] / expected_occurrences) * 100, 1
                    )
            
            return patterns


async def get_multi_reminder_comparison(
    user_id: str,
    days: int = 30
) -> list[dict]:
    """
    Compare all user's tracked reminders
    
    Args:
        user_id: Telegram user ID
        days: Period to analyze (default: 30)
    
    Returns:
        List of reminder summaries, each containing:
        - reminder_id: UUID
        - message: Reminder message
        - completion_rate: Percentage
        - current_streak: Current streak
        - total_completions: Count
        - total_skips: Count
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Get all active reminders with tracking enabled
            await cur.execute(
                """
                SELECT id, message
                FROM reminders
                WHERE user_id = %s 
                  AND active = true
                  AND enable_completion_tracking = true
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
            reminders = await cur.fetchall()
            
            comparisons = []
            
            for reminder_row in reminders:
                reminder_id, message = reminder_row
                
                # Get analytics for this reminder
                analytics = await get_reminder_analytics(user_id, str(reminder_id), days)
                
                if "error" not in analytics:
                    comparisons.append({
                        "reminder_id": str(reminder_id),
                        "message": message,
                        "completion_rate": analytics["completion_rate"],
                        "current_streak": analytics["current_streak"],
                        "total_completions": analytics["total_completions"],
                        "total_skips": analytics["total_skips"],
                        "average_delay_minutes": analytics["average_delay_minutes"]
                    })
            
            # Sort by completion rate (descending)
            comparisons.sort(key=lambda x: x["completion_rate"], reverse=True)

            return comparisons


# ========================================
# Phase 3: Adaptive Intelligence Functions
# ========================================

async def detect_timing_patterns(user_id: str, reminder_id: str, days: int = 30) -> dict:
    """
    Detect timing patterns in reminder completions

    Returns:
        {
            'consistent_early': bool,  # >70% completions are >15 min early
            'consistent_late': bool,   # >70% completions are >15 min late
            'average_delay_minutes': float,
            'weekday_vs_weekend_diff': bool,  # Significant timing difference
            'suggested_time_adjustment': Optional[int],  # Minutes to adjust
            'pattern_confidence': float  # 0.0 to 1.0
        }
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Get completion time patterns
            await cur.execute(
                """
                SELECT
                    EXTRACT(EPOCH FROM (completed_at - scheduled_time))/60 as delay_minutes,
                    EXTRACT(DOW FROM scheduled_time) as day_of_week,
                    completed_at
                FROM reminder_completions
                WHERE user_id = %s AND reminder_id = %s
                AND completed_at > NOW() - INTERVAL '%s days'
                ORDER BY completed_at DESC
                """,
                (user_id, reminder_id, days)
            )

            completions = await cur.fetchall()

            if len(completions) < 7:  # Need at least a week of data
                return {
                    "error": "Insufficient data",
                    "pattern_confidence": 0.0
                }

            # Analyze delays
            delays = [row[0] for row in completions]
            avg_delay = sum(delays) / len(delays)

            # Check for consistent early/late patterns
            early_count = sum(1 for d in delays if d < -15)  # >15 min early
            late_count = sum(1 for d in delays if d > 15)     # >15 min late
            total = len(delays)

            consistent_early = (early_count / total) > 0.7
            consistent_late = (late_count / total) > 0.7

            # Weekday vs weekend analysis
            weekday_delays = [row[0] for row in completions if row[1] in (1, 2, 3, 4, 5)]  # Mon-Fri
            weekend_delays = [row[0] for row in completions if row[1] in (0, 6)]  # Sat-Sun

            weekday_weekend_diff = False
            if len(weekday_delays) >= 3 and len(weekend_delays) >= 2:
                weekday_avg = sum(weekday_delays) / len(weekday_delays)
                weekend_avg = sum(weekend_delays) / len(weekend_delays)
                # Significant if >30 min difference
                weekday_weekend_diff = abs(weekday_avg - weekend_avg) > 30

            # Suggest time adjustment
            suggested_adjustment = None
            if consistent_early or consistent_late:
                # Round to nearest 15 minutes
                suggested_adjustment = int(round(avg_delay / 15) * 15)

            # Calculate confidence based on data consistency
            variance = sum((d - avg_delay) ** 2 for d in delays) / len(delays)
            std_dev = variance ** 0.5
            # Higher std dev = lower confidence
            confidence = max(0.0, min(1.0, 1.0 - (std_dev / 60)))  # Normalize to 0-1

            return {
                "consistent_early": consistent_early,
                "consistent_late": consistent_late,
                "average_delay_minutes": round(avg_delay, 1),
                "weekday_vs_weekend_diff": weekday_weekend_diff,
                "suggested_time_adjustment": suggested_adjustment,
                "pattern_confidence": round(confidence, 2),
                "sample_size": total
            }


async def detect_difficult_days(user_id: str, reminder_id: str, days: int = 30) -> dict:
    """
    Detect days of week with low completion rates

    Returns:
        {
            'difficult_days': list[str],  # e.g., ['Thursday', 'Saturday']
            'day_completion_rates': dict[str, float],
            'worst_day': str,
            'worst_day_rate': float
        }
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Get expected completions per day
            await cur.execute(
                """
                SELECT
                    EXTRACT(DOW FROM scheduled_time) as day_of_week,
                    COUNT(*) as expected
                FROM reminder_completions
                WHERE user_id = %s AND reminder_id = %s
                AND scheduled_time > NOW() - INTERVAL '%s days'
                GROUP BY day_of_week
                """,
                (user_id, reminder_id, days)
            )

            expected_by_day = {row[0]: row[1] for row in await cur.fetchall()}

            if not expected_by_day:
                return {"error": "No completion data"}

            # Get actual completions per day
            await cur.execute(
                """
                SELECT
                    EXTRACT(DOW FROM scheduled_time) as day_of_week,
                    COUNT(*) as completed
                FROM reminder_completions
                WHERE user_id = %s AND reminder_id = %s
                AND completed_at IS NOT NULL
                AND scheduled_time > NOW() - INTERVAL '%s days'
                GROUP BY day_of_week
                """,
                (user_id, reminder_id, days)
            )

            completed_by_day = {row[0]: row[1] for row in await cur.fetchall()}

            # Calculate completion rates per day
            day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            day_rates = {}

            for day_num in expected_by_day.keys():
                expected = expected_by_day.get(day_num, 0)
                completed = completed_by_day.get(day_num, 0)
                rate = completed / expected if expected > 0 else 0.0
                day_rates[day_names[int(day_num)]] = round(rate, 2)

            # Find difficult days (<50% completion rate)
            user_avg_rate = sum(day_rates.values()) / len(day_rates) if day_rates else 0.0
            difficult_days = [
                day for day, rate in day_rates.items()
                if rate < 0.5  # Less than 50% completion
            ]

            # Find worst day
            worst_day = min(day_rates.items(), key=lambda x: x[1]) if day_rates else (None, 0.0)

            return {
                "difficult_days": difficult_days,
                "day_completion_rates": day_rates,
                "worst_day": worst_day[0],
                "worst_day_rate": worst_day[1],
                "average_completion_rate": round(user_avg_rate, 2)
            }


async def generate_adaptive_suggestions(user_id: str, reminder_id: str) -> list[dict]:
    """
    Generate personalized suggestions for improving reminder completion

    Returns list of suggestions with:
        {
            'type': str,  # 'timing_adjustment', 'difficult_day_support', 'schedule_split'
            'title': str,
            'description': str,
            'action': dict,  # Action parameters
            'priority': str,  # 'high', 'medium', 'low'
        }
    """
    suggestions = []

    # Get timing patterns
    timing_patterns = await detect_timing_patterns(user_id, reminder_id)

    if timing_patterns.get("pattern_confidence", 0) > 0.6:
        # Timing adjustment suggestion
        if timing_patterns.get("consistent_late"):
            adjustment = timing_patterns.get("suggested_time_adjustment", 0)
            if adjustment and abs(adjustment) >= 15:
                suggestions.append({
                    "type": "timing_adjustment",
                    "title": "Adjust Reminder Time",
                    "description": f"You typically complete this {abs(adjustment)} minutes late. "
                                   f"Move reminder to better match your natural rhythm?",
                    "action": {
                        "adjust_minutes": adjustment
                    },
                    "priority": "high" if abs(adjustment) > 30 else "medium"
                })

        # Weekday/weekend split
        if timing_patterns.get("weekday_vs_weekend_diff"):
            suggestions.append({
                "type": "schedule_split",
                "title": "Different Schedule for Weekends",
                "description": "Your completion times differ significantly on weekends. "
                               "Use separate reminder times for weekdays vs weekends?",
                "action": {
                    "enable_split_schedule": True
                },
                "priority": "medium"
            })

    # Get difficult days
    difficult_days_data = await detect_difficult_days(user_id, reminder_id)

    if difficult_days_data.get("difficult_days"):
        for day in difficult_days_data["difficult_days"]:
            rate = difficult_days_data["day_completion_rates"].get(day, 0)
            suggestions.append({
                "type": "difficult_day_support",
                "title": f"{day} Needs Support",
                "description": f"Your {day} completion rate is {rate*100:.0f}%, well below average. "
                               f"Add backup reminder or earlier notification on {day}s?",
                "action": {
                    "day_of_week": day,
                    "add_backup_reminder": True
                },
                "priority": "high" if rate < 0.3 else "medium"
            })

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    suggestions.sort(key=lambda x: priority_order.get(x["priority"], 3))

    return suggestions


async def check_missed_reminder_grace_period(user_id: str, reminder_id: str, scheduled_time: datetime) -> bool:
    """
    Check if reminder was missed and grace period has passed

    Returns True if:
    - Reminder was scheduled more than 2 hours ago
    - No completion recorded
    - Tracking is enabled
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Check if completion exists
            await cur.execute(
                """
                SELECT COUNT(*)
                FROM reminder_completions
                WHERE user_id = %s
                AND reminder_id = %s
                AND scheduled_time = %s
                """,
                (user_id, reminder_id, scheduled_time)
            )

            completion_exists = (await cur.fetchone())[0] > 0

            if completion_exists:
                return False

            # Check if 2+ hours have passed
            from datetime import timezone
            now = datetime.now(timezone.utc)
            time_since_scheduled = (now - scheduled_time).total_seconds() / 3600  # hours

            # Check if reminder has tracking enabled
            reminder = await get_reminder_by_id(reminder_id)
            tracking_enabled = reminder.get("enable_completion_tracking", True) if reminder else False

            return tracking_enabled and time_since_scheduled >= 2.0


# ========================================
# Phase 4: Gamification Functions
# ========================================

async def get_all_achievements() -> list[dict]:
    """Get all achievement definitions"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, name, description, icon, category, criteria, tier
                FROM achievements
                ORDER BY
                    CASE tier
                        WHEN 'bronze' THEN 1
                        WHEN 'silver' THEN 2
                        WHEN 'gold' THEN 3
                        WHEN 'platinum' THEN 4
                    END,
                    name
                """
            )

            achievements = []
            for row in await cur.fetchall():
                achievements.append({
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "icon": row[3],
                    "category": row[4],
                    "criteria": row[5],
                    "tier": row[6]
                })

            return achievements


async def get_user_achievements(user_id: str) -> list[dict]:
    """Get all achievements unlocked by user"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT
                    ua.achievement_id,
                    ua.unlocked_at,
                    ua.metadata,
                    a.name,
                    a.description,
                    a.icon,
                    a.category,
                    a.tier
                FROM user_achievements ua
                JOIN achievements a ON ua.achievement_id = a.id
                WHERE ua.user_id = %s
                ORDER BY ua.unlocked_at DESC
                """,
                (user_id,)
            )

            achievements = []
            for row in await cur.fetchall():
                achievements.append({
                    "achievement_id": row[0],
                    "unlocked_at": row[1],
                    "metadata": row[2],
                    "name": row[3],
                    "description": row[4],
                    "icon": row[5],
                    "category": row[6],
                    "tier": row[7]
                })

            return achievements


async def unlock_achievement(
    user_id: str,
    achievement_id: str,
    metadata: dict = None
) -> bool:
    """
    Unlock an achievement for a user

    Returns True if unlocked (new), False if already unlocked
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Try to insert
            await cur.execute(
                """
                INSERT INTO user_achievements (user_id, achievement_id, metadata)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, achievement_id) DO NOTHING
                RETURNING id
                """,
                (user_id, achievement_id, json.dumps(metadata) if metadata else None)
            )

            result = await cur.fetchone()
            await conn.commit()

            return result is not None  # True if inserted, False if already existed


async def count_user_completions(user_id: str) -> int:
    """Count total completions across all reminders"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT COUNT(*)
                FROM reminder_completions
                WHERE user_id = %s
                """,
                (user_id,)
            )

            return (await cur.fetchone())[0]


async def count_early_completions(user_id: str) -> int:
    """Count completions that were early (before scheduled time)"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT COUNT(*)
                FROM reminder_completions
                WHERE user_id = %s
                AND completed_at < scheduled_time
                """,
                (user_id,)
            )

            return (await cur.fetchone())[0]


async def count_active_reminders(user_id: str, tracking_enabled: bool = None) -> int:
    """Count active reminders for user"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            if tracking_enabled is not None:
                await cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM reminders
                    WHERE user_id = %s
                    AND active = true
                    AND enable_completion_tracking = %s
                    """,
                    (user_id, tracking_enabled)
                )
            else:
                await cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM reminders
                    WHERE user_id = %s
                    AND active = true
                    """,
                    (user_id,)
                )

            return (await cur.fetchone())[0]


async def count_perfect_completion_days(user_id: str) -> int:
    """
    Count consecutive days with 100% completion rate

    A perfect day = all scheduled reminders were completed
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # This is a simplified version
            # Full implementation would check daily completion rates
            await cur.execute(
                """
                WITH daily_stats AS (
                    SELECT
                        DATE(scheduled_time) as day,
                        COUNT(*) as scheduled,
                        COUNT(completed_at) as completed
                    FROM reminder_completions
                    WHERE user_id = %s
                    GROUP BY DATE(scheduled_time)
                )
                SELECT COUNT(*)
                FROM daily_stats
                WHERE completed = scheduled
                """,
                (user_id,)
            )

            return (await cur.fetchone())[0]


async def check_recovery_pattern(user_id: str, threshold: float) -> bool:
    """
    Check if user recovered from low completion rate

    Returns True if user had a week <60% then recovered to >threshold
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Get recent weekly completion rates
            await cur.execute(
                """
                WITH weekly_rates AS (
                    SELECT
                        DATE_TRUNC('week', scheduled_time) as week,
                        COUNT(CASE WHEN completed_at IS NOT NULL THEN 1 END)::float /
                        COUNT(*)::float as rate
                    FROM reminder_completions
                    WHERE user_id = %s
                    AND scheduled_time > NOW() - INTERVAL '60 days'
                    GROUP BY DATE_TRUNC('week', scheduled_time)
                    ORDER BY week DESC
                    LIMIT 4
                )
                SELECT rate FROM weekly_rates
                """,
                (user_id,)
            )

            rates = [row[0] for row in await cur.fetchall()]

            if len(rates) < 2:
                return False

            # Check if most recent week is above threshold
            # and previous week(s) were below 60%
            current_rate = rates[0]
            had_low_week = any(r < 0.6 for r in rates[1:])

            return current_rate >= threshold and had_low_week


async def count_stats_views(user_id: str) -> int:
    """
    Count how many times user has viewed statistics

    Note: This would need a tracking table in production.
    For now, estimate based on reminder analytics calls.
    """
    # Placeholder - in production, track this in a separate table
    return 0  # TODO: Implement stats view tracking


async def update_completion_note(
    user_id: str,
    reminder_id: str,
    scheduled_time: str,
    note: str
) -> None:
    """
    Add or update note for a completion

    Args:
        user_id: User's Telegram ID
        reminder_id: Reminder UUID
        scheduled_time: Scheduled time string
        note: Note text (max 200 chars)
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE reminder_completions
                SET notes = %s
                WHERE user_id = %s
                AND reminder_id = %s
                AND scheduled_time = %s
                """,
                (note[:200], user_id, reminder_id, scheduled_time)
            )
            await conn.commit()


# ==========================================
# Gamification System Functions
# ==========================================

# XP Functions
async def get_user_xp_data(user_id: str) -> dict:
    """
    Get user XP data (creates if doesn't exist)

    Returns:
        {
            'user_id': str,
            'total_xp': int,
            'current_level': int,
            'xp_to_next_level': int,
            'level_tier': str,
            'created_at': datetime,
            'updated_at': datetime
        }
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT user_id, total_xp, current_level, xp_to_next_level, level_tier, created_at, updated_at
                FROM user_xp
                WHERE user_id = %s
                """,
                (user_id,)
            )
            row = await cur.fetchone()

            if not row:
                # Create new user XP record with defaults
                await cur.execute(
                    """
                    INSERT INTO user_xp (user_id, total_xp, current_level, xp_to_next_level, level_tier)
                    VALUES (%s, 0, 1, 100, 'bronze')
                    RETURNING user_id, total_xp, current_level, xp_to_next_level, level_tier, created_at, updated_at
                    """,
                    (user_id,)
                )
                row = await cur.fetchone()
                await conn.commit()
                logger.info(f"Created new XP record for user {user_id}")

            return dict(row) if row else None


async def update_user_xp(user_id: str, xp_data: dict) -> None:
    """
    Update user XP data

    Args:
        user_id: User's Telegram ID
        xp_data: Dict with total_xp, current_level, xp_to_next_level, level_tier
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE user_xp
                SET total_xp = %s,
                    current_level = %s,
                    xp_to_next_level = %s,
                    level_tier = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                """,
                (
                    xp_data['total_xp'],
                    xp_data['current_level'],
                    xp_data['xp_to_next_level'],
                    xp_data['level_tier'],
                    user_id
                )
            )
            await conn.commit()


async def add_xp_transaction(
    user_id: str,
    amount: int,
    source_type: str,
    source_id: Optional[str],
    reason: str
) -> str:
    """
    Add XP transaction

    Args:
        user_id: User's Telegram ID
        amount: XP amount
        source_type: 'reminder', 'meal', 'exercise', 'sleep', 'tracking', 'achievement', 'streak_milestone'
        source_id: Optional UUID of source activity
        reason: Human-readable description

    Returns:
        Transaction ID (UUID string)
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO xp_transactions (user_id, amount, source_type, source_id, reason)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (user_id, amount, source_type, source_id, reason)
            )
            result = await cur.fetchone()
            await conn.commit()
            return str(result['id']) if result else None


async def get_xp_transactions(user_id: str, limit: int = 50) -> list[dict]:
    """
    Get recent XP transactions for user

    Args:
        user_id: User's Telegram ID
        limit: Maximum number of transactions to return

    Returns:
        List of transactions ordered by awarded_at DESC
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, amount, source_type, source_id, reason, awarded_at
                FROM xp_transactions
                WHERE user_id = %s
                ORDER BY awarded_at DESC
                LIMIT %s
                """,
                (user_id, limit)
            )
            rows = await cur.fetchall()
            return [dict(row) for row in rows]


# Streak Functions
async def get_user_streak(user_id: str, streak_type: str, source_id: Optional[str] = None) -> dict:
    """
    Get specific streak for user (creates if doesn't exist)

    Args:
        user_id: User's Telegram ID
        streak_type: 'medication', 'nutrition', 'exercise', 'sleep', 'hydration', 'mindfulness', 'overall'
        source_id: Optional specific reminder/category ID

    Returns:
        Streak data dict
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, streak_type, source_id, current_streak, best_streak,
                       last_activity_date, freeze_days_remaining, created_at, updated_at
                FROM user_streaks
                WHERE user_id = %s AND streak_type = %s AND (source_id = %s OR (source_id IS NULL AND %s IS NULL))
                """,
                (user_id, streak_type, source_id, source_id)
            )
            row = await cur.fetchone()

            if not row:
                # Create new streak record
                await cur.execute(
                    """
                    INSERT INTO user_streaks (user_id, streak_type, source_id, current_streak, best_streak, freeze_days_remaining)
                    VALUES (%s, %s, %s, 0, 0, 2)
                    RETURNING id, user_id, streak_type, source_id, current_streak, best_streak,
                              last_activity_date, freeze_days_remaining, created_at, updated_at
                    """,
                    (user_id, streak_type, source_id)
                )
                row = await cur.fetchone()
                await conn.commit()
                logger.info(f"Created new streak for user {user_id}: {streak_type}")

            return dict(row) if row else None


async def update_user_streak(user_id: str, streak_type: str, streak_data: dict, source_id: Optional[str] = None) -> None:
    """
    Update streak data

    Args:
        user_id: User's Telegram ID
        streak_type: Streak type
        streak_data: Dict with current_streak, best_streak, last_activity_date, freeze_days_remaining
        source_id: Optional source ID
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE user_streaks
                SET current_streak = %s,
                    best_streak = %s,
                    last_activity_date = %s,
                    freeze_days_remaining = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s AND streak_type = %s AND (source_id = %s OR (source_id IS NULL AND %s IS NULL))
                """,
                (
                    streak_data['current_streak'],
                    streak_data['best_streak'],
                    streak_data['last_activity_date'],
                    streak_data['freeze_days_remaining'],
                    user_id,
                    streak_type,
                    source_id,
                    source_id
                )
            )
            await conn.commit()


async def get_all_user_streaks(user_id: str) -> list[dict]:
    """
    Get all streaks for user

    Args:
        user_id: User's Telegram ID

    Returns:
        List of all user streaks
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, streak_type, source_id, current_streak, best_streak,
                       last_activity_date, freeze_days_remaining, created_at, updated_at
                FROM user_streaks
                WHERE user_id = %s
                ORDER BY current_streak DESC
                """,
                (user_id,)
            )
            rows = await cur.fetchall()
            return [dict(row) for row in rows]


# Achievement Functions
async def get_all_achievements() -> list[dict]:
    """
    Get all achievement definitions

    Returns:
        List of all achievements
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, achievement_key, name, description, icon, category, criteria, xp_reward, tier, sort_order
                FROM achievements
                ORDER BY sort_order, name
                """
            )
            rows = await cur.fetchall()
            return [dict(row) for row in rows]


async def get_achievement_by_key(key: str) -> Optional[dict]:
    """
    Get achievement by key

    Args:
        key: Achievement key (e.g., 'week_warrior')

    Returns:
        Achievement dict or None
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, achievement_key, name, description, icon, category, criteria, xp_reward, tier, sort_order
                FROM achievements
                WHERE achievement_key = %s
                """,
                (key,)
            )
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_user_achievement_unlocks(user_id: str) -> list[dict]:
    """
    Get user's unlocked achievements

    Args:
        user_id: User's Telegram ID

    Returns:
        List of unlocked achievements with progress
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, achievement_id, unlocked_at, progress
                FROM user_achievements
                WHERE user_id = %s
                ORDER BY unlocked_at DESC
                """,
                (user_id,)
            )
            rows = await cur.fetchall()
            return [dict(row) for row in rows]


async def add_user_achievement(user_id: str, achievement_id: str, progress: Optional[dict] = None) -> bool:
    """
    Add achievement unlock for user

    Args:
        user_id: User's Telegram ID
        achievement_id: Achievement UUID
        progress: Optional progress data

    Returns:
        True if newly unlocked, False if already unlocked
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Try to insert, ignore if already exists
            await cur.execute(
                """
                INSERT INTO user_achievements (user_id, achievement_id, progress)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, achievement_id) DO NOTHING
                RETURNING id
                """,
                (user_id, achievement_id, json.dumps(progress) if progress else None)
            )
            result = await cur.fetchone()
            await conn.commit()

            if result:
                logger.info(f"User {user_id} unlocked achievement {achievement_id}")
                return True
            return False


async def has_user_unlocked_achievement(user_id: str, achievement_id: str) -> bool:
    """
    Check if user has unlocked achievement

    Args:
        user_id: User's Telegram ID
        achievement_id: Achievement UUID

    Returns:
        True if unlocked, False otherwise
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT COUNT(*)
                FROM user_achievements
                WHERE user_id = %s AND achievement_id = %s
                """,
                (user_id, achievement_id)
            )
            result = await cur.fetchone()
            return result['count'] > 0 if result else False


# Aliases for consistency with old mock_store API
async def get_user_achievements(user_id: str) -> list[dict]:
    """Alias for get_user_achievement_unlocks"""
    return await get_user_achievement_unlocks(user_id)


async def unlock_user_achievement(user_id: str, achievement_id: str) -> bool:
    """Alias for add_user_achievement"""
    return await add_user_achievement(user_id, achievement_id)


# API Compatibility Wrapper Functions
async def get_user_xp_level(user_id: str) -> dict:
    """
    Wrapper for API compatibility - returns XP data in expected format

    Converts get_user_xp_data() output to match API endpoint expectations.

    Returns:
        {
            'xp': int,               # total_xp
            'level': int,            # current_level
            'tier': str,             # level_tier
            'xp_to_next_level': int  # xp_to_next_level
        }
    """
    xp_data = await get_user_xp_data(user_id)
    return {
        'xp': xp_data['total_xp'],
        'level': xp_data['current_level'],
        'tier': xp_data['level_tier'],
        'xp_to_next_level': xp_data['xp_to_next_level']
    }


async def get_user_streaks(user_id: str) -> list[dict]:
    """
    Wrapper for API compatibility - alias to get_all_user_streaks

    Returns all streaks for the user.
    """
    return await get_all_user_streaks(user_id)


# Profile and Preference Audit Functions
async def audit_profile_update(
    user_id: str,
    field_name: str,
    old_value: Optional[str],
    new_value: str,
    updated_by: str = "user"
) -> None:
    """
    Log profile field update to audit table

    Args:
        user_id: User's Telegram ID
        field_name: Name of the profile field being updated
        old_value: Previous value (None if new field)
        new_value: New value being set
        updated_by: Source of update ('user' or 'auto')

    Purpose:
        Creates audit trail for profile changes to track data modifications
        and help debug issues where user data changes unexpectedly.
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO profile_update_audit (user_id, field_name, old_value, new_value, updated_by)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, field_name, old_value, new_value, updated_by)
            )
            await conn.commit()
    logger.info(f"Audited profile update for user {user_id}: {field_name}")


async def audit_preference_update(
    user_id: str,
    preference_name: str,
    old_value: Optional[str],
    new_value: str,
    updated_by: str = "user"
) -> None:
    """
    Log preference change to audit table

    Args:
        user_id: User's Telegram ID
        preference_name: Name of the preference being updated
        old_value: Previous value (None if new preference)
        new_value: New value being set
        updated_by: Source of update ('user' or 'auto')

    Purpose:
        Creates audit trail for preference changes to track modifications
        and understand user behavior patterns.
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO preference_update_audit (user_id, preference_name, old_value, new_value, updated_by)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, preference_name, old_value, new_value, updated_by)
            )
            await conn.commit()
    logger.info(f"Audited preference update for user {user_id}: {preference_name}")
