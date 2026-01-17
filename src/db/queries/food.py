"""Food entry database queries"""
import json
import logging
import asyncio
from typing import Optional
from datetime import datetime
from uuid import UUID
from src.db.connection import db
from src.models.food import FoodEntry

logger = logging.getLogger(__name__)


# Food entry operations
async def save_food_entry(entry: FoodEntry) -> None:
    """Save food entry to database and create health_event"""
    food_entry_id = None

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO food_entries
                (id, user_id, timestamp, photo_path, foods, total_calories, total_macros, meal_type, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(entry.id),  # Include the UUID from the entry
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
            food_entry_id = entry.id  # Use the entry.id since we're inserting it
            await conn.commit()

    logger.info(f"Saved food entry {entry.id} for user {entry.user_id}")

    # Create health event in background (non-blocking)
    if food_entry_id:
        asyncio.create_task(_create_food_health_event(entry, food_entry_id))


async def _create_food_health_event(entry: FoodEntry, food_entry_id: UUID):
    """
    Background task to create health event for food entry.

    This runs asynchronously after the main food_entry is saved, so it doesn't
    block the user-facing transaction. If event creation fails, it logs the error
    but doesn't affect the main flow.
    """
    try:
        from src.services.health_events import create_health_event

        metadata = {
            "meal_type": entry.meal_type,
            "total_calories": entry.total_calories,
            "total_macros": entry.total_macros.model_dump(),
            "foods": [f.model_dump() for f in entry.foods],
            "photo_path": entry.photo_path,
            "notes": entry.notes
        }

        await create_health_event(
            user_id=entry.user_id,
            event_type="meal",
            timestamp=entry.timestamp,
            metadata=metadata,
            source_table="food_entries",
            source_id=food_entry_id
        )
        logger.debug(f"Created health_event for food_entry {food_entry_id}")

    except Exception as e:
        logger.error(
            f"Failed to create health_event for food_entry {food_entry_id}",
            exc_info=True
        )


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
