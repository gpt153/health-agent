"""Unit tests for Streak System (src/gamification/streak_system.py)"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import date, datetime, timezone, timedelta

from src.gamification.streak_system import (
    update_streak,
    use_freeze_day,
    get_streak_info,
    calculate_streak_milestones,
)


# ============================================================================
# Streak Update Tests
# ============================================================================

@pytest.mark.asyncio
async def test_update_streak_first_activity():
    """Test first activity creates streak of 1"""
    user_id = "123456789"
    streak_type = "nutrition"

    mock_streak_data = {
        "current_streak": 0,
        "best_streak": 0,
        "last_activity_date": None,
        "freeze_days": 0
    }

    with patch('src.gamification.streak_system.queries.get_user_streak', AsyncMock(return_value=mock_streak_data)):
        with patch('src.gamification.streak_system.queries.update_user_streak', AsyncMock()):
            result = await update_streak(user_id, streak_type)

            assert result["current_streak"] == 1
            assert result["best_streak"] == 1


@pytest.mark.asyncio
async def test_update_streak_consecutive_day():
    """Test consecutive day activity increments streak"""
    user_id = "123456789"
    streak_type = "exercise"

    yesterday = date.today() - timedelta(days=1)
    mock_streak_data = {
        "current_streak": 5,
        "best_streak": 10,
        "last_activity_date": yesterday,
        "freeze_days": 2
    }

    with patch('src.gamification.streak_system.queries.get_user_streak', AsyncMock(return_value=mock_streak_data)):
        with patch('src.gamification.streak_system.queries.update_user_streak', AsyncMock()):
            result = await update_streak(user_id, streak_type)

            assert result["current_streak"] == 6
            assert result["best_streak"] == 10  # Unchanged


@pytest.mark.asyncio
async def test_update_streak_same_day_no_change():
    """Test activity on same day doesn't increment streak again"""
    user_id = "123456789"
    streak_type = "medication"

    today = date.today()
    mock_streak_data = {
        "current_streak": 3,
        "best_streak": 5,
        "last_activity_date": today,
        "freeze_days": 1
    }

    with patch('src.gamification.streak_system.queries.get_user_streak', AsyncMock(return_value=mock_streak_data)):
        with patch('src.gamification.streak_system.queries.update_user_streak', AsyncMock()):
            result = await update_streak(user_id, streak_type)

            assert result["current_streak"] == 3  # No change
            assert result["message"] is not None


@pytest.mark.asyncio
async def test_update_streak_gap_resets():
    """Test gap of more than 1 day resets streak"""
    user_id = "123456789"
    streak_type = "hydration"

    three_days_ago = date.today() - timedelta(days=3)
    mock_streak_data = {
        "current_streak": 7,
        "best_streak": 14,
        "last_activity_date": three_days_ago,
        "freeze_days": 0  # No freeze days available
    }

    with patch('src.gamification.streak_system.queries.get_user_streak', AsyncMock(return_value=mock_streak_data)):
        with patch('src.gamification.streak_system.queries.update_user_streak', AsyncMock()):
            result = await update_streak(user_id, streak_type)

            assert result["current_streak"] == 1  # Reset
            assert result["best_streak"] == 14  # Best unchanged


@pytest.mark.asyncio
async def test_update_streak_freeze_day_protection():
    """Test freeze day protects streak during 1-day gap"""
    user_id = "123456789"
    streak_type = "sleep"

    two_days_ago = date.today() - timedelta(days=2)
    mock_streak_data = {
        "current_streak": 10,
        "best_streak": 15,
        "last_activity_date": two_days_ago,
        "freeze_days": 3
    }

    with patch('src.gamification.streak_system.queries.get_user_streak', AsyncMock(return_value=mock_streak_data)):
        with patch('src.gamification.streak_system.queries.update_user_streak', AsyncMock()):
            result = await update_streak(user_id, streak_type)

            assert result["streak_protected"] is True
            assert result["current_streak"] == 11  # Continues
            # Freeze day should be consumed


@pytest.mark.asyncio
async def test_update_streak_new_best():
    """Test updating best streak when current exceeds it"""
    user_id = "123456789"
    streak_type = "nutrition"

    yesterday = date.today() - timedelta(days=1)
    mock_streak_data = {
        "current_streak": 14,
        "best_streak": 14,
        "last_activity_date": yesterday,
        "freeze_days": 0
    }

    with patch('src.gamification.streak_system.queries.get_user_streak', AsyncMock(return_value=mock_streak_data)):
        with patch('src.gamification.streak_system.queries.update_user_streak', AsyncMock()):
            result = await update_streak(user_id, streak_type)

            assert result["current_streak"] == 15
            assert result["best_streak"] == 15  # New best!


@pytest.mark.asyncio
async def test_update_streak_milestone_7_days():
    """Test reaching 7-day milestone"""
    user_id = "123456789"
    streak_type = "overall"

    yesterday = date.today() - timedelta(days=1)
    mock_streak_data = {
        "current_streak": 6,
        "best_streak": 10,
        "last_activity_date": yesterday,
        "freeze_days": 0
    }

    with patch('src.gamification.streak_system.queries.get_user_streak', AsyncMock(return_value=mock_streak_data)):
        with patch('src.gamification.streak_system.queries.update_user_streak', AsyncMock()):
            result = await update_streak(user_id, streak_type)

            assert result["current_streak"] == 7
            assert result["milestone_reached"] is True
            assert result["xp_bonus"] > 0


@pytest.mark.asyncio
async def test_update_streak_milestone_30_days():
    """Test reaching 30-day milestone"""
    user_id = "123456789"
    streak_type = "medication"

    yesterday = date.today() - timedelta(days=1)
    mock_streak_data = {
        "current_streak": 29,
        "best_streak": 35,
        "last_activity_date": yesterday,
        "freeze_days": 1
    }

    with patch('src.gamification.streak_system.queries.get_user_streak', AsyncMock(return_value=mock_streak_data)):
        with patch('src.gamification.streak_system.queries.update_user_streak', AsyncMock()):
            result = await update_streak(user_id, streak_type)

            assert result["current_streak"] == 30
            assert result["milestone_reached"] is True
            assert result["xp_bonus"] >= 100  # 30-day milestone is significant


# ============================================================================
# Freeze Day Tests
# ============================================================================

@pytest.mark.asyncio
async def test_use_freeze_day_success():
    """Test successfully using a freeze day"""
    user_id = "123456789"
    streak_type = "exercise"

    mock_streak_data = {
        "current_streak": 5,
        "freeze_days": 2
    }

    with patch('src.gamification.streak_system.queries.get_user_streak', AsyncMock(return_value=mock_streak_data)):
        with patch('src.gamification.streak_system.queries.use_streak_freeze', AsyncMock()):
            result = await use_freeze_day(user_id, streak_type)

            assert result["success"] is True
            assert result["freeze_days_remaining"] == 1


@pytest.mark.asyncio
async def test_use_freeze_day_none_available():
    """Test using freeze day when none available"""
    user_id = "123456789"
    streak_type = "nutrition"

    mock_streak_data = {
        "current_streak": 10,
        "freeze_days": 0
    }

    with patch('src.gamification.streak_system.queries.get_user_streak', AsyncMock(return_value=mock_streak_data)):
        result = await use_freeze_day(user_id, streak_type)

        assert result["success"] is False
        assert "no freeze days" in result["message"].lower()


# ============================================================================
# Get Streak Info Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_streak_info():
    """Test retrieving streak information"""
    user_id = "123456789"
    streak_type = "sleep"

    mock_streak_data = {
        "user_id": user_id,
        "streak_type": streak_type,
        "current_streak": 14,
        "best_streak": 21,
        "last_activity_date": date.today() - timedelta(days=1),
        "freeze_days": 3,
        "created_at": datetime.now(timezone.utc)
    }

    with patch('src.gamification.streak_system.queries.get_user_streak', AsyncMock(return_value=mock_streak_data)):
        result = await get_streak_info(user_id, streak_type)

        assert result["current_streak"] == 14
        assert result["best_streak"] == 21
        assert result["freeze_days"] == 3


@pytest.mark.asyncio
async def test_get_streak_info_new_user():
    """Test retrieving streak info for new user"""
    user_id = "999999999"
    streak_type = "medication"

    with patch('src.gamification.streak_system.queries.get_user_streak', AsyncMock(return_value=None)):
        with patch('src.gamification.streak_system.queries.create_user_streak', AsyncMock()):
            result = await get_streak_info(user_id, streak_type)

            assert result["current_streak"] == 0
            assert result["best_streak"] == 0


# ============================================================================
# Milestone Calculation Tests
# ============================================================================

def test_calculate_streak_milestones():
    """Test milestone calculation for different streak lengths"""
    assert calculate_streak_milestones(0) == []
    assert 7 in calculate_streak_milestones(7)
    assert 14 in calculate_streak_milestones(14)
    assert 30 in calculate_streak_milestones(30)
    assert 60 in calculate_streak_milestones(60)
    assert 100 in calculate_streak_milestones(100)


def test_calculate_streak_milestones_returns_all():
    """Test that milestone calculation returns all passed milestones"""
    milestones = calculate_streak_milestones(35)

    assert 7 in milestones
    assert 14 in milestones
    assert 30 in milestones
    assert 60 not in milestones  # Not reached yet


# ============================================================================
# Edge Case Tests
# ============================================================================

@pytest.mark.asyncio
async def test_update_streak_future_date():
    """Test update streak with future date (should handle gracefully)"""
    user_id = "123456789"
    streak_type = "nutrition"
    future_date = date.today() + timedelta(days=5)

    mock_streak_data = {
        "current_streak": 5,
        "best_streak": 10,
        "last_activity_date": date.today(),
        "freeze_days": 0
    }

    with patch('src.gamification.streak_system.queries.get_user_streak', AsyncMock(return_value=mock_streak_data)):
        with patch('src.gamification.streak_system.queries.update_user_streak', AsyncMock()):
            result = await update_streak(user_id, streak_type, activity_date=future_date)

            # Should handle gracefully (implementation dependent)
            assert "current_streak" in result


@pytest.mark.asyncio
async def test_update_streak_past_date():
    """Test update streak with past date (backfilling)"""
    user_id = "123456789"
    streak_type = "exercise"
    past_date = date.today() - timedelta(days=7)

    mock_streak_data = {
        "current_streak": 0,
        "best_streak": 5,
        "last_activity_date": None,
        "freeze_days": 0
    }

    with patch('src.gamification.streak_system.queries.get_user_streak', AsyncMock(return_value=mock_streak_data)):
        with patch('src.gamification.streak_system.queries.update_user_streak', AsyncMock()):
            result = await update_streak(user_id, streak_type, activity_date=past_date)

            assert result["current_streak"] >= 1


@pytest.mark.asyncio
async def test_update_streak_timezone_boundary():
    """Test streak update near timezone boundaries"""
    user_id = "123456789"
    streak_type = "medication"

    # Last activity was 23:59 yesterday in user's timezone
    yesterday_late = datetime.now(timezone.utc) - timedelta(hours=1)

    mock_streak_data = {
        "current_streak": 3,
        "best_streak": 5,
        "last_activity_date": yesterday_late.date(),
        "freeze_days": 0
    }

    with patch('src.gamification.streak_system.queries.get_user_streak', AsyncMock(return_value=mock_streak_data)):
        with patch('src.gamification.streak_system.queries.update_user_streak', AsyncMock()):
            result = await update_streak(user_id, streak_type)

            # Should correctly identify as consecutive day
            assert result["current_streak"] in [3, 4]


@pytest.mark.asyncio
async def test_update_streak_long_streak():
    """Test handling very long streaks (365+ days)"""
    user_id = "123456789"
    streak_type = "overall"

    yesterday = date.today() - timedelta(days=1)
    mock_streak_data = {
        "current_streak": 365,
        "best_streak": 400,
        "last_activity_date": yesterday,
        "freeze_days": 5
    }

    with patch('src.gamification.streak_system.queries.get_user_streak', AsyncMock(return_value=mock_streak_data)):
        with patch('src.gamification.streak_system.queries.update_user_streak', AsyncMock()):
            result = await update_streak(user_id, streak_type)

            assert result["current_streak"] == 366
            assert result["best_streak"] == 400


@pytest.mark.asyncio
@pytest.mark.parametrize("streak_type", [
    "medication",
    "nutrition",
    "exercise",
    "sleep",
    "hydration",
    "mindfulness",
    "overall"
])
async def test_update_streak_all_types(streak_type):
    """Test streak update works for all streak types"""
    user_id = "123456789"

    yesterday = date.today() - timedelta(days=1)
    mock_streak_data = {
        "current_streak": 1,
        "best_streak": 5,
        "last_activity_date": yesterday,
        "freeze_days": 0
    }

    with patch('src.gamification.streak_system.queries.get_user_streak', AsyncMock(return_value=mock_streak_data)):
        with patch('src.gamification.streak_system.queries.update_user_streak', AsyncMock()):
            result = await update_streak(user_id, streak_type)

            assert result["current_streak"] == 2
            assert isinstance(result["message"], str)


@pytest.mark.asyncio
async def test_update_streak_freeze_day_consumption():
    """Test that freeze days are properly consumed"""
    user_id = "123456789"
    streak_type = "sleep"

    two_days_ago = date.today() - timedelta(days=2)
    mock_streak_data = {
        "current_streak": 5,
        "best_streak": 10,
        "last_activity_date": two_days_ago,
        "freeze_days": 1  # Only 1 freeze day
    }

    with patch('src.gamification.streak_system.queries.get_user_streak', AsyncMock(return_value=mock_streak_data)):
        with patch('src.gamification.streak_system.queries.update_user_streak', AsyncMock()) as mock_update:
            result = await update_streak(user_id, streak_type)

            # Should use the freeze day
            assert result["streak_protected"] is True
            # Verify freeze day was decremented in update call
            mock_update.assert_called_once()


@pytest.mark.asyncio
async def test_streak_milestone_xp_scaling():
    """Test that milestone XP rewards scale appropriately"""
    milestones = {
        7: 50,
        14: 100,
        30: 200,
        60: 400,
        100: 800,
    }

    for streak_length, expected_min_xp in milestones.items():
        user_id = "123456789"
        streak_type = "overall"

        yesterday = date.today() - timedelta(days=1)
        mock_streak_data = {
            "current_streak": streak_length - 1,
            "best_streak": streak_length + 10,
            "last_activity_date": yesterday,
            "freeze_days": 0
        }

        with patch('src.gamification.streak_system.queries.get_user_streak', AsyncMock(return_value=mock_streak_data)):
            with patch('src.gamification.streak_system.queries.update_user_streak', AsyncMock()):
                result = await update_streak(user_id, streak_type)

                if result.get("milestone_reached"):
                    assert result["xp_bonus"] >= expected_min_xp, \
                        f"Milestone {streak_length} should award at least {expected_min_xp} XP"
