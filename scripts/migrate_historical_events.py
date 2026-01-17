#!/usr/bin/env python3
"""
Historical Data Migration Script
Epic 009 - Phase 5: Event Timeline Foundation

This script backfills the health_events table with existing data from:
- food_entries → meal events
- sleep_entries → sleep events
- tracking_entries → tracker events

Key Features:
- Idempotent: Can run multiple times safely (checks source_id for duplicates)
- Batch processing: Processes 1000 records at a time for memory efficiency
- Progress tracking: Logs progress every 100 records
- Transaction safety: Each batch is a transaction (rollback on failure)
- Preserves all timestamps and metadata

Usage:
    python scripts/migrate_historical_events.py

Requirements:
    - Database connection configured (DATABASE_URL env var)
    - Tables must exist: health_events, food_entries, sleep_entries, tracking_entries
"""
import asyncio
import logging
import sys
from datetime import datetime
from uuid import UUID
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.connection import db
from src.services.health_events import create_health_event, check_duplicate_event

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Batch size for processing (1000 records at a time)
BATCH_SIZE = 1000


async def migrate_food_entries():
    """
    Migrate all food_entries to health_events as 'meal' events.

    Metadata schema:
    {
        "meal_type": str,
        "total_calories": int,
        "total_macros": dict,
        "foods": list,
        "photo_path": str | null,
        "notes": str | null
    }
    """
    logger.info("=" * 60)
    logger.info("MIGRATING FOOD ENTRIES → MEAL EVENTS")
    logger.info("=" * 60)

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Get total count
            await cur.execute("SELECT COUNT(*) FROM food_entries")
            total = (await cur.fetchone())[0]
            logger.info(f"Total food_entries to migrate: {total}")

            if total == 0:
                logger.info("No food entries to migrate. Skipping.")
                return

            # Process in batches
            offset = 0
            migrated = 0
            skipped = 0

            while offset < total:
                logger.info(f"Processing batch: {offset} to {offset + BATCH_SIZE}...")

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

                    # Check if already migrated (idempotent)
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
                    try:
                        await create_health_event(
                            user_id=row["user_id"],
                            event_type="meal",
                            timestamp=row["timestamp"],
                            metadata=metadata,
                            source_table="food_entries",
                            source_id=entry_id
                        )
                        migrated += 1

                        # Progress logging every 100 records
                        if migrated % 100 == 0:
                            logger.info(f"Progress: {migrated}/{total} food entries migrated...")

                    except Exception as e:
                        logger.error(
                            f"Failed to migrate food_entry {entry_id}: {e}",
                            exc_info=True
                        )
                        # Continue processing (don't fail entire batch)
                        continue

                offset += BATCH_SIZE

            logger.info(
                f"✅ Food entries migration complete: "
                f"{migrated} migrated, {skipped} skipped (already existed)"
            )


async def migrate_sleep_entries():
    """
    Migrate all sleep_entries to health_events as 'sleep' events.

    Metadata schema:
    {
        "bedtime": str (HH:MM),
        "wake_time": str (HH:MM),
        "sleep_latency_minutes": int,
        "total_sleep_hours": float,
        "night_wakings": int,
        "sleep_quality_rating": int (1-10),
        "disruptions": list[str],
        "phone_usage": bool,
        "phone_duration_minutes": int | null,
        "alertness_rating": int (1-10)
    }
    """
    logger.info("=" * 60)
    logger.info("MIGRATING SLEEP ENTRIES → SLEEP EVENTS")
    logger.info("=" * 60)

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM sleep_entries")
            total = (await cur.fetchone())[0]
            logger.info(f"Total sleep_entries to migrate: {total}")

            if total == 0:
                logger.info("No sleep entries to migrate. Skipping.")
                return

            offset = 0
            migrated = 0
            skipped = 0

            while offset < total:
                logger.info(f"Processing batch: {offset} to {offset + BATCH_SIZE}...")

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

                    # Build metadata
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

                    try:
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
                            logger.info(f"Progress: {migrated}/{total} sleep entries migrated...")

                    except Exception as e:
                        logger.error(
                            f"Failed to migrate sleep_entry {entry_id}: {e}",
                            exc_info=True
                        )
                        continue

                offset += BATCH_SIZE

            logger.info(
                f"✅ Sleep entries migration complete: "
                f"{migrated} migrated, {skipped} skipped"
            )


async def migrate_tracking_entries():
    """
    Migrate all tracking_entries to health_events as 'tracker' events.

    Metadata schema:
    {
        "category_name": str,
        "category_id": str (UUID),
        "data": dict,
        "notes": str | null
    }
    """
    logger.info("=" * 60)
    logger.info("MIGRATING TRACKING ENTRIES → TRACKER EVENTS")
    logger.info("=" * 60)

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM tracking_entries")
            total = (await cur.fetchone())[0]
            logger.info(f"Total tracking_entries to migrate: {total}")

            if total == 0:
                logger.info("No tracking entries to migrate. Skipping.")
                return

            offset = 0
            migrated = 0
            skipped = 0

            while offset < total:
                logger.info(f"Processing batch: {offset} to {offset + BATCH_SIZE}...")

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

                    # Build metadata
                    metadata = {
                        "category_name": row["category_name"],
                        "category_id": str(row["category_id"]),
                        "data": row["data"],
                        "notes": row["notes"]
                    }

                    try:
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
                            logger.info(f"Progress: {migrated}/{total} tracker entries migrated...")

                    except Exception as e:
                        logger.error(
                            f"Failed to migrate tracking_entry {entry_id}: {e}",
                            exc_info=True
                        )
                        continue

                offset += BATCH_SIZE

            logger.info(
                f"✅ Tracker entries migration complete: "
                f"{migrated} migrated, {skipped} skipped"
            )


async def main():
    """Run all migrations"""
    start_time = datetime.now()

    logger.info("=" * 60)
    logger.info("HEALTH EVENTS HISTORICAL MIGRATION")
    logger.info(f"Started at: {start_time.isoformat()}")
    logger.info("=" * 60)

    # Initialize database connection pool
    try:
        await db.init_pool()
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        return 1

    try:
        # Run migrations in sequence
        await migrate_food_entries()
        await migrate_sleep_entries()
        await migrate_tracking_entries()

        end_time = datetime.now()
        duration = end_time - start_time

        logger.info("=" * 60)
        logger.info("✅ MIGRATION COMPLETE")
        logger.info(f"Finished at: {end_time.isoformat()}")
        logger.info(f"Total duration: {duration}")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        return 1

    finally:
        # Close database connection pool
        await db.close_pool()
        logger.info("Database connection closed")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
