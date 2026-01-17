"""
Health Event Ingestion Pipeline
Epic 009 - Phase 5: Event Timeline Foundation

This module provides the unified event ingestion pipeline for all health-related
activities. It consolidates events from multiple sources (food logs, sleep entries,
exercise, custom trackers, symptoms, mood) into a single temporal timeline.

Key Features:
- Unified event creation with JSONB metadata
- Event type validation
- Deduplication logic for idempotent migrations
- Temporal queries optimized for <50ms performance
- Background async processing support
"""
import logging
from typing import Any, Dict, Optional, Literal, List
from datetime import datetime
from uuid import UUID, uuid4
from src.db.connection import db
import json

logger = logging.getLogger(__name__)

# Type alias for supported event types
EventType = Literal[
    "meal",
    "sleep",
    "exercise",
    "symptom",
    "mood",
    "stress",
    "tracker",
    "custom"
]

# Set of valid event types for validation
VALID_EVENT_TYPES = {
    "meal",
    "sleep",
    "exercise",
    "symptom",
    "mood",
    "stress",
    "tracker",
    "custom"
}


async def create_health_event(
    user_id: str,
    event_type: EventType,
    timestamp: datetime,
    metadata: Dict[str, Any],
    source_table: Optional[str] = None,
    source_id: Optional[UUID] = None
) -> UUID:
    """
    Create a health event in the unified timeline.

    This is the core function for event ingestion. It validates the event type,
    stores metadata as JSONB, and creates a timestamped record in the health_events
    table.

    Args:
        user_id: Telegram user ID (references users.telegram_id)
        event_type: Type of event (meal, sleep, exercise, symptom, mood, stress, tracker, custom)
        timestamp: When the event occurred (should be UTC)
        metadata: Event-specific data (flexible JSONB schema per event type)
        source_table: Original table name for backfill tracking (e.g., 'food_entries')
        source_id: Original record UUID for backfill verification (enables idempotent migrations)

    Returns:
        UUID of the created health_event

    Raises:
        ValueError: If event_type is invalid or metadata is empty
        psycopg.DatabaseError: If database insertion fails

    Example:
        >>> await create_health_event(
        ...     user_id="123456789",
        ...     event_type="meal",
        ...     timestamp=datetime.now(),
        ...     metadata={
        ...         "meal_type": "lunch",
        ...         "total_calories": 650,
        ...         "total_macros": {"protein": 35, "carbs": 75, "fat": 18}
        ...     }
        ... )
    """
    # Validation: Event type
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(
            f"Invalid event_type '{event_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_EVENT_TYPES))}"
        )

    # Validation: Metadata cannot be empty
    if not metadata:
        raise ValueError("metadata cannot be empty")

    event_id = uuid4()

    try:
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO health_events
                    (id, user_id, event_type, timestamp, metadata, source_table, source_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        event_id,
                        user_id,
                        event_type,
                        timestamp,
                        json.dumps(metadata),
                        source_table,
                        source_id
                    )
                )
                await conn.commit()

        logger.info(
            f"Created health_event: {event_type} for user {user_id} "
            f"at {timestamp.isoformat()} (id: {event_id})"
        )
        return event_id

    except Exception as e:
        logger.error(
            f"Failed to create health_event: {event_type} for user {user_id}",
            exc_info=True
        )
        raise


async def get_health_events(
    user_id: str,
    start_date: datetime,
    end_date: datetime,
    event_types: Optional[List[EventType]] = None
) -> List[Dict[str, Any]]:
    """
    Query health events for a user within a date range.

    This function uses the optimized temporal indexes for fast queries.
    Target performance: <50ms for 30-day date ranges.

    Args:
        user_id: Telegram user ID
        start_date: Start of time range (inclusive)
        end_date: End of time range (inclusive)
        event_types: Optional filter by event types (e.g., ['meal', 'sleep'])

    Returns:
        List of health events sorted by timestamp DESC (most recent first)

    Example:
        >>> # Get all events in last 30 days
        >>> events = await get_health_events(
        ...     user_id="123",
        ...     start_date=datetime.now() - timedelta(days=30),
        ...     end_date=datetime.now()
        ... )
        >>>
        >>> # Get only meals in last week
        >>> meals = await get_health_events(
        ...     user_id="123",
        ...     start_date=datetime.now() - timedelta(days=7),
        ...     end_date=datetime.now(),
        ...     event_types=["meal"]
        ... )
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            if event_types:
                # Query with event type filter
                await cur.execute(
                    """
                    SELECT id, user_id, event_type, timestamp, metadata,
                           source_table, source_id, created_at
                    FROM health_events
                    WHERE user_id = %s
                      AND timestamp >= %s
                      AND timestamp <= %s
                      AND event_type = ANY(%s)
                    ORDER BY timestamp DESC
                    """,
                    (user_id, start_date, end_date, event_types)
                )
            else:
                # Query all event types
                await cur.execute(
                    """
                    SELECT id, user_id, event_type, timestamp, metadata,
                           source_table, source_id, created_at
                    FROM health_events
                    WHERE user_id = %s
                      AND timestamp >= %s
                      AND timestamp <= %s
                    ORDER BY timestamp DESC
                    """,
                    (user_id, start_date, end_date)
                )

            rows = await cur.fetchall()
            return [dict(row) for row in rows]


async def check_duplicate_event(
    source_table: str,
    source_id: UUID
) -> bool:
    """
    Check if an event already exists for a given source record.

    This function is used during historical migration to prevent duplicate
    events when the migration script is run multiple times (idempotent migrations).

    Uses the idx_health_events_source index for fast lookups.

    Args:
        source_table: Original table name (e.g., 'food_entries')
        source_id: Original record UUID

    Returns:
        True if event already exists, False otherwise

    Example:
        >>> # Check before migrating a food entry
        >>> if not await check_duplicate_event('food_entries', entry_id):
        ...     await create_health_event(...)  # Safe to create
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT COUNT(*) FROM health_events
                WHERE source_table = %s AND source_id = %s
                """,
                (source_table, source_id)
            )
            row = await cur.fetchone()
            count = row[0] if row else 0
            return count > 0


async def get_event_count_by_type(
    user_id: str,
    start_date: datetime,
    end_date: datetime
) -> Dict[str, int]:
    """
    Get count of events grouped by event_type for a user within a date range.

    Useful for dashboard summaries and analytics.

    Args:
        user_id: Telegram user ID
        start_date: Start of time range
        end_date: End of time range

    Returns:
        Dictionary mapping event_type to count
        Example: {"meal": 90, "sleep": 30, "tracker": 45}

    Example:
        >>> counts = await get_event_count_by_type(
        ...     user_id="123",
        ...     start_date=datetime.now() - timedelta(days=30),
        ...     end_date=datetime.now()
        ... )
        >>> print(f"Logged {counts['meal']} meals this month")
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT event_type, COUNT(*) as count
                FROM health_events
                WHERE user_id = %s
                  AND timestamp >= %s
                  AND timestamp <= %s
                GROUP BY event_type
                ORDER BY count DESC
                """,
                (user_id, start_date, end_date)
            )
            rows = await cur.fetchall()
            return {row["event_type"]: row["count"] for row in rows}


async def delete_health_event(event_id: UUID) -> bool:
    """
    Delete a health event by ID.

    Note: This is rarely needed as events are typically immutable.
    Use case: User corrections or data removal requests.

    Args:
        event_id: UUID of the health_event to delete

    Returns:
        True if event was deleted, False if not found

    Example:
        >>> deleted = await delete_health_event(event_id)
        >>> if deleted:
        ...     logger.info("Event deleted successfully")
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM health_events WHERE id = %s",
                (event_id,)
            )
            deleted_count = cur.rowcount
            await conn.commit()

            if deleted_count > 0:
                logger.info(f"Deleted health_event: {event_id}")
                return True
            else:
                logger.warning(f"Health_event not found for deletion: {event_id}")
                return False
