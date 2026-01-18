"""Unit tests for UserService"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Mock psycopg and db connection before importing UserService
sys.modules['psycopg'] = MagicMock()
sys.modules['psycopg_pool'] = MagicMock()
sys.modules['src.db.connection'] = MagicMock()

from src.services.user_service import UserService


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
    memory.create_user_files = AsyncMock()
    memory.update_preferences = AsyncMock()
    memory.load_user_memory = AsyncMock(return_value={'preferences': 'test prefs'})
    return memory


@pytest.fixture
def user_service(mock_db, mock_memory_manager):
    """Create UserService instance with mocks"""
    return UserService(mock_db, mock_memory_manager)


@pytest.mark.asyncio
@patch('src.services.user_service.queries')
async def test_create_user_success(mock_queries, user_service, mock_memory_manager):
    """Test creating a new user successfully"""
    # Setup
    telegram_id = "12345"
    mock_queries.user_exists = AsyncMock(return_value=False)
    mock_queries.create_user = AsyncMock()

    # Execute
    result = await user_service.create_user(telegram_id)

    # Assert
    assert result['success'] is True
    assert result['telegram_id'] == telegram_id
    assert result['existing'] is False
    mock_queries.create_user.assert_called_once_with(telegram_id)
    mock_memory_manager.create_user_files.assert_called_once_with(telegram_id)


@pytest.mark.asyncio
@patch('src.services.user_service.queries')
async def test_create_user_already_exists(mock_queries, user_service):
    """Test creating a user that already exists"""
    # Setup
    telegram_id = "12345"
    mock_queries.user_exists = AsyncMock(return_value=True)

    # Execute
    result = await user_service.create_user(telegram_id)

    # Assert
    assert result['success'] is True
    assert result['existing'] is True
    assert result['message'] == 'User already exists'


@pytest.mark.asyncio
@patch('src.services.user_service.queries')
async def test_get_user_exists(mock_queries, user_service):
    """Test getting an existing user"""
    # Setup
    telegram_id = "12345"
    mock_subscription = {'status': 'active', 'tier': 'pro'}
    mock_queries.user_exists = AsyncMock(return_value=True)
    mock_queries.get_user_subscription_status = AsyncMock(return_value=mock_subscription)

    # Execute
    result = await user_service.get_user(telegram_id)

    # Assert
    assert result is not None
    assert result['telegram_id'] == telegram_id
    assert result['exists'] is True
    assert result['subscription'] == mock_subscription


@pytest.mark.asyncio
@patch('src.services.user_service.queries')
async def test_get_user_not_exists(mock_queries, user_service):
    """Test getting a non-existent user"""
    # Setup
    telegram_id = "12345"
    mock_queries.user_exists = AsyncMock(return_value=False)

    # Execute
    result = await user_service.get_user(telegram_id)

    # Assert
    assert result is None


@pytest.mark.asyncio
@patch('src.services.user_service.queries')
async def test_user_exists_true(mock_queries, user_service):
    """Test user_exists returns True"""
    # Setup
    telegram_id = "12345"
    mock_queries.user_exists = AsyncMock(return_value=True)

    # Execute
    result = await user_service.user_exists(telegram_id)

    # Assert
    assert result is True


@pytest.mark.asyncio
@patch('src.services.user_service.queries')
async def test_user_exists_false(mock_queries, user_service):
    """Test user_exists returns False"""
    # Setup
    telegram_id = "12345"
    mock_queries.user_exists = AsyncMock(return_value=False)

    # Execute
    result = await user_service.user_exists(telegram_id)

    # Assert
    assert result is False


@pytest.mark.asyncio
@patch('src.services.user_service.queries')
async def test_activate_user_success(mock_queries, user_service):
    """Test activating user with valid invite code"""
    # Setup
    telegram_id = "12345"
    invite_code = "HEALTH2024"
    code_details = {'tier': 'pro', 'trial_days': 30, 'is_master_code': False}
    subscription = {'status': 'trial', 'tier': 'pro'}

    mock_queries.validate_invite_code = AsyncMock(return_value=code_details)
    mock_queries.use_invite_code = AsyncMock(return_value=True)
    mock_queries.get_user_subscription_status = AsyncMock(return_value=subscription)

    # Execute
    result = await user_service.activate_user(telegram_id, invite_code)

    # Assert
    assert result['success'] is True
    assert result['subscription'] == subscription
    assert result['code_details'] == code_details
    mock_queries.validate_invite_code.assert_called_once_with(invite_code)
    mock_queries.use_invite_code.assert_called_once_with(invite_code, telegram_id)


@pytest.mark.asyncio
@patch('src.services.user_service.queries')
async def test_activate_user_invalid_code(mock_queries, user_service):
    """Test activating user with invalid invite code"""
    # Setup
    telegram_id = "12345"
    invite_code = "INVALID"
    mock_queries.validate_invite_code = AsyncMock(return_value=None)

    # Execute
    result = await user_service.activate_user(telegram_id, invite_code)

    # Assert
    assert result['success'] is False
    assert 'Invalid or expired' in result['message']


@pytest.mark.asyncio
@patch('src.services.user_service.queries')
async def test_is_authorized_active(mock_queries, user_service):
    """Test is_authorized for active user"""
    # Setup
    telegram_id = "12345"
    mock_queries.get_user_subscription_status = AsyncMock(
        return_value={'status': 'active', 'tier': 'pro'}
    )

    # Execute
    result = await user_service.is_authorized(telegram_id)

    # Assert
    assert result is True


@pytest.mark.asyncio
@patch('src.services.user_service.queries')
async def test_is_authorized_trial(mock_queries, user_service):
    """Test is_authorized for trial user"""
    # Setup
    telegram_id = "12345"
    mock_queries.get_user_subscription_status = AsyncMock(
        return_value={'status': 'trial', 'tier': 'pro'}
    )

    # Execute
    result = await user_service.is_authorized(telegram_id)

    # Assert
    assert result is True


@pytest.mark.asyncio
@patch('src.services.user_service.queries')
async def test_is_authorized_pending(mock_queries, user_service):
    """Test is_authorized for pending user"""
    # Setup
    telegram_id = "12345"
    mock_queries.get_user_subscription_status = AsyncMock(
        return_value={'status': 'pending', 'tier': 'basic'}
    )

    # Execute
    result = await user_service.is_authorized(telegram_id)

    # Assert
    assert result is False


@pytest.mark.asyncio
@patch('src.services.user_service.queries')
async def test_is_authorized_no_subscription(mock_queries, user_service):
    """Test is_authorized when user has no subscription"""
    # Setup
    telegram_id = "12345"
    mock_queries.get_user_subscription_status = AsyncMock(return_value=None)

    # Execute
    result = await user_service.is_authorized(telegram_id)

    # Assert
    assert result is False


@pytest.mark.asyncio
@patch('src.services.user_service.queries')
async def test_get_onboarding_state(mock_queries, user_service):
    """Test getting onboarding state"""
    # Setup
    telegram_id = "12345"
    onboarding_state = {'current_step': 'language', 'completed_at': None}
    mock_queries.get_onboarding_state = AsyncMock(return_value=onboarding_state)

    # Execute
    result = await user_service.get_onboarding_state(telegram_id)

    # Assert
    assert result == onboarding_state


@pytest.mark.asyncio
@patch('src.services.user_service.queries')
async def test_update_onboarding_state(mock_queries, user_service):
    """Test updating onboarding state"""
    # Setup
    telegram_id = "12345"
    state = {'current_step': 'goals', 'data': {}}
    mock_queries.update_onboarding_state = AsyncMock()

    # Execute
    result = await user_service.update_onboarding_state(telegram_id, state)

    # Assert
    assert result is True
    mock_queries.update_onboarding_state.assert_called_once_with(telegram_id, state)


@pytest.mark.asyncio
@patch('src.services.user_service.queries')
async def test_complete_onboarding(mock_queries, user_service):
    """Test completing onboarding"""
    # Setup
    telegram_id = "12345"
    mock_queries.complete_onboarding = AsyncMock()

    # Execute
    result = await user_service.complete_onboarding(telegram_id)

    # Assert
    assert result is True
    mock_queries.complete_onboarding.assert_called_once_with(telegram_id)


@pytest.mark.asyncio
async def test_update_preferences(user_service, mock_memory_manager):
    """Test updating user preferences"""
    # Setup
    telegram_id = "12345"
    key = "timezone"
    value = "America/New_York"

    # Execute
    result = await user_service.update_preferences(telegram_id, key, value)

    # Assert
    assert result is True
    mock_memory_manager.update_preferences.assert_called_once_with(telegram_id, key, value)


@pytest.mark.asyncio
async def test_get_preferences(user_service, mock_memory_manager):
    """Test getting user preferences"""
    # Setup
    telegram_id = "12345"

    # Execute
    result = await user_service.get_preferences(telegram_id)

    # Assert
    assert 'raw_content' in result
    assert result['telegram_id'] == telegram_id
    mock_memory_manager.load_user_memory.assert_called_once_with(telegram_id)


@pytest.mark.asyncio
@patch('src.services.user_service.queries')
async def test_get_subscription_status(mock_queries, user_service):
    """Test getting subscription status"""
    # Setup
    telegram_id = "12345"
    subscription = {'status': 'active', 'tier': 'pro', 'start_date': '2024-01-01'}
    mock_queries.get_user_subscription_status = AsyncMock(return_value=subscription)

    # Execute
    result = await user_service.get_subscription_status(telegram_id)

    # Assert
    assert result == subscription


@pytest.mark.asyncio
async def test_set_timezone(user_service, mock_memory_manager):
    """Test setting user timezone"""
    # Setup
    telegram_id = "12345"
    timezone = "America/Los_Angeles"

    # Execute
    result = await user_service.set_timezone(telegram_id, timezone)

    # Assert
    assert result is True
    mock_memory_manager.update_preferences.assert_called_once_with(
        telegram_id, 'timezone', timezone
    )


# Note: test_get_timezone is skipped because it requires timezone_helper module
# which has external dependencies. This functionality is tested in integration tests.
