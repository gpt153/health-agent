"""Tracking and sleep entry database queries"""
import json
import logging
import asyncio
from typing import Optional
from datetime import datetime
from uuid import UUID
from src.db.connection import db
from src.models.tracking import TrackingCategory, TrackerEntry
from src.models.sleep import SleepEntry

logger = logging.getLogger(__name__)


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


async def save_tracking_entry(entry: TrackerEntry) -> None:
    """Save tracking entry and create health_event"""
    category_name = None

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # First get category name for metadata
            await cur.execute(
                "SELECT name FROM tracking_categories WHERE id = %s",
                (entry.category_id,)
            )
            category_row = await cur.fetchone()
            category_name = category_row["name"] if category_row else "Unknown"

            # Save tracking entry
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

    # Create health event in background (non-blocking)
    if category_name:
        asyncio.create_task(_create_tracker_health_event(entry, category_name))


async def _create_tracker_health_event(entry: TrackerEntry, category_name: str):
    """
    Background task to create health event for tracker entry.

    This runs asynchronously after the main tracking_entry is saved.
    """
    try:
        from src.services.health_events import create_health_event

        metadata = {
            "category_name": category_name,
            "category_id": str(entry.category_id),
            "data": entry.data,
            "notes": entry.notes
        }

        await create_health_event(
            user_id=entry.user_id,
            event_type="tracker",
            timestamp=entry.timestamp,
            metadata=metadata,
            source_table="tracking_entries",
            source_id=entry.id
        )
        logger.debug(f"Created health_event for tracking_entry {entry.id}")

    except Exception as e:
        logger.error(
            f"Failed to create health_event for tracking_entry {entry.id}",
            exc_info=True
        )


async def get_recent_tracker_entries(user_id: str, category_id, limit: int = 10) -> list[dict]:
    """Get recent tracking entries for a specific tracker"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, category_id, timestamp, data, notes
                FROM tracking_entries
                WHERE user_id = %s AND category_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (user_id, category_id, limit)
            )
            rows = await cur.fetchall()

            if not rows:
                return []

            # Get column names
            columns = [desc[0] for desc in cur.description]

            # Convert rows to list of dicts
            return [dict(zip(columns, row)) for row in rows]


# Sleep entry operations
async def save_sleep_entry(entry: SleepEntry) -> None:
    """Save sleep quiz entry to database and create health_event"""
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

    # Create health event in background (non-blocking)
    asyncio.create_task(_create_sleep_health_event(entry))


async def _create_sleep_health_event(entry: SleepEntry):
    """
    Background task to create health event for sleep entry.

    This runs asynchronously after the main sleep_entry is saved.
    """
    try:
        from src.services.health_events import create_health_event

        metadata = {
            "bedtime": str(entry.bedtime),
            "wake_time": str(entry.wake_time),
            "sleep_latency_minutes": entry.sleep_latency_minutes,
            "total_sleep_hours": entry.total_sleep_hours,
            "night_wakings": entry.night_wakings,
            "sleep_quality_rating": entry.sleep_quality_rating,
            "disruptions": entry.disruptions,
            "phone_usage": entry.phone_usage,
            "phone_duration_minutes": entry.phone_duration_minutes,
            "alertness_rating": entry.alertness_rating
        }

        # Parse entry.id to UUID if it's a string
        entry_id = UUID(entry.id) if isinstance(entry.id, str) else entry.id

        await create_health_event(
            user_id=entry.user_id,
            event_type="sleep",
            timestamp=entry.logged_at,
            metadata=metadata,
            source_table="sleep_entries",
            source_id=entry_id
        )
        logger.debug(f"Created health_event for sleep_entry {entry.id}")

    except Exception as e:
        logger.error(
            f"Failed to create health_event for sleep_entry {entry.id}",
            exc_info=True
        )


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
