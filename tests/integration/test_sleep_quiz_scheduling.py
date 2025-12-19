"""Integration tests for sleep quiz auto-scheduling"""
import pytest
from datetime import datetime, time
from src.db.queries import (
    save_sleep_quiz_settings,
    get_sleep_quiz_settings,
    save_sleep_quiz_submission,
    get_submission_patterns,
)
from src.db.connection import db
from src.models.sleep_settings import SleepQuizSettings, SleepQuizSubmission
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
async def test_save_and_retrieve_settings(init_db):
    """Test saving and retrieving sleep quiz settings"""
    settings = SleepQuizSettings(
        user_id="test_user_settings_123",
        enabled=True,
        preferred_time=time(7, 30),
        timezone="Europe/Stockholm",
        language_code="sv"
    )

    await save_sleep_quiz_settings(settings)

    # Retrieve
    retrieved = await get_sleep_quiz_settings("test_user_settings_123")

    assert retrieved is not None
    assert retrieved['enabled'] is True
    assert retrieved['timezone'] == "Europe/Stockholm"
    assert retrieved['language_code'] == "sv"


@pytest.mark.asyncio
async def test_update_existing_settings(init_db):
    """Test updating existing settings (upsert)"""
    user_id = "test_user_update_456"

    # Create initial settings
    settings1 = SleepQuizSettings(
        user_id=user_id,
        enabled=True,
        preferred_time=time(7, 0),
        timezone="UTC",
        language_code="en"
    )
    await save_sleep_quiz_settings(settings1)

    # Update settings
    settings2 = SleepQuizSettings(
        user_id=user_id,
        enabled=False,
        preferred_time=time(8, 30),
        timezone="America/New_York",
        language_code="es"
    )
    await save_sleep_quiz_settings(settings2)

    # Retrieve
    retrieved = await get_sleep_quiz_settings(user_id)

    assert retrieved['enabled'] is False
    assert retrieved['timezone'] == "America/New_York"
    assert retrieved['language_code'] == "es"


@pytest.mark.asyncio
async def test_save_submission_pattern(init_db):
    """Test saving quiz submission for pattern learning"""
    now = datetime.now()
    scheduled = now.replace(hour=7, minute=0, second=0, microsecond=0)

    submission = SleepQuizSubmission(
        id=str(uuid4()),
        user_id="test_user_pattern_789",
        scheduled_time=scheduled,
        submitted_at=now,
        response_delay_minutes=15
    )

    await save_sleep_quiz_submission(submission)

    # Retrieve patterns
    patterns = await get_submission_patterns("test_user_pattern_789", days=1)

    assert len(patterns) > 0
    assert patterns[0]['response_delay_minutes'] == 15


@pytest.mark.asyncio
async def test_calculate_average_delay(init_db):
    """Test calculating average submission delay"""
    user_id = "test_user_avg_delay_999"
    now = datetime.now()
    scheduled = now.replace(hour=7, minute=0, second=0, microsecond=0)

    # Create multiple submissions with different delays
    for delay in [10, 20, 15, 25, 20]:
        submission = SleepQuizSubmission(
            id=str(uuid4()),
            user_id=user_id,
            scheduled_time=scheduled,
            submitted_at=now,
            response_delay_minutes=delay
        )
        await save_sleep_quiz_submission(submission)

    # Retrieve and calculate average
    patterns = await get_submission_patterns(user_id, days=30)

    assert len(patterns) >= 5

    delays = [p['response_delay_minutes'] for p in patterns]
    avg_delay = sum(delays) / len(delays)

    # Average should be 18 (10+20+15+25+20)/5
    assert abs(avg_delay - 18.0) < 1.0  # Allow small floating point error
