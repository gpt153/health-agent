"""
Tests for Phase 2: Visualization & Reports

Tests dashboard generation, weekly/monthly reports, and progress charts.
"""

import pytest
from datetime import date, datetime, timedelta
from src.gamification import mock_store
from src.gamification.dashboards import (
    get_daily_snapshot,
    get_weekly_overview,
    get_monthly_report,
    get_progress_chart,
)


@pytest.fixture
def clean_mock_store():
    """Clear mock store before each test"""
    mock_store._user_xp = {}
    mock_store._xp_transactions = {}
    mock_store._streaks = {}
    mock_store._user_achievements = {}
    yield
    mock_store._user_xp = {}
    mock_store._xp_transactions = {}
    mock_store._streaks = {}
    mock_store._user_achievements = {}


@pytest.mark.asyncio
async def test_daily_snapshot_no_activity(clean_mock_store):
    """Test daily snapshot with no activity"""
    user_id = "test_user_1"

    snapshot = await get_daily_snapshot(user_id)

    assert "📊 DAILY HEALTH SNAPSHOT" in snapshot
    assert "Today's XP: 0" in snapshot
    assert "No XP earned yet today" in snapshot


@pytest.mark.asyncio
async def test_daily_snapshot_with_activity(clean_mock_store):
    """Test daily snapshot with today's activity"""
    from src.gamification import award_xp, update_streak

    user_id = "test_user_2"
    today = date.today()

    # Award some XP today
    await award_xp(user_id, 10, "reminder", reason="Medication")
    await award_xp(user_id, 5, "nutrition", reason="Meal logged")
    await award_xp(user_id, 20, "sleep", reason="Sleep quiz")

    # Create a streak
    await update_streak(user_id, "medication", activity_date=today)

    snapshot = await get_daily_snapshot(user_id)

    assert "📊 DAILY HEALTH SNAPSHOT" in snapshot
    assert "Today's XP: 35" in snapshot  # 10 + 5 + 20
    assert "3 activities" in snapshot
    assert "Active Streaks:" in snapshot
    assert "medication" in snapshot.lower()


@pytest.mark.asyncio
async def test_weekly_overview_no_activity(clean_mock_store):
    """Test weekly overview with no activity"""
    user_id = "test_user_3"

    overview = await get_weekly_overview(user_id)

    assert "📅 WEEKLY HEALTH OVERVIEW" in overview
    assert "This Week's XP: 0" in overview
    assert "No activities yet this week" in overview


@pytest.mark.asyncio
async def test_weekly_overview_with_activity(clean_mock_store):
    """Test weekly overview with activity this week"""
    from src.gamification import award_xp

    user_id = "test_user_4"
    today = date.today()

    # Get week start (Monday)
    week_start = today - timedelta(days=today.weekday())

    # Award XP throughout the week
    for i in range(5):  # 5 days of activity
        activity_date = week_start + timedelta(days=i)

        # Create transactions backdated
        tx = {
            'user_id': user_id,
            'amount': 15,
            'source_type': 'reminder',
            'source_id': f'reminder_{i}',
            'reason': f'Day {i+1} medication',
            'awarded_at': datetime.combine(activity_date, datetime.min.time())
        }

        if user_id not in mock_store._xp_transactions:
            mock_store._xp_transactions[user_id] = []
        mock_store._xp_transactions[user_id].append(tx)

        # Update XP total
        user_xp = mock_store.get_user_xp_data(user_id)
        user_xp['total_xp'] += 15
        mock_store.update_user_xp(user_id, user_xp)

    overview = await get_weekly_overview(user_id)

    assert "📅 WEEKLY HEALTH OVERVIEW" in overview
    assert "This Week's XP: 75" in overview  # 15 * 5
    assert "5 activities" in overview


@pytest.mark.asyncio
async def test_weekly_overview_breakdown(clean_mock_store):
    """Test weekly overview shows activity breakdown"""
    from src.gamification import award_xp

    user_id = "test_user_5"
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    # Different activity types
    activities = [
        ("reminder", 10, "Medication"),
        ("reminder", 10, "Medication"),
        ("nutrition", 5, "Meal"),
        ("sleep", 20, "Sleep quiz"),
        ("tracking", 10, "Exercise"),
    ]

    for i, (source_type, amount, reason) in enumerate(activities):
        activity_date = week_start + timedelta(days=i)

        tx = {
            'user_id': user_id,
            'amount': amount,
            'source_type': source_type,
            'source_id': f'{source_type}_{i}',
            'reason': reason,
            'awarded_at': datetime.combine(activity_date, datetime.min.time())
        }

        if user_id not in mock_store._xp_transactions:
            mock_store._xp_transactions[user_id] = []
        mock_store._xp_transactions[user_id].append(tx)

        user_xp = mock_store.get_user_xp_data(user_id)
        user_xp['total_xp'] += amount
        mock_store.update_user_xp(user_id, user_xp)

    overview = await get_weekly_overview(user_id)

    assert "ACTIVITY BREAKDOWN" in overview
    assert "reminder" in overview.lower()
    assert "nutrition" in overview.lower()


@pytest.mark.asyncio
async def test_monthly_report_no_activity(clean_mock_store):
    """Test monthly report with no activity"""
    user_id = "test_user_6"

    report = await get_monthly_report(user_id)

    assert "📆 MONTHLY HEALTH REPORT" in report
    assert "This Month's XP: 0" in report
    assert "No activities logged this month" in report


@pytest.mark.asyncio
async def test_monthly_report_with_activity(clean_mock_store):
    """Test monthly report with activity"""
    from src.gamification import award_xp

    user_id = "test_user_7"
    today = date.today()
    month_start = date(today.year, today.month, 1)

    # Award XP on multiple days this month
    for day in [1, 3, 5, 7, 10, 15, 20]:
        activity_date = month_start.replace(day=day)

        tx = {
            'user_id': user_id,
            'amount': 25,
            'source_type': 'reminder',
            'source_id': f'reminder_{day}',
            'reason': f'Day {day} medication',
            'awarded_at': datetime.combine(activity_date, datetime.min.time())
        }

        if user_id not in mock_store._xp_transactions:
            mock_store._xp_transactions[user_id] = []
        mock_store._xp_transactions[user_id].append(tx)

        user_xp = mock_store.get_user_xp_data(user_id)
        user_xp['total_xp'] += 25
        mock_store.update_user_xp(user_id, user_xp)

    report = await get_monthly_report(user_id)

    assert "📆 MONTHLY HEALTH REPORT" in report
    assert "This Month's XP: 175" in report  # 25 * 7
    assert "7 activities" in report
    assert "Active Days: 7" in report


@pytest.mark.asyncio
async def test_monthly_report_insights(clean_mock_store):
    """Test monthly report provides insights"""
    from src.gamification import award_xp

    user_id = "test_user_8"
    today = date.today()
    month_start = date(today.year, today.month, 1)

    # High activity rate
    for day in range(1, 20):  # 19 days
        if day <= today.day:
            activity_date = month_start.replace(day=day)

            tx = {
                'user_id': user_id,
                'amount': 20,
                'source_type': 'reminder',
                'source_id': f'reminder_{day}',
                'reason': 'Daily medication',
                'awarded_at': datetime.combine(activity_date, datetime.min.time())
            }

            if user_id not in mock_store._xp_transactions:
                mock_store._xp_transactions[user_id] = []
            mock_store._xp_transactions[user_id].append(tx)

            user_xp = mock_store.get_user_xp_data(user_id)
            user_xp['total_xp'] += 20
            mock_store.update_user_xp(user_id, user_xp)

    report = await get_monthly_report(user_id)

    assert "💡 INSIGHTS" in report
    # High activity should trigger positive insight
    assert "Excellent" in report or "Great" in report or "Outstanding" in report


@pytest.mark.asyncio
async def test_progress_chart_no_data(clean_mock_store):
    """Test progress chart with no data"""
    user_id = "test_user_9"

    chart = await get_progress_chart(user_id, days=7)

    assert "📈 PROGRESS CHART" in chart
    assert "No XP data" in chart


@pytest.mark.asyncio
async def test_progress_chart_with_data(clean_mock_store):
    """Test progress chart generation"""
    from src.gamification import award_xp

    user_id = "test_user_10"
    today = date.today()

    # Create XP transactions over 7 days
    for i in range(7):
        activity_date = today - timedelta(days=6-i)
        amount = (i + 1) * 10  # Increasing XP each day

        tx = {
            'user_id': user_id,
            'amount': amount,
            'source_type': 'reminder',
            'source_id': f'reminder_{i}',
            'reason': f'Day {i} activity',
            'awarded_at': datetime.combine(activity_date, datetime.min.time())
        }

        if user_id not in mock_store._xp_transactions:
            mock_store._xp_transactions[user_id] = []
        mock_store._xp_transactions[user_id].append(tx)

        user_xp = mock_store.get_user_xp_data(user_id)
        user_xp['total_xp'] += amount
        mock_store.update_user_xp(user_id, user_xp)

    chart = await get_progress_chart(user_id, days=7)

    assert "📈 PROGRESS CHART" in chart
    assert "Last 7 Days" in chart
    assert "▓" in chart  # Progress bars present
    assert "Total XP: 280" in chart  # Sum of 10+20+30+40+50+60+70


@pytest.mark.asyncio
async def test_progress_chart_30_days(clean_mock_store):
    """Test 30-day progress chart"""
    from src.gamification import award_xp

    user_id = "test_user_11"
    today = date.today()

    # Create XP transactions over 30 days
    for i in range(30):
        activity_date = today - timedelta(days=29-i)

        tx = {
            'user_id': user_id,
            'amount': 15,
            'source_type': 'reminder',
            'source_id': f'reminder_{i}',
            'reason': 'Daily activity',
            'awarded_at': datetime.combine(activity_date, datetime.min.time())
        }

        if user_id not in mock_store._xp_transactions:
            mock_store._xp_transactions[user_id] = []
        mock_store._xp_transactions[user_id].append(tx)

        user_xp = mock_store.get_user_xp_data(user_id)
        user_xp['total_xp'] += 15
        mock_store.update_user_xp(user_id, user_xp)

    chart = await get_progress_chart(user_id, days=30)

    assert "📈 PROGRESS CHART" in chart
    assert "Last 30 Days" in chart
    assert "Total XP: 450" in chart  # 15 * 30


@pytest.mark.asyncio
async def test_daily_snapshot_with_achievements(clean_mock_store):
    """Test daily snapshot shows recent achievements"""
    from src.gamification import award_xp, check_and_award_achievements

    user_id = "test_user_12"

    # Award XP to trigger achievement check
    await award_xp(user_id, 100, "reminder", reason="First activity")

    # Trigger achievement check
    achievements = await check_and_award_achievements(
        user_id,
        trigger_type="completion",
        context={'source_type': 'reminder'}
    )

    snapshot = await get_daily_snapshot(user_id)

    assert "📊 DAILY HEALTH SNAPSHOT" in snapshot

    # If achievements were unlocked, they should appear
    if achievements:
        assert "Recent Achievements:" in snapshot


@pytest.mark.asyncio
async def test_weekly_overview_with_streaks(clean_mock_store):
    """Test weekly overview shows streak changes"""
    from src.gamification import update_streak

    user_id = "test_user_13"
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    # Build a 5-day streak this week
    for i in range(5):
        activity_date = week_start + timedelta(days=i)
        await update_streak(user_id, "medication", activity_date=activity_date)

    overview = await get_weekly_overview(user_id)

    assert "📅 WEEKLY HEALTH OVERVIEW" in overview
    assert "medication" in overview.lower()
    assert "5-day" in overview or "streak" in overview.lower()


@pytest.mark.asyncio
async def test_monthly_report_specific_month(clean_mock_store):
    """Test monthly report for specific month"""
    from src.gamification import award_xp

    user_id = "test_user_14"

    # Create data for a specific month (e.g., November 2024)
    target_month = date(2024, 11, 1)

    # Add transactions in November
    for day in [5, 10, 15, 20]:
        activity_date = target_month.replace(day=day)

        tx = {
            'user_id': user_id,
            'amount': 30,
            'source_type': 'reminder',
            'source_id': f'reminder_{day}',
            'reason': 'November activity',
            'awarded_at': datetime.combine(activity_date, datetime.min.time())
        }

        if user_id not in mock_store._xp_transactions:
            mock_store._xp_transactions[user_id] = []
        mock_store._xp_transactions[user_id].append(tx)

        user_xp = mock_store.get_user_xp_data(user_id)
        user_xp['total_xp'] += 30
        mock_store.update_user_xp(user_id, user_xp)

    # Request November report
    report = await get_monthly_report(user_id, month=target_month)

    assert "📆 MONTHLY HEALTH REPORT" in report
    assert "November" in report
    assert "This Month's XP: 120" in report  # 30 * 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
