"""
Integration test for Issue #120: Sleep quiz save failures

Tests the race condition fix where concurrent user creation
could cause foreign key violations when saving sleep entries.
"""
import pytest
import asyncio
from uuid import uuid4
from datetime import time as time_type
from src.db.queries.user import create_user, user_exists
from src.db.queries.tracking import save_sleep_entry
from src.models.sleep import SleepEntry
from src.utils.datetime_helpers import now_utc
from src.db.connection import db


@pytest.fixture(scope="function")
async def db_connection():
    """Initialize database connection for tests"""
    await db.init_pool()
    yield db
    await db.close_pool()


@pytest.mark.asyncio
async def test_concurrent_user_creation_no_race_condition(db_connection):
    """
    Test that concurrent user creation doesn't cause race conditions.

    This simulates the scenario from Issue #120 where:
    1. Multiple processes try to create the same user
    2. One process attempts to save sleep entry
    3. Foreign key constraint should not fail

    Expected: All operations succeed, no foreign key violations.
    """
    test_user_id = f"test_race_{uuid4().hex[:8]}"

    try:
        # Simulate concurrent user creation (multiple processes)
        tasks = [
            create_user(test_user_id),
            create_user(test_user_id),
            create_user(test_user_id)
        ]
        await asyncio.gather(*tasks)

        # Verify user exists after concurrent creation
        assert await user_exists(test_user_id), "User should exist after creation"

        # Now attempt to save sleep entry (this would fail in old code)
        entry = SleepEntry(
            id=str(uuid4()),
            user_id=test_user_id,
            logged_at=now_utc(),
            bedtime=time_type(22, 0),
            sleep_latency_minutes=15,
            wake_time=time_type(7, 0),
            total_sleep_hours=8.5,
            night_wakings=0,
            sleep_quality_rating=8,
            disruptions=[],
            phone_usage=False,
            phone_duration_minutes=0,
            alertness_rating=8
        )

        # This should NOT raise a foreign key violation
        await save_sleep_entry(entry)

        # Verify entry was saved
        from src.db.queries.tracking import get_sleep_entries
        entries = await get_sleep_entries(test_user_id, days=1)
        assert len(entries) > 0, "Sleep entry should be saved"
        assert entries[0]['user_id'] == test_user_id

    finally:
        # Cleanup: delete test user (CASCADE will delete sleep entries)
        from src.db.connection import db
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM users WHERE telegram_id = %s",
                    (test_user_id,)
                )
                await conn.commit()


@pytest.mark.asyncio
async def test_sleep_quiz_with_new_user(db_connection):
    """
    Test sleep quiz flow with a brand new user (Issue #120 scenario).

    This simulates:
    1. User starts sleep quiz (user doesn't exist yet)
    2. create_user() is called
    3. User completes quiz
    4. save_sleep_entry() is called

    Expected: No foreign key violations, entry saves successfully.
    """
    test_user_id = f"test_new_{uuid4().hex[:8]}"

    try:
        # Verify user doesn't exist initially
        assert not await user_exists(test_user_id), "User should not exist initially"

        # Simulate quiz start: create user
        await create_user(test_user_id)

        # Verify user now exists
        assert await user_exists(test_user_id), "User should exist after creation"

        # Simulate quiz completion: save sleep entry
        entry = SleepEntry(
            id=str(uuid4()),
            user_id=test_user_id,
            logged_at=now_utc(),
            bedtime=time_type(23, 30),
            sleep_latency_minutes=20,
            wake_time=time_type(7, 30),
            total_sleep_hours=7.5,
            night_wakings=1,
            sleep_quality_rating=7,
            disruptions=["noise"],
            phone_usage=True,
            phone_duration_minutes=15,
            alertness_rating=7
        )

        # This should succeed without foreign key violation
        await save_sleep_entry(entry)

        # Verify entry was saved
        from src.db.queries.tracking import get_sleep_entries
        entries = await get_sleep_entries(test_user_id, days=1)
        assert len(entries) == 1, "Should have exactly one sleep entry"
        assert entries[0]['sleep_quality_rating'] == 7
        assert entries[0]['total_sleep_hours'] == 7.5

    finally:
        # Cleanup
        from src.db.connection import db
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM users WHERE telegram_id = %s",
                    (test_user_id,)
                )
                await conn.commit()


@pytest.mark.asyncio
async def test_create_user_idempotence(db_connection):
    """
    Test that create_user() is truly idempotent (can be called multiple times safely).

    This verifies the fix for Issue #120 where DO NOTHING was changed to DO UPDATE.
    """
    test_user_id = f"test_idem_{uuid4().hex[:8]}"

    try:
        # Call create_user multiple times
        await create_user(test_user_id)
        await create_user(test_user_id)
        await create_user(test_user_id)

        # Verify user exists
        assert await user_exists(test_user_id), "User should exist"

        # Verify only one user record exists
        from src.db.connection import db
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT COUNT(*) as count FROM users WHERE telegram_id = %s",
                    (test_user_id,)
                )
                result = await cur.fetchone()
                assert result['count'] == 1, "Should have exactly one user record"

    finally:
        # Cleanup
        from src.db.connection import db
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM users WHERE telegram_id = %s",
                    (test_user_id,)
                )
                await conn.commit()


@pytest.mark.asyncio
async def test_foreign_key_constraint_still_enforced(db_connection):
    """
    Verify that foreign key constraints are still properly enforced.

    This ensures our fix doesn't break database integrity.
    """
    non_existent_user = f"nonexistent_{uuid4().hex[:8]}"

    # Verify user doesn't exist
    assert not await user_exists(non_existent_user)

    # Attempt to save sleep entry for non-existent user should fail
    entry = SleepEntry(
        id=str(uuid4()),
        user_id=non_existent_user,
        logged_at=now_utc(),
        bedtime=time_type(22, 0),
        sleep_latency_minutes=10,
        wake_time=time_type(7, 0),
        total_sleep_hours=8.0,
        night_wakings=0,
        sleep_quality_rating=8,
        disruptions=[],
        phone_usage=False,
        phone_duration_minutes=0,
        alertness_rating=8
    )

    # This should raise a foreign key violation
    with pytest.raises(Exception) as exc_info:
        await save_sleep_entry(entry)

    # Verify it's a foreign key error
    error_msg = str(exc_info.value).lower()
    assert (
        'foreign key' in error_msg or
        'violates foreign key constraint' in error_msg
    ), f"Expected foreign key error, got: {exc_info.value}"
