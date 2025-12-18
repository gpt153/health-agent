"""Integration tests for sleep quiz flow"""
import pytest
from datetime import datetime, time
from src.db.queries import save_sleep_entry, get_sleep_entries
from src.db.connection import db
from src.models.sleep import SleepEntry
from uuid import uuid4


@pytest.fixture(scope="module", autouse=True)
def event_loop():
    """Create event loop for async tests"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module", autouse=True)
async def init_db():
    """Initialize database pool for tests"""
    await db.init_pool()
    yield
    await db.close_pool()


@pytest.mark.asyncio
async def test_save_and_retrieve_sleep_entry(init_db):
    """Test saving sleep entry to database and retrieving it"""
    # Create test entry
    entry = SleepEntry(
        id=str(uuid4()),
        user_id="test_user_sleep_123",
        logged_at=datetime.now(),
        bedtime=time(22, 0),
        sleep_latency_minutes=15,
        wake_time=time(7, 0),
        total_sleep_hours=8.75,
        night_wakings=0,
        sleep_quality_rating=8,
        disruptions=[],
        phone_usage=False,
        phone_duration_minutes=None,
        alertness_rating=7
    )

    # Save to database
    await save_sleep_entry(entry)

    # Retrieve from database
    entries = await get_sleep_entries("test_user_sleep_123", days=1)

    # Verify
    assert len(entries) > 0
    assert entries[0]['sleep_quality_rating'] == 8
    assert entries[0]['total_sleep_hours'] == 8.75
    assert entries[0]['phone_usage'] is False


@pytest.mark.asyncio
async def test_save_sleep_entry_with_disruptions(init_db):
    """Test saving entry with multiple disruptions"""
    entry = SleepEntry(
        id=str(uuid4()),
        user_id="test_user_sleep_456",
        logged_at=datetime.now(),
        bedtime=time(23, 30),
        sleep_latency_minutes=45,
        wake_time=time(6, 15),
        total_sleep_hours=6.5,
        night_wakings=3,
        sleep_quality_rating=4,
        disruptions=["noise", "light", "stress"],
        phone_usage=True,
        phone_duration_minutes=45,
        alertness_rating=3
    )

    await save_sleep_entry(entry)

    entries = await get_sleep_entries("test_user_sleep_456", days=1)

    assert len(entries) > 0
    assert entries[0]['phone_usage'] is True
    assert entries[0]['phone_duration_minutes'] == 45


@pytest.mark.asyncio
async def test_get_sleep_entries_date_range(init_db):
    """Test retrieving entries within date range"""
    # Create entry for specific user
    entry = SleepEntry(
        id=str(uuid4()),
        user_id="test_user_sleep_range",
        logged_at=datetime.now(),
        bedtime=time(22, 0),
        sleep_latency_minutes=20,
        wake_time=time(7, 30),
        total_sleep_hours=9.0,
        night_wakings=1,
        sleep_quality_rating=9,
        disruptions=["dream"],
        phone_usage=False,
        phone_duration_minutes=None,
        alertness_rating=8
    )

    await save_sleep_entry(entry)

    # Retrieve last 7 days
    entries = await get_sleep_entries("test_user_sleep_range", days=7)

    assert len(entries) > 0
    # Should return entries sorted by logged_at DESC
    assert entries[0]['sleep_quality_rating'] == 9
