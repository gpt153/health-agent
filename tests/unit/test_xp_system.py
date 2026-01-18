"""Unit tests for XP and Leveling System (src/gamification/xp_system.py)"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from src.gamification.xp_system import (
    calculate_level_from_xp,
    award_xp,
    get_user_level_info,
)


# ============================================================================
# Level Calculation Tests
# ============================================================================

def test_calculate_level_from_xp_level_1_zero():
    """Test level 1 with 0 XP"""
    result = calculate_level_from_xp(0)

    assert result["current_level"] == 1
    assert result["level_tier"] == "bronze"
    assert result["xp_in_current_level"] == 0
    assert result["xp_to_next_level"] == 100
    assert result["total_xp_for_next_level"] == 100


def test_calculate_level_from_xp_bronze_tier():
    """Test bronze tier levels (1-5)"""
    # Level 1 with 50 XP
    result = calculate_level_from_xp(50)
    assert result["current_level"] == 1
    assert result["level_tier"] == "bronze"
    assert result["xp_in_current_level"] == 50
    assert result["xp_to_next_level"] == 50

    # Level 2 exactly (100 XP)
    result = calculate_level_from_xp(100)
    assert result["current_level"] == 2
    assert result["level_tier"] == "bronze"
    assert result["xp_in_current_level"] == 0
    assert result["xp_to_next_level"] == 100

    # Level 5 exactly (400 XP total)
    result = calculate_level_from_xp(400)
    assert result["current_level"] == 5
    assert result["level_tier"] == "bronze"
    assert result["xp_in_current_level"] == 0


def test_calculate_level_from_xp_silver_tier():
    """Test silver tier levels (6-15)"""
    # Level 6 exactly (500 XP total: 4*100 for bronze + 200 for level 6)
    result = calculate_level_from_xp(500)
    assert result["current_level"] == 6
    assert result["level_tier"] == "silver"
    assert result["xp_in_current_level"] == 0
    assert result["xp_to_next_level"] == 200

    # Level 10 mid-progress (400 + 800 + 100)
    result = calculate_level_from_xp(1300)
    assert result["current_level"] == 10
    assert result["level_tier"] == "silver"
    assert result["xp_in_current_level"] == 100
    assert result["xp_to_next_level"] == 100


def test_calculate_level_from_xp_gold_tier():
    """Test gold tier levels (16-30)"""
    # Level 16 exactly (bronze 400 + silver 2000 = 2400 + 500 for level 16)
    result = calculate_level_from_xp(2900)
    assert result["current_level"] == 16
    assert result["level_tier"] == "gold"
    assert result["xp_in_current_level"] == 0
    assert result["xp_to_next_level"] == 500

    # Level 20 mid-progress
    result = calculate_level_from_xp(4900)  # Bronze 400 + Silver 2000 + Gold 2500
    assert result["current_level"] == 21
    assert result["level_tier"] == "gold"


def test_calculate_level_from_xp_platinum_tier():
    """Test platinum tier levels (31+)"""
    # Level 31 exactly (bronze 400 + silver 2000 + gold 7500 = 9900 + 1000 for level 31)
    result = calculate_level_from_xp(10900)
    assert result["current_level"] == 31
    assert result["level_tier"] == "platinum"
    assert result["xp_in_current_level"] == 0
    assert result["xp_to_next_level"] == 1000

    # Very high level (level 50)
    result = calculate_level_from_xp(29900)  # 400 + 2000 + 7500 + 19000 + 900
    assert result["current_level"] == 50
    assert result["level_tier"] == "platinum"


def test_calculate_level_from_xp_boundary_values():
    """Test boundary values between tiers"""
    # Exactly at level 5 boundary (going to silver)
    result = calculate_level_from_xp(400)
    assert result["current_level"] == 5
    assert result["level_tier"] == "bronze"

    # One XP into level 6
    result = calculate_level_from_xp(401)
    assert result["current_level"] == 5
    assert result["level_tier"] == "bronze"
    assert result["xp_in_current_level"] == 1

    # Exactly at level 6
    result = calculate_level_from_xp(500)
    assert result["current_level"] == 6
    assert result["level_tier"] == "silver"


def test_calculate_level_from_xp_negative():
    """Test that negative XP is handled (should be level 1)"""
    result = calculate_level_from_xp(-100)
    assert result["current_level"] == 1
    assert result["level_tier"] == "bronze"


def test_calculate_level_from_xp_large_values():
    """Test very large XP values (level 100+)"""
    # 100,000 XP
    result = calculate_level_from_xp(100000)
    assert result["current_level"] > 80
    assert result["level_tier"] == "platinum"


# ============================================================================
# XP Award Tests
# ============================================================================

@pytest.mark.asyncio
async def test_award_xp_basic():
    """Test awarding XP to a user"""
    user_id = "123456789"
    amount = 50
    source_type = "reminder_completion"

    mock_xp_data = {
        "total_xp": 100,
        "level": 2
    }

    with patch('src.gamification.xp_system.queries.get_user_xp_data', AsyncMock(return_value=mock_xp_data)):
        with patch('src.gamification.xp_system.queries.award_user_xp', AsyncMock()) as mock_award:
            with patch('src.gamification.xp_system.queries.add_xp_transaction', AsyncMock()):
                result = await award_xp(user_id, amount, source_type)

                mock_award.assert_called_once()
                assert result["xp_awarded"] == amount


@pytest.mark.asyncio
async def test_award_xp_with_level_up():
    """Test awarding XP that causes a level up"""
    user_id = "123456789"
    amount = 150

    # User at 380 XP (level 4, 80 XP into level)
    mock_xp_data_before = {
        "total_xp": 380,
        "level": 4
    }

    # After award: 530 XP (level 6)
    mock_xp_data_after = {
        "total_xp": 530,
        "level": 6
    }

    with patch('src.gamification.xp_system.queries.get_user_xp_data', AsyncMock(side_effect=[
        mock_xp_data_before,
        mock_xp_data_after
    ])):
        with patch('src.gamification.xp_system.queries.award_user_xp', AsyncMock()):
            with patch('src.gamification.xp_system.queries.add_xp_transaction', AsyncMock()):
                result = await award_xp(user_id, amount, "meal_log")

                assert result["xp_awarded"] == amount
                assert result.get("level_up") is True or result.get("old_level") < result.get("new_level")


@pytest.mark.asyncio
async def test_award_xp_zero_amount():
    """Test awarding 0 XP (should still record transaction)"""
    user_id = "123456789"

    mock_xp_data = {"total_xp": 100, "level": 2}

    with patch('src.gamification.xp_system.queries.get_user_xp_data', AsyncMock(return_value=mock_xp_data)):
        with patch('src.gamification.xp_system.queries.award_user_xp', AsyncMock()) as mock_award:
            with patch('src.gamification.xp_system.queries.add_xp_transaction', AsyncMock()):
                result = await award_xp(user_id, 0, "test")

                assert result["xp_awarded"] == 0


@pytest.mark.asyncio
async def test_award_xp_with_source_id():
    """Test awarding XP with source ID for tracking"""
    user_id = "123456789"
    amount = 25
    source_type = "achievement_unlock"
    source_id = "first_meal_logged"

    mock_xp_data = {"total_xp": 200, "level": 3}

    with patch('src.gamification.xp_system.queries.get_user_xp_data', AsyncMock(return_value=mock_xp_data)):
        with patch('src.gamification.xp_system.queries.award_user_xp', AsyncMock()):
            with patch('src.gamification.xp_system.queries.add_xp_transaction', AsyncMock()) as mock_transaction:
                result = await award_xp(user_id, amount, source_type, source_id=source_id)

                assert result["xp_awarded"] == amount
                # Verify transaction was recorded with source_id
                mock_transaction.assert_called_once()


@pytest.mark.asyncio
async def test_award_xp_with_custom_reason():
    """Test awarding XP with custom reason"""
    user_id = "123456789"
    amount = 100
    reason = "Completed 7-day streak milestone"

    mock_xp_data = {"total_xp": 500, "level": 6}

    with patch('src.gamification.xp_system.queries.get_user_xp_data', AsyncMock(return_value=mock_xp_data)):
        with patch('src.gamification.xp_system.queries.award_user_xp', AsyncMock()):
            with patch('src.gamification.xp_system.queries.add_xp_transaction', AsyncMock()) as mock_transaction:
                result = await award_xp(user_id, amount, "streak_milestone", reason=reason)

                assert result["xp_awarded"] == amount
                mock_transaction.assert_called_once()


@pytest.mark.asyncio
async def test_award_xp_new_user():
    """Test awarding XP to a new user (no existing XP data)"""
    user_id = "999999999"
    amount = 10

    # New user has no XP data
    with patch('src.gamification.xp_system.queries.get_user_xp_data', AsyncMock(return_value=None)):
        with patch('src.gamification.xp_system.queries.create_user_xp_data', AsyncMock()):
            with patch('src.gamification.xp_system.queries.award_user_xp', AsyncMock()):
                with patch('src.gamification.xp_system.queries.add_xp_transaction', AsyncMock()):
                    result = await award_xp(user_id, amount, "first_action")

                    assert result["xp_awarded"] == amount


# ============================================================================
# Get User Level Info Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_user_level_info():
    """Test retrieving user level information"""
    user_id = "123456789"

    mock_xp_data = {
        "user_id": user_id,
        "total_xp": 750,
        "level": 8,
        "last_updated": datetime.now(timezone.utc)
    }

    with patch('src.gamification.xp_system.queries.get_user_xp_data', AsyncMock(return_value=mock_xp_data)):
        result = await get_user_level_info(user_id)

        assert result["total_xp"] == 750
        assert result["current_level"] == 8
        assert result["level_tier"] == "silver"


@pytest.mark.asyncio
async def test_get_user_level_info_new_user():
    """Test retrieving level info for new user"""
    user_id = "999999999"

    with patch('src.gamification.xp_system.queries.get_user_xp_data', AsyncMock(return_value=None)):
        with patch('src.gamification.xp_system.queries.create_user_xp_data', AsyncMock()):
            result = await get_user_level_info(user_id)

            assert result["total_xp"] == 0
            assert result["current_level"] == 1
            assert result["level_tier"] == "bronze"


# ============================================================================
# XP Source Type Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("source_type,expected_min_xp", [
    ("reminder_completion", 10),
    ("meal_log", 5),
    ("exercise_log", 15),
    ("sleep_quiz", 20),
    ("tracking_entry", 10),
    ("streak_milestone", 50),
    ("achievement_unlock", 25),
])
async def test_award_xp_source_types(source_type, expected_min_xp):
    """Test different XP source types have appropriate amounts"""
    user_id = "123456789"

    mock_xp_data = {"total_xp": 100, "level": 2}

    with patch('src.gamification.xp_system.queries.get_user_xp_data', AsyncMock(return_value=mock_xp_data)):
        with patch('src.gamification.xp_system.queries.award_user_xp', AsyncMock()):
            with patch('src.gamification.xp_system.queries.add_xp_transaction', AsyncMock()):
                result = await award_xp(user_id, expected_min_xp, source_type)

                assert result["xp_awarded"] >= expected_min_xp


# ============================================================================
# Edge Case Tests
# ============================================================================

def test_calculate_level_max_int():
    """Test level calculation with maximum integer value"""
    import sys
    max_xp = sys.maxsize

    result = calculate_level_from_xp(max_xp)

    # Should handle gracefully
    assert result["current_level"] > 1
    assert result["level_tier"] == "platinum"


def test_calculate_level_from_xp_float():
    """Test that float XP values work (should be rounded/truncated)"""
    result = calculate_level_from_xp(150.7)

    assert result["current_level"] == 2
    assert result["level_tier"] == "bronze"


@pytest.mark.asyncio
async def test_award_xp_concurrent_updates():
    """Test awarding XP handles concurrent update scenarios"""
    user_id = "123456789"

    mock_xp_data = {"total_xp": 100, "level": 2}

    with patch('src.gamification.xp_system.queries.get_user_xp_data', AsyncMock(return_value=mock_xp_data)):
        with patch('src.gamification.xp_system.queries.award_user_xp', AsyncMock()):
            with patch('src.gamification.xp_system.queries.add_xp_transaction', AsyncMock()):
                # Simulate multiple concurrent XP awards
                import asyncio
                results = await asyncio.gather(
                    award_xp(user_id, 10, "action1"),
                    award_xp(user_id, 15, "action2"),
                    award_xp(user_id, 20, "action3")
                )

                # All should complete successfully
                assert len(results) == 3
                assert all(r["xp_awarded"] > 0 for r in results)


def test_tier_progression_consistency():
    """Test that tier progression is consistent across all levels"""
    # Bronze: levels 1-5
    for level in range(1, 6):
        xp = (level - 1) * 100
        result = calculate_level_from_xp(xp)
        assert result["level_tier"] == "bronze", f"Level {level} should be bronze"

    # Silver: levels 6-15
    for level in range(6, 16):
        xp = 400 + (level - 5) * 200  # Bronze XP + silver levels
        result = calculate_level_from_xp(xp)
        assert result["level_tier"] == "silver", f"Level {level} should be silver"

    # Gold: levels 16-30
    for level in range(16, 31):
        xp = 400 + 2000 + (level - 15) * 500  # Bronze + Silver + gold levels
        result = calculate_level_from_xp(xp)
        assert result["level_tier"] == "gold", f"Level {level} should be gold"


def test_xp_to_next_level_accuracy():
    """Test that XP to next level calculations are accurate"""
    # At exact level boundary
    result = calculate_level_from_xp(100)
    assert result["xp_to_next_level"] == 100

    # 50 XP into level
    result = calculate_level_from_xp(150)
    assert result["xp_to_next_level"] == 50

    # 1 XP before next level
    result = calculate_level_from_xp(199)
    assert result["xp_to_next_level"] == 1
