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
