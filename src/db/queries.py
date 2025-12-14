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
