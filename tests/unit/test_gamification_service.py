"""Unit tests for GamificationService"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import sys

# Mock external dependencies before importing GamificationService
sys.modules['psycopg'] = MagicMock()
sys.modules['psycopg_pool'] = MagicMock()
sys.modules['src.db.connection'] = MagicMock()
sys.modules['src.gamification.xp_system'] = MagicMock()
sys.modules['src.gamification.streak_system'] = MagicMock()
sys.modules['src.gamification.achievement_system'] = MagicMock()
sys.modules['src.gamification.motivation_profiles'] = MagicMock()

from src.services.gamification_service import GamificationService


@pytest.fixture
def mock_db():
    """Mock database connection"""
    db = MagicMock()
    db.connection = AsyncMock()
    return db


@pytest.fixture
def gamification_service(mock_db):
    """Create GamificationService instance with mocks"""
    return GamificationService(mock_db)


# Test process_reminder_completion
@pytest.mark.asyncio
@patch('src.services.gamification_service.award_xp')
@patch('src.services.gamification_service.update_streak')
@patch('src.services.gamification_service.check_and_award_achievements')
@patch('src.services.gamification_service.get_or_detect_profile')
@patch('src.services.gamification_service.get_motivational_message')
async def test_process_reminder_completion_success(
    mock_motivational_msg,
    mock_get_profile,
    mock_check_achievements,
    mock_update_streak,
    mock_award_xp,
    gamification_service
):
    """Test successful reminder completion gamification"""
    # Setup
    user_id = "12345"
    reminder_id = "reminder-uuid"
    completed_at = datetime(2024, 1, 15, 10, 5)  # 10:05
    scheduled_time = "10:00"  # 5 minutes late, within 30 min window

    # Mock award_xp
    mock_award_xp.return_value = AsyncMock(return_value={
        'xp_awarded': 15,  # 10 base + 5 bonus
        'leveled_up': False,
        'new_level': 5
    })()

    # Mock update_streak
    mock_update_streak.return_value = AsyncMock(return_value={
        'current_streak': 7,
        'milestone_reached': False
    })()

    # Mock check_and_award_achievements
    mock_check_achievements.return_value = AsyncMock(return_value=[])()

    # Mock motivation profile
    mock_get_profile.return_value = AsyncMock(return_value='achiever')()
    mock_motivational_msg.return_value = "Great job staying consistent!"

    # Execute
    result = await gamification_service.process_reminder_completion(
        user_id, reminder_id, completed_at, scheduled_time
    )

    # Assert
    assert result['xp_awarded'] == 15  # Base 10 + on-time bonus 5
    assert result['level_up'] is False
    assert result['new_level'] == 5
    assert result['streak_updated'] is True
    assert result['current_streak'] == 7
    assert len(result['achievements_unlocked']) == 0
    assert 'Great job' in result['message']
    assert '⭐' in result['message']  # XP display


@pytest.mark.asyncio
@patch('src.services.gamification_service.award_xp')
@patch('src.services.gamification_service.update_streak')
@patch('src.services.gamification_service.check_and_award_achievements')
@patch('src.services.gamification_service.get_or_detect_profile')
@patch('src.services.gamification_service.get_motivational_message')
async def test_process_reminder_completion_with_level_up(
    mock_motivational_msg,
    mock_get_profile,
    mock_check_achievements,
    mock_update_streak,
    mock_award_xp,
    gamification_service
):
    """Test reminder completion with level up"""
    # Setup
    user_id = "12345"
    reminder_id = "reminder-uuid"
    completed_at = datetime(2024, 1, 15, 10, 0)
    scheduled_time = "10:00"

    # Mock level up
    mock_award_xp.return_value = AsyncMock(return_value={
        'xp_awarded': 15,
        'leveled_up': True,
        'new_level': 6,
        'new_tier': 'silver'
    })()

    mock_update_streak.return_value = AsyncMock(return_value={
        'current_streak': 7,
        'milestone_reached': False
    })()

    mock_check_achievements.return_value = AsyncMock(return_value=[])()
    mock_get_profile.return_value = AsyncMock(return_value='achiever')()
    mock_motivational_msg.return_value = "Level up! You're unstoppable!"

    # Execute
    result = await gamification_service.process_reminder_completion(
        user_id, reminder_id, completed_at, scheduled_time
    )

    # Assert
    assert result['level_up'] is True
    assert result['new_level'] == 6
    assert '🥈' in result['message']  # Silver tier emoji
    assert 'Level 6 reached' in result['message']


@pytest.mark.asyncio
@patch('src.services.gamification_service.award_xp')
@patch('src.services.gamification_service.update_streak')
@patch('src.services.gamification_service.check_and_award_achievements')
@patch('src.services.gamification_service.get_or_detect_profile')
@patch('src.services.gamification_service.get_motivational_message')
async def test_process_reminder_completion_with_achievement(
    mock_motivational_msg,
    mock_get_profile,
    mock_check_achievements,
    mock_update_streak,
    mock_award_xp,
    gamification_service
):
    """Test reminder completion with achievement unlock"""
    # Setup
    user_id = "12345"
    reminder_id = "reminder-uuid"
    completed_at = datetime(2024, 1, 15, 10, 0)
    scheduled_time = "10:00"

    # Mock achievement
    achievement = {
        'name': 'Medication Master',
        'icon': '💊',
        'xp_reward': 50
    }

    mock_award_xp.side_effect = [
        AsyncMock(return_value={
            'xp_awarded': 15,
            'leveled_up': False,
            'new_level': 5
        })(),
        AsyncMock(return_value={'xp_awarded': 50})()  # Achievement XP
    ]

    mock_update_streak.return_value = AsyncMock(return_value={
        'current_streak': 7,
        'milestone_reached': False
    })()

    mock_check_achievements.return_value = AsyncMock(return_value=[achievement])()
    mock_get_profile.return_value = AsyncMock(return_value='achiever')()
    mock_motivational_msg.return_value = "Achievement unlocked!"

    # Execute
    result = await gamification_service.process_reminder_completion(
        user_id, reminder_id, completed_at, scheduled_time
    )

    # Assert
    assert result['xp_awarded'] == 65  # 15 base + 50 achievement
    assert len(result['achievements_unlocked']) == 1
    assert result['achievements_unlocked'][0]['name'] == 'Medication Master'
    assert '💊' in result['message']


# Test process_food_entry
@pytest.mark.asyncio
@patch('src.services.gamification_service.award_xp')
@patch('src.services.gamification_service.update_streak')
@patch('src.services.gamification_service.check_and_award_achievements')
async def test_process_food_entry_success(
    mock_check_achievements,
    mock_update_streak,
    mock_award_xp,
    gamification_service
):
    """Test successful food entry gamification"""
    # Setup
    user_id = "12345"
    food_entry_id = "food-uuid"
    logged_at = datetime(2024, 1, 15, 12, 30)
    meal_type = "lunch"

    mock_award_xp.return_value = AsyncMock(return_value={
        'xp_awarded': 5,
        'leveled_up': False,
        'new_level': 3
    })()

    mock_update_streak.return_value = AsyncMock(return_value={
        'current_streak': 5,
        'milestone_reached': False
    })()

    mock_check_achievements.return_value = AsyncMock(return_value=[])()

    # Execute
    result = await gamification_service.process_food_entry(
        user_id, food_entry_id, logged_at, meal_type
    )

    # Assert
    assert result['xp_awarded'] == 5
    assert result['streak_updated'] is True
    assert result['current_streak'] == 5
    assert '5-day nutrition streak' in result['message']


# Test process_sleep_quiz
@pytest.mark.asyncio
@patch('src.services.gamification_service.award_xp')
@patch('src.services.gamification_service.update_streak')
@patch('src.services.gamification_service.check_and_award_achievements')
async def test_process_sleep_quiz_success(
    mock_check_achievements,
    mock_update_streak,
    mock_award_xp,
    gamification_service
):
    """Test successful sleep quiz gamification"""
    # Setup
    user_id = "12345"
    sleep_entry_id = "sleep-uuid"
    logged_at = datetime(2024, 1, 15, 8, 0)

    mock_award_xp.return_value = AsyncMock(return_value={
        'xp_awarded': 20,
        'leveled_up': False,
        'new_level': 4
    })()

    mock_update_streak.return_value = AsyncMock(return_value={
        'current_streak': 10,
        'milestone_reached': False
    })()

    mock_check_achievements.return_value = AsyncMock(return_value=[])()

    # Execute
    result = await gamification_service.process_sleep_quiz(
        user_id, sleep_entry_id, logged_at
    )

    # Assert
    assert result['xp_awarded'] == 20
    assert result['current_streak'] == 10
    assert 'sleep tracking streak' in result['message']


# Test process_tracking_entry
@pytest.mark.asyncio
@patch('src.services.gamification_service.award_xp')
@patch('src.services.gamification_service.update_streak')
@patch('src.services.gamification_service.check_and_award_achievements')
async def test_process_tracking_entry_exercise(
    mock_check_achievements,
    mock_update_streak,
    mock_award_xp,
    gamification_service
):
    """Test tracking entry for exercise category"""
    # Setup
    user_id = "12345"
    tracking_entry_id = "tracking-uuid"
    category_name = "Daily Exercise"
    logged_at = datetime(2024, 1, 15, 18, 0)

    mock_award_xp.return_value = AsyncMock(return_value={
        'xp_awarded': 10,
        'leveled_up': False,
        'new_level': 4
    })()

    mock_update_streak.return_value = AsyncMock(return_value={
        'current_streak': 3,
        'milestone_reached': False
    })()

    mock_check_achievements.return_value = AsyncMock(return_value=[])()

    # Execute
    result = await gamification_service.process_tracking_entry(
        user_id, tracking_entry_id, category_name, logged_at
    )

    # Assert
    assert result['xp_awarded'] == 10
    assert result['current_streak'] == 3
    # Verify streak type was mapped correctly (exercise)
    mock_update_streak.assert_called_once()
    call_args = mock_update_streak.call_args
    assert call_args.kwargs['streak_type'] == 'exercise'


@pytest.mark.asyncio
@patch('src.services.gamification_service.award_xp')
@patch('src.services.gamification_service.update_streak')
@patch('src.services.gamification_service.check_and_award_achievements')
async def test_process_tracking_entry_water(
    mock_check_achievements,
    mock_update_streak,
    mock_award_xp,
    gamification_service
):
    """Test tracking entry for water/hydration category"""
    # Setup
    user_id = "12345"
    tracking_entry_id = "tracking-uuid"
    category_name = "Water Intake"
    logged_at = datetime(2024, 1, 15, 18, 0)

    mock_award_xp.return_value = AsyncMock(return_value={
        'xp_awarded': 10,
        'leveled_up': False,
        'new_level': 4
    })()

    mock_update_streak.return_value = AsyncMock(return_value={
        'current_streak': 5,
        'milestone_reached': False
    })()

    mock_check_achievements.return_value = AsyncMock(return_value=[])()

    # Execute
    result = await gamification_service.process_tracking_entry(
        user_id, tracking_entry_id, category_name, logged_at
    )

    # Assert
    # Verify streak type was mapped to hydration
    call_args = mock_update_streak.call_args
    assert call_args.kwargs['streak_type'] == 'hydration'


# Test get_user_stats
@pytest.mark.asyncio
@patch('src.services.gamification_service.get_user_xp')
@patch('src.services.gamification_service.get_user_streaks')
async def test_get_user_stats_success(
    mock_get_streaks,
    mock_get_xp,
    gamification_service
):
    """Test getting user gamification stats"""
    # Setup
    user_id = "12345"

    mock_get_xp.return_value = AsyncMock(return_value={
        'current_xp': 350,
        'current_level': 5,
        'level_tier': 'bronze',
        'xp_in_current_level': 50,
        'xp_to_next_level': 50
    })()

    mock_get_streaks.return_value = AsyncMock(return_value={
        'medication': 7,
        'nutrition': 5,
        'exercise': 0
    })()

    # Execute
    result = await gamification_service.get_user_stats(user_id)

    # Assert
    assert result['success'] is True
    assert result['xp']['current_level'] == 5
    assert result['streaks']['medication'] == 7


# Test error handling
@pytest.mark.asyncio
@patch('src.services.gamification_service.award_xp')
async def test_process_reminder_completion_error(
    mock_award_xp,
    gamification_service
):
    """Test error handling in reminder completion"""
    # Setup
    user_id = "12345"
    reminder_id = "reminder-uuid"
    completed_at = datetime(2024, 1, 15, 10, 0)
    scheduled_time = "10:00"

    # Mock error
    mock_award_xp.side_effect = Exception("Database error")

    # Execute
    result = await gamification_service.process_reminder_completion(
        user_id, reminder_id, completed_at, scheduled_time
    )

    # Assert - returns empty result on error
    assert result['xp_awarded'] == 0
    assert result['level_up'] is False
    assert result['message'] == ''


# Test helper methods
def test_calculate_reminder_xp_on_time(gamification_service):
    """Test XP calculation for on-time completion"""
    completed_at = datetime(2024, 1, 15, 10, 15)
    scheduled_time = "10:00"  # 15 minutes late, within window

    base_xp, bonus_xp = gamification_service._calculate_reminder_xp(
        completed_at, scheduled_time
    )

    assert base_xp == 10
    assert bonus_xp == 5  # On-time bonus


def test_calculate_reminder_xp_late(gamification_service):
    """Test XP calculation for late completion"""
    completed_at = datetime(2024, 1, 15, 11, 0)
    scheduled_time = "10:00"  # 60 minutes late, outside window

    base_xp, bonus_xp = gamification_service._calculate_reminder_xp(
        completed_at, scheduled_time
    )

    assert base_xp == 10
    assert bonus_xp == 0  # No bonus


def test_map_category_to_streak_type_exercise(gamification_service):
    """Test category mapping for exercise"""
    streak_type = gamification_service._map_category_to_streak_type("Daily Exercise")
    assert streak_type == 'exercise'


def test_map_category_to_streak_type_water(gamification_service):
    """Test category mapping for hydration"""
    streak_type = gamification_service._map_category_to_streak_type("Water Intake")
    assert streak_type == 'hydration'


def test_map_category_to_streak_type_meditation(gamification_service):
    """Test category mapping for mindfulness"""
    streak_type = gamification_service._map_category_to_streak_type("Meditation")
    assert streak_type == 'mindfulness'


def test_map_category_to_streak_type_other(gamification_service):
    """Test category mapping for unknown category"""
    streak_type = gamification_service._map_category_to_streak_type("Random Category")
    assert streak_type == 'overall'
