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
    messages = []
    for row in reversed(rows):
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
