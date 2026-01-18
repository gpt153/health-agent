# Phase 5 Implementation Plan: Event Timeline Foundation

**Epic:** Ultimate Memory System - Visual Food Memory & Pattern Detection
**Issue:** #106
**Estimated Time:** 8 hours
**Priority:** High

---

## 📊 Executive Summary

This phase creates a unified **health_events** table that serves as a temporal foundation for all user health activities. The system will ingest events from multiple sources (food logs, sleep entries, exercise, custom trackers, symptoms, mood) into a single timeline, enabling powerful pattern detection and correlation analysis.

**Key Insight:** By unifying all health events into a single temporal table with JSONB metadata, we enable cross-domain pattern detection (e.g., "poor sleep quality 3 hours after high-carb meals") without complex JOIN operations.

---

## 🏗️ Architecture Overview

### Current System
- **Siloed data storage:** `food_entries`, `sleep_entries`, `tracking_entries` exist independently
- **Limited correlation:** Difficult to find patterns across different health domains
- **No unified timeline:** Each system maintains its own temporal data

### Target System
- **Unified event stream:** Single `health_events` table with polymorphic event types
- **JSONB metadata:** Flexible schema per event type (meals store calories/macros, sleep stores quality/duration, etc.)
- **Temporal indexing:** Optimized for time-range queries (<50ms for 30-day windows)
- **Real-time ingestion:** Automatic event creation whenever users log any health data

### Data Flow
```
User Action (log food/sleep/exercise/tracker)
    ↓
Existing Service (save_food_entry, save_sleep_entry, etc.)
    ↓
[NEW] create_health_event() - Background async task
    ↓
health_events table
    ↓
[FUTURE] Pattern Detection Engine (Phase 6)
```

---

## 🗄️ Database Schema Design

### Migration: `migrations/021_health_events.sql`

#### Table: `health_events`

```sql
CREATE TABLE IF NOT EXISTS health_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    metadata JSONB NOT NULL,
    source_table VARCHAR(50),     -- 'food_entries', 'sleep_entries', etc.
    source_id UUID,               -- FK to original record (for backfill verification)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_event_type CHECK (
        event_type IN (
            'meal',
            'sleep',
            'exercise',
            'symptom',
            'mood',
            'stress',
            'tracker',
            'custom'
        )
    )
);
```

#### Indexes (Performance Critical)

**Requirement:** <50ms for 30-day temporal queries

```sql
-- Primary temporal query index (MOST IMPORTANT)
CREATE INDEX idx_health_events_user_time
ON health_events(user_id, timestamp DESC);

-- Event type filtering
CREATE INDEX idx_health_events_user_type_time
ON health_events(user_id, event_type, timestamp DESC);

-- JSONB metadata queries (GIN index with jsonb_path_ops for performance)
CREATE INDEX idx_health_events_metadata
ON health_events USING GIN(metadata jsonb_path_ops);

-- Backfill verification index
CREATE INDEX idx_health_events_source
ON health_events(source_table, source_id)
WHERE source_id IS NOT NULL;

-- Pattern detection queries (composite index)
CREATE INDEX idx_health_events_pattern_query
ON health_events(user_id, event_type, timestamp DESC)
INCLUDE (metadata);
```

**Index Strategy Rationale:**
- `idx_health_events_user_time`: Enables fast "last 30 days of all events" queries
- `idx_health_events_user_type_time`: Enables fast "last 30 days of meals" queries
- `idx_health_events_metadata`: Enables JSONB queries like "find all meals with >500 calories"
- `idx_health_events_source`: Prevents duplicate backfills during historical migration
- `idx_health_events_pattern_query`: Optimized for Phase 6 pattern detection (INCLUDE clause avoids table lookups)

---

## 📦 Event Metadata Schemas

### Event Type: `meal`
```json
{
  "meal_type": "lunch",
  "total_calories": 650,
  "total_macros": {
    "protein": 35,
    "carbs": 75,
    "fat": 18
  },
  "foods": [
    {
      "name": "Chicken breast",
      "quantity": "200g",
      "calories": 330,
      "macros": {"protein": 31, "carbs": 0, "fat": 7}
    }
  ],
  "photo_path": "/path/to/photo.jpg"
}
```

### Event Type: `sleep`
```json
{
  "bedtime": "23:00",
  "wake_time": "07:30",
  "total_sleep_hours": 7.5,
  "sleep_quality_rating": 8,
  "night_wakings": 1,
  "disruptions": ["noise", "bathroom"],
  "phone_usage": true,
  "phone_duration_minutes": 15,
  "alertness_rating": 7
}
```

### Event Type: `exercise`
```json
{
  "activity_type": "running",
  "duration_minutes": 30,
  "intensity": "moderate",
  "notes": "Morning jog, felt great"
}
```

### Event Type: `tracker` (Custom Tracking)
```json
{
  "category_name": "Blood Pressure",
  "category_id": "uuid-here",
  "data": {
    "systolic": 120,
    "diastolic": 80,
    "heart_rate": 72
  }
}
```

### Event Type: `symptom`
```json
{
  "symptom_type": "headache",
  "severity": 6,
  "duration_minutes": 120,
  "notes": "Started after lunch"
}
```

### Event Type: `mood`
```json
{
  "mood_rating": 7,
  "emotions": ["happy", "energetic"],
  "notes": "Great day at work"
}
```

---

## 🔧 Event Ingestion Pipeline

### File: `src/services/health_events.py`

#### Function: `create_health_event()`

```python
"""
Health event ingestion pipeline
Handles creation of unified health events from various sources
"""
import logging
from typing import Any, Dict, Optional, Literal
from datetime import datetime
from uuid import UUID, uuid4
from src.db.connection import db
import json

logger = logging.getLogger(__name__)

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

async def create_health_event(
    user_id: str,
    event_type: EventType,
    timestamp: datetime,
    metadata: Dict[str, Any],
    source_table: Optional[str] = None,
    source_id: Optional[UUID] = None
) -> UUID:
    """
    Create a health event in the unified timeline

    Args:
        user_id: Telegram user ID
        event_type: Type of event (meal, sleep, exercise, etc.)
        timestamp: When the event occurred
        metadata: Event-specific data (flexible JSONB)
        source_table: Original table name (for backfill tracking)
        source_id: Original record UUID (for backfill verification)

    Returns:
        UUID of created health_event

    Raises:
        ValueError: If event_type is invalid
        psycopg.DatabaseError: If insertion fails
    """
    event_id = uuid4()

    # Validation
    valid_types = {
        "meal", "sleep", "exercise", "symptom",
        "mood", "stress", "tracker", "custom"
    }
    if event_type not in valid_types:
        raise ValueError(
            f"Invalid event_type '{event_type}'. "
            f"Must be one of: {', '.join(valid_types)}"
        )

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
            f"at {timestamp.isoformat()}"
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
    event_types: Optional[list[EventType]] = None
) -> list[dict]:
    """
    Query health events for a user within a date range

    Args:
        user_id: Telegram user ID
        start_date: Start of time range
        end_date: End of time range
        event_types: Optional filter by event types

    Returns:
        List of health events sorted by timestamp DESC
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            if event_types:
                await cur.execute(
                    """
                    SELECT id, user_id, event_type, timestamp, metadata, created_at
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
                await cur.execute(
                    """
                    SELECT id, user_id, event_type, timestamp, metadata, created_at
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
    Check if an event already exists for a given source record
    Used during historical migration to prevent duplicates

    Returns:
        True if event already exists, False otherwise
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
            return row[0] > 0
```

---

## 🔄 Historical Data Migration

### File: `scripts/migrate_historical_events.py`

#### Strategy
- **Idempotent:** Can run multiple times safely (checks `source_id` before inserting)
- **Batch processing:** Process in chunks of 1000 records to avoid memory issues
- **Progress tracking:** Log progress every 100 records
- **Rollback safety:** Uses transactions per batch

#### Implementation

```python
"""
Historical data migration script
Backfills health_events table from existing data sources
"""
import asyncio
import logging
from datetime import datetime
from uuid import UUID
from src.db.connection import db
from src.services.health_events import create_health_event, check_duplicate_event
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BATCH_SIZE = 1000


async def migrate_food_entries():
    """Migrate all food_entries to health_events"""
    logger.info("Starting food_entries migration...")

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Get total count
            await cur.execute("SELECT COUNT(*) FROM food_entries")
            total = (await cur.fetchone())[0]
            logger.info(f"Total food_entries to migrate: {total}")

            # Process in batches
            offset = 0
            migrated = 0
            skipped = 0

            while offset < total:
                await cur.execute(
                    """
                    SELECT id, user_id, timestamp, photo_path, foods,
                           total_calories, total_macros, meal_type, notes
                    FROM food_entries
                    ORDER BY timestamp ASC
                    LIMIT %s OFFSET %s
                    """,
                    (BATCH_SIZE, offset)
                )

                rows = await cur.fetchall()

                for row in rows:
                    entry_id = row["id"]

                    # Check if already migrated
                    if await check_duplicate_event("food_entries", entry_id):
                        skipped += 1
                        continue

                    # Build metadata
                    metadata = {
                        "meal_type": row["meal_type"],
                        "total_calories": row["total_calories"],
                        "total_macros": row["total_macros"],
                        "foods": row["foods"],
                        "photo_path": row["photo_path"],
                        "notes": row["notes"]
                    }

                    # Create health event
                    await create_health_event(
                        user_id=row["user_id"],
                        event_type="meal",
                        timestamp=row["timestamp"],
                        metadata=metadata,
                        source_table="food_entries",
                        source_id=entry_id
                    )
                    migrated += 1

                    if migrated % 100 == 0:
                        logger.info(f"Migrated {migrated}/{total} food entries...")

                offset += BATCH_SIZE

            logger.info(
                f"Food entries migration complete: "
                f"{migrated} migrated, {skipped} skipped (duplicates)"
            )


async def migrate_sleep_entries():
    """Migrate all sleep_entries to health_events"""
    logger.info("Starting sleep_entries migration...")

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM sleep_entries")
            total = (await cur.fetchone())[0]
            logger.info(f"Total sleep_entries to migrate: {total}")

            offset = 0
            migrated = 0
            skipped = 0

            while offset < total:
                await cur.execute(
                    """
                    SELECT id, user_id, logged_at, bedtime, sleep_latency_minutes,
                           wake_time, total_sleep_hours, night_wakings,
                           sleep_quality_rating, disruptions, phone_usage,
                           phone_duration_minutes, alertness_rating
                    FROM sleep_entries
                    ORDER BY logged_at ASC
                    LIMIT %s OFFSET %s
                    """,
                    (BATCH_SIZE, offset)
                )

                rows = await cur.fetchall()

                for row in rows:
                    entry_id = row["id"]

                    if await check_duplicate_event("sleep_entries", entry_id):
                        skipped += 1
                        continue

                    metadata = {
                        "bedtime": str(row["bedtime"]),
                        "wake_time": str(row["wake_time"]),
                        "sleep_latency_minutes": row["sleep_latency_minutes"],
                        "total_sleep_hours": row["total_sleep_hours"],
                        "night_wakings": row["night_wakings"],
                        "sleep_quality_rating": row["sleep_quality_rating"],
                        "disruptions": row["disruptions"],
                        "phone_usage": row["phone_usage"],
                        "phone_duration_minutes": row["phone_duration_minutes"],
                        "alertness_rating": row["alertness_rating"]
                    }

                    await create_health_event(
                        user_id=row["user_id"],
                        event_type="sleep",
                        timestamp=row["logged_at"],
                        metadata=metadata,
                        source_table="sleep_entries",
                        source_id=entry_id
                    )
                    migrated += 1

                    if migrated % 100 == 0:
                        logger.info(f"Migrated {migrated}/{total} sleep entries...")

                offset += BATCH_SIZE

            logger.info(
                f"Sleep entries migration complete: "
                f"{migrated} migrated, {skipped} skipped"
            )


async def migrate_tracking_entries():
    """Migrate all tracking_entries to health_events"""
    logger.info("Starting tracking_entries migration...")

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM tracking_entries")
            total = (await cur.fetchone())[0]
            logger.info(f"Total tracking_entries to migrate: {total}")

            offset = 0
            migrated = 0
            skipped = 0

            while offset < total:
                await cur.execute(
                    """
                    SELECT te.id, te.user_id, te.timestamp, te.data, te.notes,
                           tc.name as category_name, tc.id as category_id
                    FROM tracking_entries te
                    JOIN tracking_categories tc ON te.category_id = tc.id
                    ORDER BY te.timestamp ASC
                    LIMIT %s OFFSET %s
                    """,
                    (BATCH_SIZE, offset)
                )

                rows = await cur.fetchall()

                for row in rows:
                    entry_id = row["id"]

                    if await check_duplicate_event("tracking_entries", entry_id):
                        skipped += 1
                        continue

                    metadata = {
                        "category_name": row["category_name"],
                        "category_id": str(row["category_id"]),
                        "data": row["data"],
                        "notes": row["notes"]
                    }

                    await create_health_event(
                        user_id=row["user_id"],
                        event_type="tracker",
                        timestamp=row["timestamp"],
                        metadata=metadata,
                        source_table="tracking_entries",
                        source_id=entry_id
                    )
                    migrated += 1

                    if migrated % 100 == 0:
                        logger.info(f"Migrated {migrated}/{total} tracker entries...")

                offset += BATCH_SIZE

            logger.info(
                f"Tracker entries migration complete: "
                f"{migrated} migrated, {skipped} skipped"
            )


async def main():
    """Run all migrations"""
    logger.info("=" * 60)
    logger.info("HEALTH EVENTS HISTORICAL MIGRATION")
    logger.info("=" * 60)

    # Initialize database
    from src.db.connection import db as database
    await database.init_pool()

    try:
        # Run migrations in order
        await migrate_food_entries()
        await migrate_sleep_entries()
        await migrate_tracking_entries()

        logger.info("=" * 60)
        logger.info("MIGRATION COMPLETE")
        logger.info("=" * 60)

    finally:
        await database.close_pool()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## ⚡ Real-time Event Hooks

### Strategy
- **Async background tasks:** Event creation happens in background to avoid blocking user responses
- **Fire-and-forget pattern:** Main transaction commits first, then event is created
- **Error resilience:** If event creation fails, log error but don't block main flow

### File: `src/db/queries/food.py` (Update existing)

```python
# Add to existing file
from src.services.health_events import create_health_event
import asyncio

async def save_food_entry(entry: FoodEntry) -> None:
    """Save food entry to database"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO food_entries
                (user_id, timestamp, photo_path, foods, total_calories, total_macros, meal_type, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
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
            food_entry_id = (await cur.fetchone())["id"]
            await conn.commit()

    logger.info(f"Saved food entry for user {entry.user_id}")

    # Create health event in background (async)
    asyncio.create_task(_create_food_health_event(entry, food_entry_id))


async def _create_food_health_event(entry: FoodEntry, food_entry_id: UUID):
    """Background task to create health event for food entry"""
    try:
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
    except Exception as e:
        logger.error(
            f"Failed to create health_event for food_entry {food_entry_id}",
            exc_info=True
        )
```

### File: `src/db/queries/tracking.py` (Update existing)

```python
# Add to existing file
from src.services.health_events import create_health_event
import asyncio

async def save_tracking_entry(entry: TrackerEntry) -> None:
    """Save tracking entry"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # First get category name
            await cur.execute(
                "SELECT name FROM tracking_categories WHERE id = %s",
                (entry.category_id,)
            )
            category_row = await cur.fetchone()
            category_name = category_row["name"] if category_row else "Unknown"

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

    # Create health event in background
    asyncio.create_task(_create_tracker_health_event(entry, category_name))


async def _create_tracker_health_event(entry: TrackerEntry, category_name: str):
    """Background task to create health event for tracker entry"""
    try:
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
    except Exception as e:
        logger.error(
            f"Failed to create health_event for tracking_entry {entry.id}",
            exc_info=True
        )


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
                    str(entry.bedtime),
                    entry.sleep_latency_minutes,
                    str(entry.wake_time),
                    entry.total_sleep_hours,
                    entry.night_wakings,
                    entry.sleep_quality_rating,
                    json.dumps(entry.disruptions),
                    entry.phone_usage,
                    entry.phone_duration_minutes,
                    entry.alertness_rating
                )
            )
            await conn.commit()

    logger.info(f"Saved sleep entry for user {entry.user_id}")

    # Create health event in background
    asyncio.create_task(_create_sleep_health_event(entry))


async def _create_sleep_health_event(entry: SleepEntry):
    """Background task to create health event for sleep entry"""
    try:
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

        await create_health_event(
            user_id=entry.user_id,
            event_type="sleep",
            timestamp=entry.logged_at,
            metadata=metadata,
            source_table="sleep_entries",
            source_id=UUID(entry.id)
        )
    except Exception as e:
        logger.error(
            f"Failed to create health_event for sleep_entry {entry.id}",
            exc_info=True
        )
```

---

## ✅ Testing Strategy

### Unit Tests: `tests/unit/test_health_events.py`

```python
import pytest
from datetime import datetime
from uuid import uuid4
from src.services.health_events import (
    create_health_event,
    get_health_events,
    check_duplicate_event
)

@pytest.mark.asyncio
async def test_create_meal_event():
    """Test creating a meal health event"""
    user_id = "test_user_123"
    timestamp = datetime.now()
    metadata = {
        "meal_type": "lunch",
        "total_calories": 500,
        "total_macros": {"protein": 30, "carbs": 50, "fat": 15}
    }

    event_id = await create_health_event(
        user_id=user_id,
        event_type="meal",
        timestamp=timestamp,
        metadata=metadata
    )

    assert event_id is not None


@pytest.mark.asyncio
async def test_invalid_event_type():
    """Test that invalid event types raise ValueError"""
    with pytest.raises(ValueError, match="Invalid event_type"):
        await create_health_event(
            user_id="test_user",
            event_type="invalid_type",
            timestamp=datetime.now(),
            metadata={}
        )


@pytest.mark.asyncio
async def test_get_health_events_filter():
    """Test filtering events by type"""
    user_id = "test_user_456"
    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 31)

    # Create multiple event types
    await create_health_event(
        user_id, "meal", datetime(2024, 1, 15), {"calories": 300}
    )
    await create_health_event(
        user_id, "sleep", datetime(2024, 1, 16), {"hours": 7}
    )

    # Query only meals
    meals = await get_health_events(
        user_id, start, end, event_types=["meal"]
    )

    assert len(meals) >= 1
    assert all(e["event_type"] == "meal" for e in meals)


@pytest.mark.asyncio
async def test_duplicate_prevention():
    """Test that duplicate events are detected"""
    source_id = uuid4()

    # Create first event
    await create_health_event(
        user_id="test_user",
        event_type="meal",
        timestamp=datetime.now(),
        metadata={},
        source_table="food_entries",
        source_id=source_id
    )

    # Check duplicate
    is_duplicate = await check_duplicate_event("food_entries", source_id)
    assert is_duplicate is True
```

### Integration Tests: `tests/integration/test_event_hooks.py`

```python
import pytest
from datetime import datetime
from src.models.food import FoodEntry, FoodItem, FoodMacros
from src.db.queries.food import save_food_entry
from src.services.health_events import get_health_events

@pytest.mark.asyncio
async def test_food_entry_creates_health_event():
    """Test that saving a food entry automatically creates a health event"""
    user_id = "test_user_789"

    # Create food entry
    entry = FoodEntry(
        user_id=user_id,
        timestamp=datetime.now(),
        foods=[
            FoodItem(
                name="Apple",
                quantity="1 medium",
                calories=95,
                macros=FoodMacros(protein=0.5, carbs=25, fat=0.3)
            )
        ],
        total_calories=95,
        total_macros=FoodMacros(protein=0.5, carbs=25, fat=0.3),
        meal_type="snack"
    )

    await save_food_entry(entry)

    # Wait for background task
    await asyncio.sleep(0.5)

    # Verify health event was created
    events = await get_health_events(
        user_id,
        start_date=entry.timestamp,
        end_date=entry.timestamp,
        event_types=["meal"]
    )

    assert len(events) >= 1
    event = events[0]
    assert event["event_type"] == "meal"
    assert event["metadata"]["total_calories"] == 95
```

### Performance Tests: `tests/performance/test_temporal_queries.py`

```python
import pytest
import time
from datetime import datetime, timedelta
from src.services.health_events import create_health_event, get_health_events

@pytest.mark.asyncio
async def test_30_day_query_performance():
    """Test that 30-day queries complete in <50ms"""
    user_id = "perf_test_user"

    # Create 100 events over 30 days
    start = datetime.now() - timedelta(days=30)
    for i in range(100):
        timestamp = start + timedelta(hours=i * 7)
        await create_health_event(
            user_id=user_id,
            event_type="meal",
            timestamp=timestamp,
            metadata={"calories": 500 + i}
        )

    # Measure query time
    query_start = time.perf_counter()
    events = await get_health_events(
        user_id,
        start_date=start,
        end_date=datetime.now()
    )
    query_time_ms = (time.perf_counter() - query_start) * 1000

    assert len(events) >= 100
    assert query_time_ms < 50, f"Query took {query_time_ms:.2f}ms (target: <50ms)"
```

---

## 📋 Implementation Checklist

### Phase 1: Database Migration (2h)
- [ ] Create `migrations/021_health_events.sql`
- [ ] Define `health_events` table with all columns
- [ ] Add CHECK constraint for valid event_types
- [ ] Create all 5 indexes (temporal, type, metadata, source, pattern)
- [ ] Add table and column comments
- [ ] Run migration on local database
- [ ] Verify indexes with `EXPLAIN ANALYZE`

### Phase 2: Event Ingestion Pipeline (3h)
- [ ] Create `src/services/health_events.py`
- [ ] Implement `create_health_event()` function
- [ ] Implement `get_health_events()` function
- [ ] Implement `check_duplicate_event()` function
- [ ] Add comprehensive logging
- [ ] Add error handling for all database operations
- [ ] Write unit tests for all functions
- [ ] Test validation logic (invalid event types, etc.)

### Phase 3: Historical Data Migration (1h)
- [ ] Create `scripts/migrate_historical_events.py`
- [ ] Implement `migrate_food_entries()`
- [ ] Implement `migrate_sleep_entries()`
- [ ] Implement `migrate_tracking_entries()`
- [ ] Add batch processing (chunks of 1000)
- [ ] Add progress logging (every 100 records)
- [ ] Add duplicate prevention checks
- [ ] Run migration on local database
- [ ] Verify all historical data migrated

### Phase 4: Real-time Event Hooks (2h)
- [ ] Update `src/db/queries/food.py` - add event hook to `save_food_entry()`
- [ ] Update `src/db/queries/tracking.py` - add event hook to `save_sleep_entry()`
- [ ] Update `src/db/queries/tracking.py` - add event hook to `save_tracking_entry()`
- [ ] Implement background task pattern with `asyncio.create_task()`
- [ ] Add error handling for background tasks
- [ ] Test event creation doesn't block main flow
- [ ] Write integration tests for all hooks
- [ ] Verify events are created after new logs

### Phase 5: Testing & Validation (30min)
- [ ] Run all unit tests (`pytest tests/unit/test_health_events.py`)
- [ ] Run all integration tests (`pytest tests/integration/test_event_hooks.py`)
- [ ] Run performance tests (verify <50ms for 30-day queries)
- [ ] Test with real user data (create food/sleep/tracker entries)
- [ ] Verify no performance regression in existing flows
- [ ] Check database size impact (health_events should be ~2x total entries)

### Phase 6: Documentation & Cleanup (30min)
- [ ] Add docstrings to all new functions
- [ ] Update README if needed
- [ ] Remove any TODO comments
- [ ] Remove any placeholder code
- [ ] Verify no print statements (use logger instead)
- [ ] Run code formatter (black/ruff)
- [ ] Final code review

---

## 🚀 Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| 30-day temporal query | <50ms | `EXPLAIN ANALYZE` on `get_health_events()` |
| Event creation | <10ms | Time `create_health_event()` |
| Historical migration | <5min for 10k events | Script execution time |
| Storage overhead | <2x original tables | Database size comparison |

---

## 🔗 Dependencies & Blockers

### Dependencies
- **None** - This phase is fully independent

### Blocks
- **Phase 6: Pattern Detection Engine** - Cannot implement pattern detection without unified event timeline

---

## 🎯 Success Criteria

- ✅ `health_events` table created with proper indexes
- ✅ All 8 event types supported (meal, sleep, exercise, symptom, mood, stress, tracker, custom)
- ✅ Historical data migrated successfully (food_entries, sleep_entries, tracking_entries)
- ✅ Real-time event creation working for all logging functions
- ✅ Temporal queries performant (<50ms for 30-day range)
- ✅ **NO placeholders or TODOs in production code**
- ✅ **NO mocks** - All code is production-ready
- ✅ Comprehensive test coverage (unit + integration + performance)
- ✅ Idempotent migration (can run multiple times safely)

---

## 🔮 Future Enhancements (Post-Phase 5)

These are **OUT OF SCOPE** for Phase 5 but good to document:

1. **Event Deletion/Archival** - Currently events are never deleted; might need archival strategy for users with years of data
2. **Event Updates** - Currently immutable; might need to support corrections/updates
3. **Event Aggregations** - Pre-computed aggregations (daily calories, weekly sleep avg) for performance
4. **Real-time Event Streaming** - WebSocket/SSE for live event feed
5. **Event Search** - Full-text search across event metadata
6. **Event Export** - Export user's complete event timeline (CSV, JSON)

---

## 📊 Database Size Estimation

Assuming:
- Average user: 3 meals/day, 1 sleep/day, 2 trackers/day = 6 events/day
- JSONB metadata: ~500 bytes avg per event
- 100 active users
- 30 days of data

**Estimated size:**
```
100 users × 6 events/day × 30 days × 500 bytes = 9 MB
```

**With indexes (~3x table size):** ~27 MB

This is negligible for Postgres - no storage concerns.

---

## 🛡️ Error Handling Strategy

### Database Errors
- **Duplicate key violations:** Log warning, continue (idempotent migration)
- **Connection errors:** Retry up to 3 times with exponential backoff
- **Constraint violations:** Raise immediately (indicates data quality issue)

### Background Task Errors
- **Event creation fails:** Log error, DO NOT block main transaction
- **Partial migration failures:** Continue processing, log all failures at end

### Validation Errors
- **Invalid event_type:** Raise `ValueError` immediately
- **Missing required fields:** Raise `ValueError` with clear message
- **Invalid JSONB:** Raise `psycopg.DatabaseError`

---

## 📝 Migration Rollback Plan

If Phase 5 needs to be rolled back:

```sql
-- Drop table (cascades to all dependent objects)
DROP TABLE IF EXISTS health_events CASCADE;

-- Verify rollback
SELECT table_name FROM information_schema.tables
WHERE table_name = 'health_events';
-- Should return 0 rows
```

**Data Safety:** Original tables (`food_entries`, `sleep_entries`, `tracking_entries`) are NEVER modified, so rollback is safe.

---

## 🎓 Key Design Decisions

### Why JSONB for metadata?
- **Flexibility:** Each event type has different fields (meals have calories, sleep has quality rating)
- **Schema evolution:** Can add new fields without migrations
- **Query performance:** GIN indexes enable fast JSONB queries
- **Storage efficiency:** Postgres compresses JSONB efficiently

### Why keep source_table + source_id?
- **Backfill verification:** Prevents duplicate events during re-runs
- **Data lineage:** Can trace health_event back to original record
- **Debugging:** Easy to verify event was created from correct source

### Why background tasks for real-time hooks?
- **Performance:** Don't block user-facing transactions
- **Resilience:** Main flow succeeds even if event creation fails
- **Scalability:** Event creation can be moved to job queue later

### Why separate migration script instead of trigger?
- **Control:** Can run migration on schedule, monitor progress
- **Testing:** Easier to test migration in isolation
- **Performance:** Batch processing faster than trigger-per-row
- **Idempotency:** Script can be safely re-run; triggers can't

---

## 🏁 Ready for Implementation

This plan provides:
- ✅ Complete database schema with performance-optimized indexes
- ✅ Production-ready event ingestion pipeline
- ✅ Idempotent historical migration script
- ✅ Real-time event hooks with error resilience
- ✅ Comprehensive testing strategy
- ✅ Clear success criteria
- ✅ Performance targets with measurement plan

**Estimated Total Time:** 8 hours

**Recommended Implementation Order:**
1. Database migration (verify indexes with EXPLAIN)
2. Event ingestion pipeline (test thoroughly)
3. Historical migration (run on local data first)
4. Real-time hooks (test async behavior)
5. Testing & validation (performance critical)

Let's build this! 🚀
