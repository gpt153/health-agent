"""Unit tests for HealthService"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date, timedelta
from uuid import uuid4
import sys

# Mock external dependencies before importing HealthService
sys.modules['psycopg'] = MagicMock()
sys.modules['psycopg_pool'] = MagicMock()
sys.modules['src.db.connection'] = MagicMock()

from src.services.health_service import HealthService


@pytest.fixture
def mock_db():
    """Mock database connection"""
    db = MagicMock()
    db.connection = AsyncMock()
    return db


@pytest.fixture
def mock_memory_manager():
    """Mock memory manager"""
    memory = AsyncMock()
    return memory


@pytest.fixture
def mock_reminder_manager():
    """Mock reminder manager"""
    reminder_mgr = AsyncMock()
    reminder_mgr.schedule_reminder = AsyncMock()
    reminder_mgr.unschedule_reminder = AsyncMock()
    return reminder_mgr


@pytest.fixture
def health_service(mock_db, mock_memory_manager):
    """Create HealthService instance with mocks"""
    return HealthService(mock_db, mock_memory_manager)


@pytest.fixture
def health_service_with_reminders(mock_db, mock_memory_manager, mock_reminder_manager):
    """Create HealthService instance with reminder manager"""
    return HealthService(mock_db, mock_memory_manager, mock_reminder_manager)


# Test create_tracking_category
@pytest.mark.asyncio
@patch('src.services.health_service.queries')
async def test_create_tracking_category_success(mock_queries, health_service):
    """Test successful tracking category creation"""
    # Setup
    user_id = "12345"
    name = "Daily Weight"
    fields = {
        'weight': {'type': 'number', 'label': 'Weight (kg)'}
    }

    mock_queries.create_tracking_category = AsyncMock()

    # Execute
    result = await health_service.create_tracking_category(
        user_id, name, fields
    )

    # Assert
    assert result['success'] is True
    assert result['category_id'] is not None
    assert result['category'].name == "Daily Weight"
    assert result['message'] == "Tracking category 'Daily Weight' created successfully"
    mock_queries.create_tracking_category.assert_called_once()


@pytest.mark.asyncio
@patch('src.services.health_service.queries')
async def test_create_tracking_category_error(mock_queries, health_service):
    """Test tracking category creation with error"""
    # Setup
    user_id = "12345"
    name = "Daily Weight"
    fields = {'weight': {'type': 'number'}}

    mock_queries.create_tracking_category = AsyncMock(side_effect=Exception("Database error"))

    # Execute
    result = await health_service.create_tracking_category(
        user_id, name, fields
    )

    # Assert
    assert result['success'] is False
    assert result['category_id'] is None
    assert "Error creating tracking category" in result['message']


# Test get_tracking_categories
@pytest.mark.asyncio
@patch('src.services.health_service.queries')
async def test_get_tracking_categories_success(mock_queries, health_service):
    """Test getting tracking categories"""
    # Setup
    user_id = "12345"
    mock_categories = [
        {'id': str(uuid4()), 'name': 'Weight', 'active': True},
        {'id': str(uuid4()), 'name': 'Steps', 'active': True}
    ]

    mock_queries.get_tracking_categories = AsyncMock(return_value=mock_categories)

    # Execute
    result = await health_service.get_tracking_categories(user_id)

    # Assert
    assert len(result) == 2
    assert result[0]['name'] == 'Weight'
    mock_queries.get_tracking_categories.assert_called_once_with(user_id, True)


# Test log_tracking_entry
@pytest.mark.asyncio
@patch('src.services.health_service.queries')
async def test_log_tracking_entry_success(mock_queries, health_service):
    """Test successful tracking entry logging"""
    # Setup
    user_id = "12345"
    category_id = str(uuid4())
    data = {'weight': 75.5, 'unit': 'kg'}
    timestamp = datetime.now()

    mock_queries.save_tracking_entry = AsyncMock()

    # Execute
    result = await health_service.log_tracking_entry(
        user_id, category_id, data, timestamp
    )

    # Assert
    assert result['success'] is True
    assert result['entry_id'] is not None
    assert result['entry'].data == data
    assert result['message'] == 'Tracking entry saved successfully'
    mock_queries.save_tracking_entry.assert_called_once()


@pytest.mark.asyncio
@patch('src.services.health_service.queries')
async def test_log_tracking_entry_error(mock_queries, health_service):
    """Test tracking entry logging with error"""
    # Setup
    user_id = "12345"
    category_id = str(uuid4())
    data = {'weight': 75.5}

    mock_queries.save_tracking_entry = AsyncMock(side_effect=Exception("Save error"))

    # Execute
    result = await health_service.log_tracking_entry(
        user_id, category_id, data
    )

    # Assert
    assert result['success'] is False
    assert result['entry_id'] is None


# Test create_reminder
@pytest.mark.asyncio
@patch('src.services.health_service.queries')
async def test_create_reminder_success(
    mock_queries,
    health_service_with_reminders,
    mock_reminder_manager
):
    """Test successful reminder creation"""
    # Setup
    user_id = "12345"
    reminder_type = "simple"
    message = "Take your medication"
    schedule = {
        'type': 'daily',
        'time': '21:00',
        'timezone': 'UTC'
    }

    mock_queries.create_reminder = AsyncMock()

    # Execute
    result = await health_service_with_reminders.create_reminder(
        user_id, reminder_type, message, schedule
    )

    # Assert
    assert result['success'] is True
    assert result['reminder_id'] is not None
    assert result['reminder'].message == message
    assert result['message'] == 'Reminder created successfully'
    mock_queries.create_reminder.assert_called_once()
    mock_reminder_manager.schedule_reminder.assert_called_once()


@pytest.mark.asyncio
@patch('src.services.health_service.queries')
async def test_create_reminder_error(mock_queries, health_service):
    """Test reminder creation with error"""
    # Setup
    user_id = "12345"
    reminder_type = "simple"
    message = "Take medication"
    schedule = {'type': 'daily', 'time': '21:00', 'timezone': 'UTC'}

    mock_queries.create_reminder = AsyncMock(side_effect=Exception("DB error"))

    # Execute
    result = await health_service.create_reminder(
        user_id, reminder_type, message, schedule
    )

    # Assert
    assert result['success'] is False
    assert result['reminder_id'] is None


# Test get_active_reminders
@pytest.mark.asyncio
@patch('src.services.health_service.queries')
async def test_get_active_reminders_success(mock_queries, health_service):
    """Test getting active reminders"""
    # Setup
    user_id = "12345"
    mock_reminders = [
        {'id': str(uuid4()), 'message': 'Medication', 'active': True},
        {'id': str(uuid4()), 'message': 'Exercise', 'active': True}
    ]

    mock_queries.get_active_reminders = AsyncMock(return_value=mock_reminders)

    # Execute
    result = await health_service.get_active_reminders(user_id)

    # Assert
    assert len(result) == 2
    assert result[0]['message'] == 'Medication'


# Test cancel_reminder
@pytest.mark.asyncio
@patch('src.services.health_service.queries')
async def test_cancel_reminder_success(
    mock_queries,
    health_service_with_reminders,
    mock_reminder_manager
):
    """Test successful reminder cancellation"""
    # Setup
    user_id = "12345"
    reminder_id = str(uuid4())

    mock_queries.delete_reminder = AsyncMock(return_value=True)

    # Execute
    result = await health_service_with_reminders.cancel_reminder(
        user_id, reminder_id
    )

    # Assert
    assert result['success'] is True
    assert result['message'] == 'Reminder cancelled successfully'
    mock_reminder_manager.unschedule_reminder.assert_called_once_with(reminder_id)


@pytest.mark.asyncio
@patch('src.services.health_service.queries')
async def test_cancel_reminder_not_found(mock_queries, health_service):
    """Test cancelling non-existent reminder"""
    # Setup
    user_id = "12345"
    reminder_id = str(uuid4())

    mock_queries.delete_reminder = AsyncMock(return_value=False)

    # Execute
    result = await health_service.cancel_reminder(user_id, reminder_id)

    # Assert
    assert result['success'] is False
    assert 'not found' in result['message']


# Test complete_reminder
@pytest.mark.asyncio
@patch('src.services.health_service.queries')
async def test_complete_reminder_success(mock_queries, health_service):
    """Test successful reminder completion"""
    # Setup
    user_id = "12345"
    reminder_id = str(uuid4())
    completed_at = datetime.now()
    completion_id = str(uuid4())

    mock_queries.save_reminder_completion = AsyncMock(return_value=completion_id)

    # Execute
    result = await health_service.complete_reminder(
        user_id, reminder_id, completed_at
    )

    # Assert
    assert result['success'] is True
    assert result['completion_id'] == completion_id
    assert result['message'] == 'Reminder marked as completed'


# Test get_reminder_streak
@pytest.mark.asyncio
@patch('src.services.health_service.queries')
async def test_get_reminder_streak_success(mock_queries, health_service):
    """Test getting reminder streak"""
    # Setup
    user_id = "12345"
    reminder_id = str(uuid4())

    mock_queries.calculate_current_streak = AsyncMock(return_value=7)
    mock_queries.calculate_best_streak = AsyncMock(return_value=14)

    # Execute
    result = await health_service.get_reminder_streak(user_id, reminder_id)

    # Assert
    assert result['current_streak'] == 7
    assert result['best_streak'] == 14


# Test get_reminder_analytics
@pytest.mark.asyncio
@patch('src.services.health_service.queries')
async def test_get_reminder_analytics_success(mock_queries, health_service):
    """Test getting reminder analytics"""
    # Setup
    user_id = "12345"
    reminder_id = str(uuid4())
    mock_analytics = {
        'completion_rate': 0.85,
        'total_completions': 25,
        'total_scheduled': 30,
        'current_streak': 7,
        'best_streak': 14,
        'avg_completion_time': '21:15'
    }

    mock_queries.get_reminder_analytics = AsyncMock(return_value=mock_analytics)

    # Execute
    result = await health_service.get_reminder_analytics(user_id, reminder_id)

    # Assert
    assert result['completion_rate'] == 0.85
    assert result['total_completions'] == 25
    assert result['current_streak'] == 7


# Test calculate_tracking_trends
@pytest.mark.asyncio
async def test_calculate_tracking_trends_insufficient_data(health_service):
    """Test trend calculation with no data"""
    # Setup
    user_id = "12345"
    category_id = str(uuid4())

    # Mock get_tracking_entries to return empty list
    with patch.object(health_service, 'get_tracking_entries', new=AsyncMock(return_value=[])):
        # Execute
        result = await health_service.calculate_tracking_trends(
            user_id, category_id, 'weight'
        )

        # Assert
        assert result['trend'] == 'insufficient_data'
        assert result['data_points'] == 0


# Test generate_health_summary
@pytest.mark.asyncio
async def test_generate_health_summary_success(health_service):
    """Test generating health summary"""
    # Setup
    user_id = "12345"
    mock_categories = [
        {'id': str(uuid4()), 'name': 'Weight'},
        {'id': str(uuid4()), 'name': 'Steps'}
    ]
    mock_reminders = [
        {'id': str(uuid4()), 'message': 'Medication'}
    ]

    # Mock methods
    with patch.object(health_service, 'get_tracking_categories', new=AsyncMock(return_value=mock_categories)):
        with patch.object(health_service, 'get_active_reminders', new=AsyncMock(return_value=mock_reminders)):
            with patch.object(health_service, 'get_tracking_entries', new=AsyncMock(return_value=[])):
                # Execute
                result = await health_service.generate_health_summary(user_id)

                # Assert
                assert result['period'] == '7 days'
                assert result['active_categories'] == 2
                assert result['reminders']['total_active'] == 1
