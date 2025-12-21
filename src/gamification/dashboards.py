"""
Gamification Dashboards and Visualizations

Provides dashboard generation for daily, weekly, and monthly health progress
with XP, streaks, achievements, and trend analysis.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from src.gamification import get_user_xp
from src.gamification.streak_system import get_user_streaks, format_streak_display
from src.gamification.achievement_system import get_user_achievements, format_achievement_display
from src.gamification.xp_system import get_xp_history
from src.db import queries

logger = logging.getLogger(__name__)


async def get_daily_snapshot(user_id: str) -> str:
    """
    Generate daily health snapshot dashboard

    Shows today's progress: XP earned, streaks status, recent achievements,
    and quick stats.

    Args:
        user_id: Telegram user ID

    Returns:
        Formatted dashboard string for display
    """
    try:
        today = date.today()

        # Get user's XP and level
        xp_data = await get_user_xp(user_id)

        # Get today's XP transactions
        all_transactions = await queries.get_xp_transactions(user_id, limit=100)
        today_transactions = [
            tx for tx in all_transactions
            if tx['awarded_at'].date() == today
        ]
        today_xp = sum(tx['amount'] for tx in today_transactions)

        # Get streaks
        streaks = await get_user_streaks(user_id)

        # Get achievements
        achievements_data = await get_user_achievements(user_id)

        # Tier emoji
        tier_emoji = {
            'bronze': '🥉',
            'silver': '🥈',
            'gold': '🥇',
            'platinum': '💫'
        }
        tier = xp_data['level_tier']
        tier_symbol = tier_emoji.get(tier, '⭐')

        # Build dashboard
        lines = [
            f"📊 **DAILY HEALTH SNAPSHOT** - {today.strftime('%A, %B %d')}",
            "",
            f"**Level {xp_data['current_level']}** {tier_symbol} {tier.title()}",
            f"Total XP: {xp_data['total_xp']} (+{xp_data['xp_to_next_level']} to next level)",
            ""
        ]

        # Today's activity
        if today_xp > 0:
            activity_count = len(today_transactions)
            lines.append(f"🎯 **TODAY'S PROGRESS**")
            lines.append(f"⭐ Earned {today_xp} XP from {activity_count} activities")
        else:
            lines.append(f"🎯 **TODAY'S PROGRESS**")
            lines.append(f"No activities tracked yet today. Start tracking to earn XP!")

        lines.append("")

        # Active streaks
        if streaks:
            lines.append(f"🔥 **ACTIVE STREAKS**")
            # Show top 3 streaks
            sorted_streaks = sorted(streaks, key=lambda x: x['current_streak'], reverse=True)
            for streak in sorted_streaks[:3]:
                lines.append(f"  {streak['current_streak']}-day {streak['streak_type']}")
            if len(streaks) > 3:
                lines.append(f"  ... and {len(streaks) - 3} more")
        else:
            lines.append(f"🔥 **STREAKS**")
            lines.append(f"No active streaks - complete activities to start!")

        lines.append("")

        # Recent achievements (today)
        recent_achievements = [
            ach for ach in achievements_data['unlocked']
            if ach['unlocked_at'].date() == today
        ]

        if recent_achievements:
            lines.append(f"🏆 **TODAY'S ACHIEVEMENTS**")
            for ach in recent_achievements:
                lines.append(f"{ach['icon']} {ach['name']} (+{ach['xp_reward']} XP)")
        else:
            lines.append(f"🏆 **ACHIEVEMENTS**")
            lines.append(f"{achievements_data['total_unlocked']}/{achievements_data['total_achievements']} unlocked")

        lines.append("")
        lines.append("💪 Keep up the great work!")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error generating daily snapshot: {e}", exc_info=True)
        return "Sorry, I couldn't generate your daily snapshot. Please try again later."


async def get_weekly_overview(user_id: str) -> str:
    """
    Generate weekly health overview

    Shows this week's progress: XP earned, activities completed, streak changes,
    achievements unlocked, and trends.

    Args:
        user_id: Telegram user ID

    Returns:
        Formatted weekly overview string
    """
    try:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())  # Monday
        week_end = week_start + timedelta(days=6)  # Sunday

        # Get user's XP
        xp_data = await get_user_xp(user_id)

        # Get this week's transactions
        all_transactions = mock_store.get_xp_transactions(user_id, limit=500)
        week_transactions = [
            tx for tx in all_transactions
            if week_start <= tx['awarded_at'].date() <= week_end
        ]
        week_xp = sum(tx['amount'] for tx in week_transactions)

        # Count activities by type
        activity_counts = {}
        for tx in week_transactions:
            source = tx['source_type']
            activity_counts[source] = activity_counts.get(source, 0) + 1

        # Get streaks
        streaks = await get_user_streaks(user_id)

        # Get achievements unlocked this week
        achievements_data = await get_user_achievements(user_id)
        week_achievements = [
            ach for ach in achievements_data['unlocked']
            if week_start <= ach['unlocked_at'].date() <= week_end
        ]

        # Build overview
        tier_emoji = {
            'bronze': '🥉',
            'silver': '🥈',
            'gold': '🥇',
            'platinum': '💫'
        }
        tier = xp_data['level_tier']
        tier_symbol = tier_emoji.get(tier, '⭐')

        lines = [
            f"📅 **WEEKLY OVERVIEW** - Week of {week_start.strftime('%B %d')}",
            "",
            f"**Level {xp_data['current_level']}** {tier_symbol} {tier.title()}",
            f"Total XP: {xp_data['total_xp']}",
            ""
        ]

        # This week's XP
        if week_xp > 0:
            lines.append(f"⭐ **THIS WEEK**")
            lines.append(f"Earned {week_xp} XP from {len(week_transactions)} activities")

            # Show breakdown by activity type
            if activity_counts:
                lines.append("")
                lines.append("📊 **ACTIVITY BREAKDOWN:**")
                activity_emoji = {
                    'reminder': '💊',
                    'nutrition': '🍎',
                    'sleep': '😴',
                    'exercise': '🏃',
                    'tracking': '📊',
                    'streak_milestone': '🔥',
                    'achievement': '🏆'
                }
                for source, count in sorted(activity_counts.items(), key=lambda x: x[1], reverse=True):
                    emoji = activity_emoji.get(source, '⭐')
                    lines.append(f"  {emoji} {source.replace('_', ' ').title()}: {count}")
        else:
            lines.append(f"⭐ **THIS WEEK**")
            lines.append(f"No activities tracked yet this week")

        lines.append("")

        # Streaks status
        if streaks:
            lines.append(f"🔥 **CURRENT STREAKS**")
            sorted_streaks = sorted(streaks, key=lambda x: x['current_streak'], reverse=True)
            for streak in sorted_streaks[:5]:
                best_indicator = " (Best!)" if streak['current_streak'] == streak['best_streak'] else ""
                lines.append(f"  {streak['current_streak']}-day {streak['streak_type']}{best_indicator}")
        else:
            lines.append(f"🔥 **STREAKS**")
            lines.append(f"No active streaks this week")

        lines.append("")

        # Achievements this week
        if week_achievements:
            lines.append(f"🏆 **ACHIEVEMENTS UNLOCKED THIS WEEK**")
            for ach in week_achievements:
                lines.append(f"{ach['icon']} {ach['name']} (+{ach['xp_reward']} XP)")
        else:
            lines.append(f"🏆 **ACHIEVEMENTS**")
            lines.append(f"{achievements_data['total_unlocked']}/{achievements_data['total_achievements']} total unlocked")

        lines.append("")
        lines.append("💪 Great work this week! Keep it up!")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error generating weekly overview: {e}", exc_info=True)
        return "Sorry, I couldn't generate your weekly overview. Please try again later."


async def get_monthly_report(user_id: str, month: Optional[date] = None) -> str:
    """
    Generate comprehensive monthly report

    Shows month's progress: total XP, level progression, streaks, achievements,
    trends, and insights.

    Args:
        user_id: Telegram user ID
        month: Optional specific month (defaults to current month)

    Returns:
        Formatted monthly report string
    """
    try:
        if month is None:
            month = date.today()

        # Calculate month start and end
        month_start = month.replace(day=1)
        # Get last day of month
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1) - timedelta(days=1)

        # Get current XP
        xp_data = await get_user_xp(user_id)

        # Get month's transactions
        all_transactions = mock_store.get_xp_transactions(user_id, limit=1000)
        month_transactions = [
            tx for tx in all_transactions
            if month_start <= tx['awarded_at'].date() <= month_end
        ]
        month_xp = sum(tx['amount'] for tx in month_transactions)

        # Count activities by type and by day
        activity_counts = {}
        daily_xp = {}
        for tx in month_transactions:
            source = tx['source_type']
            activity_counts[source] = activity_counts.get(source, 0) + 1

            day = tx['awarded_at'].date()
            daily_xp[day] = daily_xp.get(day, 0) + tx['amount']

        # Calculate level progress this month
        # (This is an approximation - in real implementation, would track start-of-month level)
        total_days = (month_end - month_start).days + 1
        active_days = len(daily_xp)
        activity_rate = (active_days / total_days) * 100 if total_days > 0 else 0

        # Get streaks
        streaks = await get_user_streaks(user_id)

        # Get achievements unlocked this month
        achievements_data = await get_user_achievements(user_id)
        month_achievements = [
            ach for ach in achievements_data['unlocked']
            if month_start <= ach['unlocked_at'].date() <= month_end
        ]

        # Build report
        tier_emoji = {
            'bronze': '🥉',
            'silver': '🥈',
            'gold': '🥇',
            'platinum': '💫'
        }
        tier = xp_data['level_tier']
        tier_symbol = tier_emoji.get(tier, '⭐')

        lines = [
            f"📊 **MONTHLY HEALTH REPORT** - {month_start.strftime('%B %Y')}",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            f"🏆 **YOUR CURRENT STATUS**",
            f"Level: **{xp_data['current_level']}** {tier_symbol} {tier.title()}",
            f"Total XP: {xp_data['total_xp']}",
            ""
        ]

        # Month's progress
        lines.append(f"📈 **THIS MONTH'S PROGRESS**")
        lines.append(f"⭐ Earned {month_xp} XP")
        lines.append(f"📅 Active {active_days}/{total_days} days ({activity_rate:.0f}%)")
        lines.append(f"🎯 {len(month_transactions)} total activities")

        if active_days > 0:
            avg_xp_per_day = month_xp / active_days
            lines.append(f"📊 Average: {avg_xp_per_day:.1f} XP/active day")

        lines.append("")

        # Activity breakdown
        if activity_counts:
            lines.append(f"📊 **ACTIVITY BREAKDOWN**")
            activity_emoji = {
                'reminder': '💊',
                'nutrition': '🍎',
                'sleep': '😴',
                'exercise': '🏃',
                'tracking': '📊',
                'streak_milestone': '🔥',
                'achievement': '🏆'
            }
            for source, count in sorted(activity_counts.items(), key=lambda x: x[1], reverse=True):
                emoji = activity_emoji.get(source, '⭐')
                lines.append(f"{emoji} {source.replace('_', ' ').title()}: {count} times")

        lines.append("")

        # Streaks summary
        if streaks:
            lines.append(f"🔥 **STREAKS**")
            sorted_streaks = sorted(streaks, key=lambda x: x['best_streak'], reverse=True)
            for streak in sorted_streaks:
                current = streak['current_streak']
                best = streak['best_streak']
                if current > 0:
                    lines.append(f"  {streak['streak_type']}: {current}-day current, {best}-day best")
                else:
                    lines.append(f"  {streak['streak_type']}: {best}-day best (ended)")

        lines.append("")

        # Achievements
        if month_achievements:
            lines.append(f"🏆 **ACHIEVEMENTS UNLOCKED THIS MONTH**")
            for ach in month_achievements:
                lines.append(f"{ach['icon']} **{ach['name']}** (+{ach['xp_reward']} XP)")
                lines.append(f"   {ach['description']}")
        else:
            lines.append(f"🏆 **ACHIEVEMENTS**")
            lines.append(f"No new achievements this month")
            lines.append(f"Total: {achievements_data['total_unlocked']}/{achievements_data['total_achievements']} unlocked")

        lines.append("")

        # Insights
        lines.append(f"💡 **INSIGHTS**")

        if activity_rate >= 80:
            lines.append(f"✨ Outstanding consistency! Active {activity_rate:.0f}% of days")
        elif activity_rate >= 50:
            lines.append(f"👍 Good consistency! Active {activity_rate:.0f}% of days")
        else:
            lines.append(f"💪 Room for improvement - try to stay more consistent!")

        if month_xp > 500:
            lines.append(f"🌟 Excellent XP earning! You're crushing it!")
        elif month_xp > 200:
            lines.append(f"✅ Solid XP progress this month!")

        highest_streak = max(streaks, key=lambda x: x['current_streak']) if streaks else None
        if highest_streak and highest_streak['current_streak'] >= 14:
            lines.append(f"🔥 Amazing {highest_streak['current_streak']}-day {highest_streak['streak_type']} streak!")

        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("")
        lines.append(f"Keep up the fantastic work! 💪")
        lines.append(f"Looking forward to an even better {(month_start + timedelta(days=32)).strftime('%B')}!")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error generating monthly report: {e}", exc_info=True)
        return "Sorry, I couldn't generate your monthly report. Please try again later."


async def get_progress_chart(user_id: str, days: int = 30) -> str:
    """
    Generate text-based progress chart showing XP earned over time

    Args:
        user_id: Telegram user ID
        days: Number of days to chart (default: 30)

    Returns:
        Text-based chart string
    """
    try:
        # Get transactions for the period
        all_transactions = mock_store.get_xp_transactions(user_id, limit=1000)

        today = date.today()
        start_date = today - timedelta(days=days - 1)

        # Aggregate XP by day
        daily_xp = {}
        for tx in all_transactions:
            tx_date = tx['awarded_at'].date()
            if start_date <= tx_date <= today:
                daily_xp[tx_date] = daily_xp.get(tx_date, 0) + tx['amount']

        if not daily_xp:
            return "No activity data for the specified period."

        # Find max XP for scaling
        max_xp = max(daily_xp.values())
        if max_xp == 0:
            return "No XP earned in the specified period."

        # Build chart
        lines = [
            f"📈 **XP PROGRESS - Last {days} Days**",
            ""
        ]

        # Group by week for readability if days > 14
        if days > 14:
            # Weekly view
            weeks = {}
            for day, xp in daily_xp.items():
                week_start = day - timedelta(days=day.weekday())
                week_key = week_start.strftime("%b %d")
                weeks[week_key] = weeks.get(week_key, 0) + xp

            max_week_xp = max(weeks.values()) if weeks else 1

            for week, xp in sorted(weeks.items()):
                bar_length = int((xp / max_week_xp) * 20)
                bar = "▓" * bar_length + "░" * (20 - bar_length)
                lines.append(f"{week}: {bar} {xp} XP")
        else:
            # Daily view
            for i in range(days):
                day = start_date + timedelta(days=i)
                xp = daily_xp.get(day, 0)
                bar_length = int((xp / max_xp) * 20) if max_xp > 0 else 0
                bar = "▓" * bar_length + "░" * (20 - bar_length)
                day_label = day.strftime("%m/%d")
                lines.append(f"{day_label}: {bar} {xp} XP")

        lines.append("")
        total_xp = sum(daily_xp.values())
        avg_xp = total_xp / days
        lines.append(f"Total: {total_xp} XP | Avg: {avg_xp:.1f} XP/day")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error generating progress chart: {e}", exc_info=True)
        return "Sorry, I couldn't generate your progress chart. Please try again later."
