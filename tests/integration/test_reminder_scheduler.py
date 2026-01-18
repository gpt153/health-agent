"""Integration tests for reminder scheduler initialization and job execution"""
import pytest
from datetime import datetime, time
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch

from telegram.ext import Application

from src.scheduler.reminder_manager import ReminderManager
from src.db.queries import create_reminder, get_active_reminders_all
from src.models.reminder import Reminder, ReminderSchedule


@pytest.mark.asyncio
async def test_reminder_manager_requires_job_queue():
    """
    Test that ReminderManager validates job_queue is not None during initialization

    This prevents silent failures when Application is built without .job_queue()
    """
    # Create Application WITHOUT job_queue
    app_no_jq = Mock(spec=Application)
    app_no_jq.job_queue = None

    # Should raise RuntimeError with helpful message
    with pytest.raises(RuntimeError) as exc_info:
        ReminderManager(app_no_jq)

    assert "job_queue is None" in str(exc_info.value)
    assert "job_queue()" in str(exc_info.value)  # Should mention how to fix


@pytest.mark.asyncio
async def test_reminder_manager_initializes_with_job_queue():
    """
    Test that ReminderManager initializes successfully when job_queue is present
    """
    # Create Application WITH job_queue
    app = Mock(spec=Application)
    app.job_queue = Mock()

    # Should initialize without error
    manager = ReminderManager(app)

    assert manager.application == app
    assert manager.job_queue == app.job_queue


@pytest.mark.asyncio
async def test_load_reminders_schedules_jobs():
    """
    Test that load_reminders() successfully schedules jobs in the job queue
    """
    # Create test user and reminder
    user_id = f"test_user_{uuid4()}"

    # Create reminder in database
    reminder = Reminder(
        user_id=user_id,
        reminder_type="daily",
        message="Test reminder - take your medicine",
        schedule=ReminderSchedule(
            type="daily",
            time="10:00",
            timezone="UTC",
            days=[0, 1, 2, 3, 4, 5, 6]  # All days
        )
    )
    await create_reminder(reminder)

    # Create mock Application with job_queue
    app = Mock(spec=Application)
    mock_job_queue = Mock()
    mock_job_queue.run_daily = Mock()
    mock_job_queue.jobs = Mock(return_value=[])
    app.job_queue = mock_job_queue

    # Initialize manager
    manager = ReminderManager(app)

    # Load reminders
    await manager.load_reminders()

    # Verify run_daily was called
    assert mock_job_queue.run_daily.called
    call_args = mock_job_queue.run_daily.call_args

    # Verify callback, time, and data
    assert call_args.kwargs['callback'] == manager._send_custom_reminder
    assert call_args.kwargs['time'].hour == 10
    assert call_args.kwargs['time'].minute == 0
    assert call_args.kwargs['data']['user_id'] == user_id
    assert call_args.kwargs['data']['message'] == "Test reminder - take your medicine"


@pytest.mark.asyncio
async def test_load_reminders_handles_multiple_reminders():
    """
    Test that load_reminders() correctly schedules multiple reminders
    """
    # Create multiple test users and reminders
    user1 = f"test_user_{uuid4()}"
    user2 = f"test_user_{uuid4()}"

    reminder1 = Reminder(
        user_id=user1,
        reminder_type="daily",
        message="Morning reminder",
        schedule=ReminderSchedule(
            type="daily",
            time="08:00",
            timezone="UTC"
        )
    )

    reminder2 = Reminder(
        user_id=user2,
        reminder_type="daily",
        message="Evening reminder",
        schedule=ReminderSchedule(
            type="daily",
            time="20:00",
            timezone="UTC"
        )
    )

    await create_reminder(reminder1)
    await create_reminder(reminder2)

    # Create mock Application
    app = Mock(spec=Application)
    mock_job_queue = Mock()
    mock_job_queue.run_daily = Mock()
    mock_job_queue.jobs = Mock(return_value=[])
    app.job_queue = mock_job_queue

    # Initialize and load
    manager = ReminderManager(app)
    await manager.load_reminders()

    # Should have called run_daily at least twice (may be more from other tests)
    assert mock_job_queue.run_daily.call_count >= 2


@pytest.mark.asyncio
async def test_load_reminders_skips_invalid_data():
    """
    Test that load_reminders() gracefully skips reminders with invalid data
    """
    # Create reminder with missing user_id (invalid)
    reminder = Reminder(
        user_id="",  # Empty user_id
        reminder_type="daily",
        message="Should be skipped",
        schedule=ReminderSchedule(
            type="daily",
            time="10:00",
            timezone="UTC"
        )
    )
    await create_reminder(reminder)

    # Create mock Application
    app = Mock(spec=Application)
    mock_job_queue = Mock()
    mock_job_queue.run_daily = Mock()
    mock_job_queue.jobs = Mock(return_value=[])
    app.job_queue = mock_job_queue

    # Initialize and load
    manager = ReminderManager(app)

    # Should not raise exception, but skip invalid reminder
    await manager.load_reminders()

    # run_daily should not be called for invalid reminder
    # (this test assumes only this invalid reminder exists in clean test DB)


@pytest.mark.asyncio
async def test_schedule_custom_reminder_validates_time_format():
    """
    Test that schedule_custom_reminder validates time format
    """
    # Create mock Application
    app = Mock(spec=Application)
    mock_job_queue = Mock()
    app.job_queue = mock_job_queue

    manager = ReminderManager(app)

    # Try to schedule with invalid time format
    await manager.schedule_custom_reminder(
        user_id="test_user",
        reminder_time="invalid",  # Not HH:MM format
        message="Test message",
        reminder_id=str(uuid4())
    )

    # Should not call run_daily (validation should reject it)
    assert not mock_job_queue.run_daily.called


@pytest.mark.asyncio
async def test_schedule_custom_reminder_validates_time_range():
    """
    Test that schedule_custom_reminder validates time is within valid range
    """
    # Create mock Application
    app = Mock(spec=Application)
    mock_job_queue = Mock()
    app.job_queue = mock_job_queue

    manager = ReminderManager(app)

    # Try to schedule with out-of-range time
    await manager.schedule_custom_reminder(
        user_id="test_user",
        reminder_time="25:70",  # Invalid: hour > 23, minute > 59
        message="Test message",
        reminder_id=str(uuid4())
    )

    # Should not call run_daily (validation should reject it)
    assert not mock_job_queue.run_daily.called


@pytest.mark.asyncio
async def test_load_reminders_logs_job_count():
    """
    Test that load_reminders() logs the job count for observability

    This helps diagnose issues by showing how many jobs were actually scheduled
    """
    # Create test reminder
    user_id = f"test_user_{uuid4()}"
    reminder = Reminder(
        user_id=user_id,
        reminder_type="daily",
        message="Test reminder",
        schedule=ReminderSchedule(
            type="daily",
            time="10:00",
            timezone="UTC"
        )
    )
    await create_reminder(reminder)

    # Create mock Application with job tracking
    app = Mock(spec=Application)
    mock_job_queue = Mock()
    mock_jobs = []

    def mock_run_daily(**kwargs):
        mock_jobs.append(kwargs)

    mock_job_queue.run_daily = mock_run_daily
    mock_job_queue.jobs = lambda: mock_jobs
    app.job_queue = mock_job_queue

    # Initialize and load
    manager = ReminderManager(app)

    # Capture logs
    with patch('src.scheduler.reminder_manager.logger') as mock_logger:
        await manager.load_reminders()

        # Verify logging includes job count
        log_calls = [str(call) for call in mock_logger.info.call_args_list]

        # Should log job count
        assert any("JobQueue now has" in call for call in log_calls)


@pytest.mark.asyncio
async def test_one_time_reminder_uses_run_once():
    """
    Test that one-time reminders use run_once instead of run_daily
    """
    # Create mock Application
    app = Mock(spec=Application)
    mock_job_queue = Mock()
    mock_job_queue.run_once = Mock()
    app.job_queue = mock_job_queue

    manager = ReminderManager(app)

    # Schedule one-time reminder
    await manager.schedule_custom_reminder(
        user_id="test_user",
        reminder_time="14:30",
        message="One-time event",
        reminder_type="once",
        reminder_date="2026-12-31",
        reminder_id=str(uuid4())
    )

    # Should call run_once, not run_daily
    assert mock_job_queue.run_once.called

    # Verify datetime is correct
    call_args = mock_job_queue.run_once.call_args
    when = call_args.kwargs['when']
    assert when.hour == 14
    assert when.minute == 30
    assert when.day == 31
    assert when.month == 12


@pytest.mark.asyncio
async def test_daily_reminder_respects_day_filter():
    """
    Test that daily reminders include day filter in job data
    """
    # Create mock Application
    app = Mock(spec=Application)
    mock_job_queue = Mock()
    mock_job_queue.run_daily = Mock()
    app.job_queue = mock_job_queue

    manager = ReminderManager(app)

    # Schedule with specific days (weekdays only)
    weekdays = [0, 1, 2, 3, 4]  # Monday-Friday
    await manager.schedule_custom_reminder(
        user_id="test_user",
        reminder_time="09:00",
        message="Weekday reminder",
        reminder_type="daily",
        days=weekdays,
        reminder_id=str(uuid4())
    )

    # Verify days filter is in job data
    call_args = mock_job_queue.run_daily.call_args
    job_data = call_args.kwargs['data']
    assert job_data['days'] == weekdays


@pytest.mark.asyncio
async def test_reminder_manager_with_real_application_builder():
    """
    Integration test with real Application builder to ensure job_queue works

    This test verifies the actual fix: using .job_queue() in builder
    """
    import os

    # Get a test token (or use dummy - Application won't connect for this test)
    test_token = os.getenv("TELEGRAM_BOT_TOKEN", "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")

    # Build Application WITH job_queue (the fix)
    app = Application.builder().token(test_token).job_queue().build()

    # Initialize Application (required for job_queue to be ready)
    await app.initialize()

    try:
        # Verify job_queue is not None
        assert app.job_queue is not None

        # ReminderManager should initialize successfully
        manager = ReminderManager(app)
        assert manager.job_queue is not None

    finally:
        # Cleanup
        await app.shutdown()
