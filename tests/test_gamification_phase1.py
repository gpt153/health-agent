"""
Test Suite for Gamification Phase 1: Foundation

Tests XP system, streak tracking, and achievement system
"""

import pytest
from datetime import date, timedelta
from src.gamification import (
    award_xp,
    get_user_xp,
    calculate_level_from_xp,
    update_streak,
    get_user_streaks,
    use_streak_freeze,
    check_and_award_achievements,
    get_user_achievements,
)
from src.gamification import mock_store


@pytest.fixture(autouse=True)
def reset_mock_store():
    """Reset mock store before each test"""
    mock_store._user_xp_store.clear()
    mock_store._xp_transactions_store.clear()
    mock_store._user_streaks_store.clear()
    mock_store._user_achievements_store.clear()
    mock_store.init_achievements()
    yield


# ============================================
# XP System Tests
# ============================================

@pytest.mark.asyncio
async def test_level_calculation():
    """Test level calculation from XP"""
    # Level 1 (Bronze)
    result = calculate_level_from_xp(0)
    assert result['current_level'] == 1
    assert result['level_tier'] == 'bronze'

    # Level 5 (Bronze)
    result = calculate_level_from_xp(400)
    assert result['current_level'] == 5
    assert result['level_tier'] == 'bronze'

    # Level 6 (Silver) - Need 400 (Bronze) + 200 (first Silver level) = 600 XP
    result = calculate_level_from_xp(600)
    assert result['current_level'] == 6
    assert result['level_tier'] == 'silver'

    # Level 15 (Silver) - Need 400 (Bronze) + 2000 (10 Silver levels) = 2400 XP
    result = calculate_level_from_xp(2400)
    assert result['current_level'] == 15
    assert result['level_tier'] == 'silver'

    # Level 16 (Gold) - Need 2400 (to level 15) + 500 (first Gold level) = 2900 XP
    result = calculate_level_from_xp(2900)
    assert result['current_level'] == 16
    assert result['level_tier'] == 'gold'

    # Level 30 (Gold) - Need 400 (Bronze) + 2000 (Silver) + 7500 (15 Gold levels) = 9900 XP
    result = calculate_level_from_xp(9900)
    assert result['current_level'] == 30
    assert result['level_tier'] == 'gold'

    # Level 31 (Platinum) - Need 9900 + 1000 = 10900 XP
    result = calculate_level_from_xp(10900)
    assert result['current_level'] == 31
    assert result['level_tier'] == 'platinum'


@pytest.mark.asyncio
async def test_award_xp_basic():
    """Test basic XP award"""
    user_id = "test_user_1"

    result = await award_xp(
        user_id=user_id,
        amount=50,
        source_type="reminder",
        reason="Completed medication reminder"
    )

    assert result['new_total_xp'] == 50
    assert result['new_level'] == 1
    assert result['xp_awarded'] == 50
    assert result['leveled_up'] is False


@pytest.mark.asyncio
async def test_level_up():
    """Test level up when XP threshold is crossed"""
    user_id = "test_user_2"

    # Award 95 XP (just below level 2)
    await award_xp(user_id, 95, "reminder", "Test 1")

    # Award 10 more XP (should trigger level up)
    result = await award_xp(user_id, 10, "reminder", "Test 2")

    assert result['new_total_xp'] == 105
    assert result['new_level'] == 2
    assert result['leveled_up'] is True
    assert result['old_level'] == 1


@pytest.mark.asyncio
async def test_tier_change():
    """Test tier change from Bronze to Silver"""
    user_id = "test_user_3"

    # Award enough XP to reach level 6 (Silver) - need 600 XP total
    result = await award_xp(user_id, 600, "reminder", "Big award")

    assert result['new_level'] == 6
    assert result['new_tier'] == 'silver'
    assert result['tier_changed'] is True
    assert result['old_tier'] == 'bronze'


@pytest.mark.asyncio
async def test_xp_history():
    """Test XP transaction history"""
    user_id = "test_user_4"

    await award_xp(user_id, 10, "reminder", "Test 1")
    await award_xp(user_id, 20, "meal", "Test 2")
    await award_xp(user_id, 15, "exercise", "Test 3")

    history = mock_store.get_xp_transactions(user_id, limit=10)

    assert len(history) == 3
    assert history[0]['amount'] == 15  # Most recent
    assert history[1]['amount'] == 20
    assert history[2]['amount'] == 10


# ============================================
# Streak System Tests
# ============================================

@pytest.mark.asyncio
async def test_streak_start():
    """Test starting a new streak"""
    user_id = "test_user_5"

    result = await update_streak(
        user_id=user_id,
        streak_type="medication",
        activity_date=date.today()
    )

    assert result['current_streak'] == 1
    assert result['best_streak'] == 1
    assert "started" in result['message'].lower()


@pytest.mark.asyncio
async def test_streak_continuation():
    """Test continuing a streak next day"""
    user_id = "test_user_6"
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Day 1
    await update_streak(user_id, "medication", activity_date=yesterday)

    # Day 2
    result = await update_streak(user_id, "medication", activity_date=today)

    assert result['current_streak'] == 2
    assert result['best_streak'] == 2
    assert "continues" in result['message'].lower()


@pytest.mark.asyncio
async def test_streak_same_day():
    """Test multiple activities on same day don't increment streak"""
    user_id = "test_user_7"
    today = date.today()

    # First activity
    result1 = await update_streak(user_id, "medication", activity_date=today)
    assert result1['current_streak'] == 1

    # Second activity same day
    result2 = await update_streak(user_id, "medication", activity_date=today)
    assert result2['current_streak'] == 1  # Should not increment


@pytest.mark.asyncio
async def test_streak_freeze_day():
    """Test streak protection with freeze day"""
    user_id = "test_user_8"
    today = date.today()
    two_days_ago = today - timedelta(days=2)

    # Day 1
    await update_streak(user_id, "medication", activity_date=two_days_ago)

    # Day 3 (2-day gap, should use freeze day)
    result = await update_streak(user_id, "medication", activity_date=today)

    assert result['current_streak'] == 2  # Streak continues
    assert result['streak_protected'] is True
    assert result['freeze_days_remaining'] == 1  # One freeze day used
    assert "protected" in result['message'].lower()


@pytest.mark.asyncio
async def test_streak_break():
    """Test streak breaking when gap is too large"""
    user_id = "test_user_9"
    today = date.today()
    week_ago = today - timedelta(days=7)

    # Day 1
    await update_streak(user_id, "medication", activity_date=week_ago)

    # Day 8 (7-day gap, should reset)
    result = await update_streak(user_id, "medication", activity_date=today)

    assert result['current_streak'] == 1  # Reset
    assert result['old_streak'] == 1
    assert "reset" in result['message'].lower()


@pytest.mark.asyncio
async def test_streak_milestone_bonus():
    """Test XP bonus at 7-day milestone"""
    user_id = "test_user_10"
    today = date.today()

    # Build up to 7-day streak
    for i in range(7):
        activity_date = today - timedelta(days=6 - i)
        result = await update_streak(user_id, "medication", activity_date=activity_date)

    assert result['current_streak'] == 7
    assert result['milestone_reached'] is True
    assert result['xp_bonus'] == 50
    assert "milestone" in result['message'].lower()


@pytest.mark.asyncio
async def test_best_streak_tracking():
    """Test that best streak is tracked correctly"""
    user_id = "test_user_11"
    today = date.today()

    # Build 5-day streak (days -4, -3, -2, -1, 0)
    for i in range(5):
        await update_streak(user_id, "medication", activity_date=today - timedelta(days=4 - i))

    # Break it by waiting more than 2 days (activity on day +4)
    await update_streak(user_id, "medication", activity_date=today + timedelta(days=4))

    # Build 3-day streak (days +4, +5, +6)
    for i in range(1, 3):
        await update_streak(user_id, "medication", activity_date=today + timedelta(days=4 + i))

    streaks = await get_user_streaks(user_id)
    med_streak = next(s for s in streaks if s['streak_type'] == 'medication')

    assert med_streak['current_streak'] == 3
    assert med_streak['best_streak'] == 5  # Should remember the 5-day streak


@pytest.mark.asyncio
async def test_multi_domain_streaks():
    """Test tracking streaks across multiple domains"""
    user_id = "test_user_12"
    today = date.today()

    # Different domains
    await update_streak(user_id, "medication", activity_date=today)
    await update_streak(user_id, "nutrition", activity_date=today)
    await update_streak(user_id, "exercise", activity_date=today)

    streaks = await get_user_streaks(user_id)

    assert len(streaks) == 3
    streak_types = {s['streak_type'] for s in streaks}
    assert streak_types == {'medication', 'nutrition', 'exercise'}


# ============================================
# Achievement System Tests
# ============================================

@pytest.mark.asyncio
async def test_first_steps_achievement():
    """Test unlocking First Steps achievement"""
    user_id = "test_user_13"

    # Award first XP (simulating first completion)
    await award_xp(user_id, 10, "reminder", "First completion")

    # Check achievements
    unlocked = await check_and_award_achievements(
        user_id,
        trigger_type="completion",
        context={'source_type': 'reminder'}
    )

    assert len(unlocked) >= 1
    achievement_keys = {ach['achievement_key'] for ach in unlocked}
    assert 'first_steps' in achievement_keys


@pytest.mark.asyncio
async def test_week_warrior_achievement():
    """Test unlocking Week Warrior achievement"""
    user_id = "test_user_14"
    today = date.today()

    # Build 7-day streak
    for i in range(7):
        await update_streak(user_id, "medication", activity_date=today - timedelta(days=6 - i))

    # Check achievements
    unlocked = await check_and_award_achievements(
        user_id,
        trigger_type="streak",
        context={'streak_type': 'medication', 'streak_count': 7}
    )

    achievement_keys = {ach['achievement_key'] for ach in unlocked}
    assert 'week_warrior' in achievement_keys


@pytest.mark.asyncio
async def test_level_milestone_achievement():
    """Test unlocking Bronze Tier achievement"""
    user_id = "test_user_15"

    # Award enough XP to reach level 5
    await award_xp(user_id, 400, "reminder", "Level up")

    # Check achievements
    unlocked = await check_and_award_achievements(
        user_id,
        trigger_type="level_up",
        context={'level': 5}
    )

    achievement_keys = {ach['achievement_key'] for ach in unlocked}
    assert 'bronze_tier' in achievement_keys


@pytest.mark.asyncio
async def test_achievement_progress_tracking():
    """Test tracking progress toward locked achievements"""
    user_id = "test_user_16"

    # Award some XP
    await award_xp(user_id, 100, "reminder", "Test")

    # Get achievements with progress
    achievements_data = await get_user_achievements(user_id, include_locked=True)

    assert 'locked' in achievements_data
    assert len(achievements_data['locked']) > 0

    # Find Week Warrior and check progress
    week_warrior = next(
        (ach for ach in achievements_data['locked'] if ach['achievement_key'] == 'week_warrior'),
        None
    )

    if week_warrior:
        assert 'progress' in week_warrior
        assert 'percentage' in week_warrior['progress']


@pytest.mark.asyncio
async def test_no_duplicate_achievements():
    """Test that achievements can't be unlocked twice"""
    user_id = "test_user_17"

    # Award first XP
    await award_xp(user_id, 10, "reminder", "First")

    # Check achievements (should unlock First Steps)
    unlocked1 = await check_and_award_achievements(
        user_id,
        trigger_type="completion",
        context={'source_type': 'reminder'}
    )

    # Award more XP
    await award_xp(user_id, 10, "reminder", "Second")

    # Check again (should NOT unlock First Steps again)
    unlocked2 = await check_and_award_achievements(
        user_id,
        trigger_type="completion",
        context={'source_type': 'reminder'}
    )

    first_steps_count = sum(
        1 for ach in (unlocked1 + unlocked2)
        if ach['achievement_key'] == 'first_steps'
    )

    assert first_steps_count == 1


# ============================================
# Integration Tests
# ============================================

@pytest.mark.asyncio
async def test_full_user_journey():
    """Test a complete user journey through gamification systems"""
    user_id = "test_user_18"
    today = date.today()

    # Day 1: Complete first reminder
    await award_xp(user_id, 10, "reminder", "First reminder")
    await update_streak(user_id, "medication", activity_date=today)
    unlocked = await check_and_award_achievements(user_id, "completion", {})

    # Should unlock First Steps
    assert any(ach['achievement_key'] == 'first_steps' for ach in unlocked)

    # Day 2-7: Build streak
    for i in range(1, 7):
        activity_date = today + timedelta(days=i)
        await award_xp(user_id, 10, "reminder", f"Day {i+1}")
        await update_streak(user_id, "medication", activity_date=activity_date)

    # Check for Week Warrior
    unlocked = await check_and_award_achievements(user_id, "streak", {'streak_count': 7})
    assert any(ach['achievement_key'] == 'week_warrior' for ach in unlocked)

    # Check final stats
    xp_data = await get_user_xp(user_id)
    assert xp_data['total_xp'] >= 70  # 7 days * 10 XP

    streaks = await get_user_streaks(user_id)
    med_streak = next(s for s in streaks if s['streak_type'] == 'medication')
    assert med_streak['current_streak'] == 7

    achievements_data = await get_user_achievements(user_id)
    assert achievements_data['total_unlocked'] >= 2  # First Steps + Week Warrior


@pytest.mark.asyncio
async def test_xp_and_achievement_bonus():
    """Test that achievement XP bonuses are included"""
    user_id = "test_user_19"

    # Award initial XP
    result1 = await award_xp(user_id, 10, "reminder", "First")
    initial_xp = result1['new_total_xp']

    # Check achievements (should unlock First Steps with 25 XP bonus)
    unlocked = await check_and_award_achievements(user_id, "completion", {})

    if unlocked:
        first_steps = next(ach for ach in unlocked if ach['achievement_key'] == 'first_steps')

        # Award the achievement XP
        result2 = await award_xp(
            user_id,
            first_steps['xp_reward'],
            "achievement",
            f"Achievement: {first_steps['name']}"
        )

        assert result2['new_total_xp'] == initial_xp + 25


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
