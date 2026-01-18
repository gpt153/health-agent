"""Unit tests for Achievement System (src/gamification/achievement_system.py)"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, date, timezone, timedelta
from uuid import uuid4

from src.gamification.achievement_system import (
    check_and_award_achievements,
    get_user_achievements,
    get_achievement_progress,
    _check_completion_count,
    _check_streak_count,
    _check_xp_total,
    _check_level_reached,
)


# ============================================================================
# Achievement Checking and Award Tests
# ============================================================================

@pytest.mark.asyncio
async def test_check_and_award_achievements_first_completion():
    """Test unlocking first completion achievement"""
    user_id = "123456789"
    trigger_type = "completion"
    context = {"domain": "medication", "count": 1}

    mock_achievements = [
        {
            "id": str(uuid4()),
            "achievement_key": "first_med_completion",
            "name": "First Dose",
            "description": "Complete your first medication reminder",
            "icon": "💊",
            "xp_reward": 50,
            "tier": "bronze",
            "criteria": {
                "type": "completion_count",
                "domain": "medication",
                "count": 1
            }
        }
    ]

    mock_user_achievements = []  # No achievements unlocked yet

    with patch('src.gamification.achievement_system.queries.get_all_achievements', AsyncMock(return_value=mock_achievements)):
        with patch('src.gamification.achievement_system.queries.get_user_achievements', AsyncMock(return_value=mock_user_achievements)):
            with patch('src.gamification.achievement_system._check_completion_count', AsyncMock(return_value=True)):
                with patch('src.gamification.achievement_system.queries.unlock_achievement', AsyncMock()):
                    with patch('src.gamification.achievement_system.award_xp', AsyncMock()):
                        result = await check_and_award_achievements(user_id, trigger_type, context)

                        assert len(result) == 1
                        assert result[0]["name"] == "First Dose"
                        assert result[0]["xp_reward"] == 50


@pytest.mark.asyncio
async def test_check_and_award_achievements_already_unlocked():
    """Test that already unlocked achievements are skipped"""
    user_id = "123456789"
    achievement_id = str(uuid4())

    mock_achievements = [
        {
            "id": achievement_id,
            "achievement_key": "first_completion",
            "name": "First Steps",
            "xp_reward": 25,
            "criteria": {"type": "completion_count", "count": 1}
        }
    ]

    mock_user_achievements = [
        {
            "achievement_id": achievement_id,
            "unlocked_at": datetime.now(timezone.utc)
        }
    ]

    with patch('src.gamification.achievement_system.queries.get_all_achievements', AsyncMock(return_value=mock_achievements)):
        with patch('src.gamification.achievement_system.queries.get_user_achievements', AsyncMock(return_value=mock_user_achievements)):
            result = await check_and_award_achievements(user_id, "completion", {})

            # Should return empty list (achievement already unlocked)
            assert len(result) == 0


@pytest.mark.asyncio
async def test_check_and_award_achievements_multiple_unlocks():
    """Test unlocking multiple achievements at once"""
    user_id = "123456789"

    mock_achievements = [
        {
            "id": str(uuid4()),
            "achievement_key": "week_streak",
            "name": "Week Warrior",
            "xp_reward": 100,
            "criteria": {"type": "streak_count", "count": 7}
        },
        {
            "id": str(uuid4()),
            "achievement_key": "perfect_week",
            "name": "Perfect Week",
            "xp_reward": 150,
            "criteria": {"type": "completion_count", "period": "week", "count": 7}
        }
    ]

    with patch('src.gamification.achievement_system.queries.get_all_achievements', AsyncMock(return_value=mock_achievements)):
        with patch('src.gamification.achievement_system.queries.get_user_achievements', AsyncMock(return_value=[])):
            with patch('src.gamification.achievement_system._check_streak_count', AsyncMock(return_value=True)):
                with patch('src.gamification.achievement_system._check_completion_count', AsyncMock(return_value=True)):
                    with patch('src.gamification.achievement_system.queries.unlock_achievement', AsyncMock()):
                        with patch('src.gamification.achievement_system.award_xp', AsyncMock()):
                            result = await check_and_award_achievements(user_id, "streak", {"count": 7})

                            # Should unlock both achievements
                            assert len(result) == 2


@pytest.mark.asyncio
async def test_check_and_award_achievements_awards_xp():
    """Test that unlocking achievement awards XP"""
    user_id = "123456789"
    xp_reward = 200

    mock_achievement = {
        "id": str(uuid4()),
        "achievement_key": "level_10",
        "name": "Silver Tier",
        "xp_reward": xp_reward,
        "criteria": {"type": "level_reached", "level": 10}
    }

    with patch('src.gamification.achievement_system.queries.get_all_achievements', AsyncMock(return_value=[mock_achievement])):
        with patch('src.gamification.achievement_system.queries.get_user_achievements', AsyncMock(return_value=[])):
            with patch('src.gamification.achievement_system._check_level_reached', AsyncMock(return_value=True)):
                with patch('src.gamification.achievement_system.queries.unlock_achievement', AsyncMock()):
                    with patch('src.gamification.achievement_system.award_xp', AsyncMock()) as mock_award_xp:
                        await check_and_award_achievements(user_id, "level_up", {"level": 10})

                        # Should award XP
                        mock_award_xp.assert_called_once_with(
                            user_id,
                            xp_reward,
                            "achievement_unlock",
                            source_id=mock_achievement["achievement_key"]
                        )


# ============================================================================
# Criteria Checking Tests
# ============================================================================

@pytest.mark.asyncio
async def test_check_completion_count_met():
    """Test completion count criteria is met"""
    user_id = "123456789"
    criteria = {
        "type": "completion_count",
        "domain": "medication",
        "count": 10
    }
    context = {}

    with patch('src.gamification.achievement_system.queries.get_user_completion_count', AsyncMock(return_value=10)):
        result = await _check_completion_count(user_id, criteria, context)
        assert result is True


@pytest.mark.asyncio
async def test_check_completion_count_not_met():
    """Test completion count criteria not met"""
    user_id = "123456789"
    criteria = {
        "type": "completion_count",
        "domain": "medication",
        "count": 100
    }

    with patch('src.gamification.achievement_system.queries.get_user_completion_count', AsyncMock(return_value=50)):
        result = await _check_completion_count(user_id, criteria, {})
        assert result is False


@pytest.mark.asyncio
async def test_check_streak_count_met():
    """Test streak count criteria is met"""
    user_id = "123456789"
    criteria = {
        "type": "streak_count",
        "domain": "nutrition",
        "count": 30
    }

    with patch('src.gamification.achievement_system.queries.get_user_best_streak', AsyncMock(return_value=35)):
        result = await _check_streak_count(user_id, criteria, {})
        assert result is True


@pytest.mark.asyncio
async def test_check_streak_count_not_met():
    """Test streak count criteria not met"""
    user_id = "123456789"
    criteria = {
        "type": "streak_count",
        "domain": "exercise",
        "count": 60
    }

    with patch('src.gamification.achievement_system.queries.get_user_best_streak', AsyncMock(return_value=45)):
        result = await _check_streak_count(user_id, criteria, {})
        assert result is False


@pytest.mark.asyncio
async def test_check_xp_total_met():
    """Test XP total criteria is met"""
    user_id = "123456789"
    criteria = {
        "type": "xp_total",
        "xp": 5000
    }

    with patch('src.gamification.achievement_system.queries.get_user_xp_data', AsyncMock(return_value={"total_xp": 6000})):
        result = await _check_xp_total(user_id, criteria, {})
        assert result is True


@pytest.mark.asyncio
async def test_check_level_reached_met():
    """Test level reached criteria is met"""
    user_id = "123456789"
    criteria = {
        "type": "level_reached",
        "level": 20
    }

    with patch('src.gamification.achievement_system.queries.get_user_xp_data', AsyncMock(return_value={"level": 22})):
        result = await _check_level_reached(user_id, criteria, {})
        assert result is True


# ============================================================================
# Get User Achievements Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_user_achievements():
    """Test retrieving user achievements"""
    user_id = "123456789"

    mock_achievements = [
        {
            "achievement_id": str(uuid4()),
            "achievement_key": "first_completion",
            "name": "First Steps",
            "unlocked_at": datetime.now(timezone.utc),
            "progress": 100
        },
        {
            "achievement_id": str(uuid4()),
            "achievement_key": "week_streak",
            "name": "Week Warrior",
            "unlocked_at": datetime.now(timezone.utc),
            "progress": 100
        }
    ]

    with patch('src.gamification.achievement_system.queries.get_user_achievements', AsyncMock(return_value=mock_achievements)):
        result = await get_user_achievements(user_id)

        assert len(result) == 2
        assert all(ach["progress"] == 100 for ach in result)


@pytest.mark.asyncio
async def test_get_user_achievements_empty():
    """Test retrieving achievements for user with none unlocked"""
    user_id = "999999999"

    with patch('src.gamification.achievement_system.queries.get_user_achievements', AsyncMock(return_value=[])):
        result = await get_user_achievements(user_id)

        assert len(result) == 0


# ============================================================================
# Get Achievement Progress Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_achievement_progress():
    """Test getting progress toward specific achievement"""
    user_id = "123456789"
    achievement_key = "hundred_completions"

    mock_progress = {
        "achievement_key": achievement_key,
        "current": 75,
        "required": 100,
        "progress_percent": 75
    }

    with patch('src.gamification.achievement_system.queries.get_achievement_progress', AsyncMock(return_value=mock_progress)):
        result = await get_achievement_progress(user_id, achievement_key)

        assert result["current"] == 75
        assert result["required"] == 100
        assert result["progress_percent"] == 75


# ============================================================================
# Achievement Tier Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("tier,expected_min_xp", [
    ("bronze", 25),
    ("silver", 50),
    ("gold", 100),
    ("platinum", 250),
])
async def test_achievement_tiers_xp_rewards(tier, expected_min_xp):
    """Test that achievement tiers have appropriate XP rewards"""
    user_id = "123456789"

    mock_achievement = {
        "id": str(uuid4()),
        "achievement_key": f"{tier}_achievement",
        "name": f"{tier.title()} Achievement",
        "tier": tier,
        "xp_reward": expected_min_xp,
        "criteria": {"type": "completion_count", "count": 1}
    }

    with patch('src.gamification.achievement_system.queries.get_all_achievements', AsyncMock(return_value=[mock_achievement])):
        with patch('src.gamification.achievement_system.queries.get_user_achievements', AsyncMock(return_value=[])):
            with patch('src.gamification.achievement_system._check_completion_count', AsyncMock(return_value=True)):
                with patch('src.gamification.achievement_system.queries.unlock_achievement', AsyncMock()):
                    with patch('src.gamification.achievement_system.award_xp', AsyncMock()):
                        result = await check_and_award_achievements(user_id, "completion", {})

                        assert result[0]["xp_reward"] >= expected_min_xp
                        assert result[0]["tier"] == tier


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_check_and_award_achievements_database_error():
    """Test handling of database errors"""
    user_id = "123456789"

    with patch('src.gamification.achievement_system.queries.get_all_achievements', AsyncMock(side_effect=Exception("DB error"))):
        # Should handle gracefully
        result = await check_and_award_achievements(user_id, "completion", {})

        # Should return empty list on error
        assert result == []


@pytest.mark.asyncio
async def test_check_and_award_achievements_malformed_criteria():
    """Test handling of malformed achievement criteria"""
    user_id = "123456789"

    mock_achievement = {
        "id": str(uuid4()),
        "achievement_key": "broken_achievement",
        "criteria": None  # Malformed
    }

    with patch('src.gamification.achievement_system.queries.get_all_achievements', AsyncMock(return_value=[mock_achievement])):
        with patch('src.gamification.achievement_system.queries.get_user_achievements', AsyncMock(return_value=[])):
            # Should handle gracefully without crashing
            result = await check_and_award_achievements(user_id, "completion", {})

            assert isinstance(result, list)


@pytest.mark.asyncio
async def test_check_and_award_achievements_concurrent_unlocks():
    """Test handling concurrent achievement unlock attempts"""
    user_id = "123456789"

    mock_achievement = {
        "id": str(uuid4()),
        "achievement_key": "test_achievement",
        "name": "Test",
        "xp_reward": 50,
        "criteria": {"type": "completion_count", "count": 1}
    }

    with patch('src.gamification.achievement_system.queries.get_all_achievements', AsyncMock(return_value=[mock_achievement])):
        with patch('src.gamification.achievement_system.queries.get_user_achievements', AsyncMock(return_value=[])):
            with patch('src.gamification.achievement_system._check_completion_count', AsyncMock(return_value=True)):
                with patch('src.gamification.achievement_system.queries.unlock_achievement', AsyncMock()):
                    with patch('src.gamification.achievement_system.award_xp', AsyncMock()):
                        # Simulate concurrent calls
                        import asyncio
                        results = await asyncio.gather(
                            check_and_award_achievements(user_id, "completion", {}),
                            check_and_award_achievements(user_id, "completion", {}),
                            check_and_award_achievements(user_id, "completion", {})
                        )

                        # Should handle gracefully
                        assert all(isinstance(r, list) for r in results)


# ============================================================================
# Domain-Specific Achievement Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("domain", [
    "medication",
    "nutrition",
    "exercise",
    "sleep",
    "hydration",
    "mindfulness"
])
async def test_domain_specific_achievements(domain):
    """Test achievements for different health domains"""
    user_id = "123456789"

    mock_achievement = {
        "id": str(uuid4()),
        "achievement_key": f"{domain}_master",
        "name": f"{domain.title()} Master",
        "xp_reward": 200,
        "criteria": {
            "type": "completion_count",
            "domain": domain,
            "count": 100
        }
    }

    with patch('src.gamification.achievement_system.queries.get_all_achievements', AsyncMock(return_value=[mock_achievement])):
        with patch('src.gamification.achievement_system.queries.get_user_achievements', AsyncMock(return_value=[])):
            with patch('src.gamification.achievement_system._check_completion_count', AsyncMock(return_value=True)):
                with patch('src.gamification.achievement_system.queries.unlock_achievement', AsyncMock()):
                    with patch('src.gamification.achievement_system.award_xp', AsyncMock()):
                        result = await check_and_award_achievements(user_id, "completion", {"domain": domain})

                        assert len(result) == 1
                        assert domain in result[0]["achievement_key"]


# ============================================================================
# Milestone Achievement Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("streak_milestone,expected_tier", [
    (7, "bronze"),
    (14, "silver"),
    (30, "gold"),
    (60, "platinum"),
    (100, "platinum"),
])
async def test_streak_milestone_achievements(streak_milestone, expected_tier):
    """Test streak milestone achievements"""
    user_id = "123456789"

    mock_achievement = {
        "id": str(uuid4()),
        "achievement_key": f"streak_{streak_milestone}",
        "name": f"{streak_milestone}-Day Streak",
        "tier": expected_tier,
        "xp_reward": streak_milestone * 5,
        "criteria": {
            "type": "streak_count",
            "count": streak_milestone
        }
    }

    with patch('src.gamification.achievement_system.queries.get_all_achievements', AsyncMock(return_value=[mock_achievement])):
        with patch('src.gamification.achievement_system.queries.get_user_achievements', AsyncMock(return_value=[])):
            with patch('src.gamification.achievement_system._check_streak_count', AsyncMock(return_value=True)):
                with patch('src.gamification.achievement_system.queries.unlock_achievement', AsyncMock()):
                    with patch('src.gamification.achievement_system.award_xp', AsyncMock()):
                        result = await check_and_award_achievements(user_id, "streak", {"count": streak_milestone})

                        assert result[0]["tier"] == expected_tier
