"""
Pydantic AI Agent Tools for Gamification

Provides tools for the health agent to query and display gamification data
(XP, levels, streaks, achievements) in response to user questions.
"""

import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from src.gamification import get_user_xp
from src.gamification.streak_system import get_user_streaks, format_streak_display
from src.gamification.achievement_system import (
    get_user_achievements,
    get_achievement_recommendations,
    format_achievement_display
)
from src.gamification.xp_system import get_xp_history

logger = logging.getLogger(__name__)


# Response Models

class XPStatusResult(BaseModel):
    """Result of XP status query"""
    success: bool
    message: str
    user_id: str
    total_xp: int
    current_level: int
    xp_to_next_level: int
    level_tier: str


class StreakStatusResult(BaseModel):
    """Result of streak status query"""
    success: bool
    message: str
    user_id: str
    streaks: List[dict]
    highest_streak: int
    highest_streak_type: str


class AchievementStatusResult(BaseModel):
    """Result of achievement status query"""
    success: bool
    message: str
    user_id: str
    total_unlocked: int
    total_achievements: int
    total_xp_from_achievements: int
    recent_unlocks: List[dict]


class XPHistoryResult(BaseModel):
    """Result of XP history query"""
    success: bool
    message: str
    user_id: str
    recent_transactions: List[dict]
    total_transactions: int


# Tool Functions

async def get_xp_status_tool(ctx: RunContext) -> XPStatusResult:
    """
    Get user's current XP, level, and progression status

    Returns detailed information about the user's XP and level,
    including progress to next level and current tier.
    """
    try:
        user_id = ctx.deps.telegram_id

        # Get XP data
        xp_data = await get_user_xp(user_id)

        # Calculate progress bar
        xp_in_level = xp_data['xp_in_current_level']
        xp_needed = xp_data['xp_to_next_level']
        progress_percent = int((xp_in_level / (xp_in_level + xp_needed)) * 100)

        # Create progress bar
        filled = int(progress_percent / 5)  # 20 chars total
        bar = "▓" * filled + "░" * (20 - filled)

        # Tier emoji
        tier_emoji = {
            'bronze': '🥉',
            'silver': '🥈',
            'gold': '🥇',
            'platinum': '💫'
        }
        tier = xp_data['level_tier']
        tier_symbol = tier_emoji.get(tier, '⭐')

        message = f"""📊 **YOUR PROGRESS**

Level: **{xp_data['current_level']}** {tier_symbol} {tier.title()}
XP: **{xp_data['total_xp']}** ({xp_in_level}/{xp_in_level + xp_needed} to next level)

Progress: {bar} {progress_percent}%

Keep tracking your health activities to earn more XP and level up! 💪"""

        return XPStatusResult(
            success=True,
            message=message,
            user_id=user_id,
            total_xp=xp_data['total_xp'],
            current_level=xp_data['current_level'],
            xp_to_next_level=xp_needed,
            level_tier=tier
        )

    except Exception as e:
        logger.error(f"Error getting XP status: {e}", exc_info=True)
        return XPStatusResult(
            success=False,
            message="Sorry, I couldn't retrieve your XP status right now. Please try again later.",
            user_id=ctx.deps.telegram_id,
            total_xp=0,
            current_level=1,
            xp_to_next_level=100,
            level_tier="bronze"
        )


async def get_streak_status_tool(ctx: RunContext) -> StreakStatusResult:
    """
    Get user's current streaks across all health domains

    Returns all active streaks (medication, nutrition, exercise, sleep, etc.)
    with current streak counts and best streaks.
    """
    try:
        user_id = ctx.deps.telegram_id

        # Get all streaks
        streaks = await get_user_streaks(user_id)

        if not streaks:
            message = """🔥 **YOUR STREAKS**

You don't have any active streaks yet. Start tracking your health activities to build streaks!

Complete health activities on consecutive days to:
- Build your streak
- Earn XP bonuses at milestones (7, 14, 30, 100 days)
- Unlock achievements

💪 Start today!"""
            return StreakStatusResult(
                success=True,
                message=message,
                user_id=user_id,
                streaks=[],
                highest_streak=0,
                highest_streak_type=""
            )

        # Find highest streak
        highest = max(streaks, key=lambda x: x['current_streak'])

        # Format streaks for display
        streak_display = format_streak_display(streaks)

        message = f"""🔥 **YOUR STREAKS**

{streak_display}

🏆 Best: {highest['current_streak']}-day {highest['streak_type']} streak

Keep it up! Hit 7 days for a bonus! 💪"""

        return StreakStatusResult(
            success=True,
            message=message,
            user_id=user_id,
            streaks=[{
                'type': s['streak_type'],
                'current': s['current_streak'],
                'best': s['best_streak']
            } for s in streaks],
            highest_streak=highest['current_streak'],
            highest_streak_type=highest['streak_type']
        )

    except Exception as e:
        logger.error(f"Error getting streak status: {e}", exc_info=True)
        return StreakStatusResult(
            success=False,
            message="Sorry, I couldn't retrieve your streaks right now. Please try again later.",
            user_id=ctx.deps.telegram_id,
            streaks=[],
            highest_streak=0,
            highest_streak_type=""
        )


async def get_achievement_status_tool(ctx: RunContext) -> AchievementStatusResult:
    """
    Get user's unlocked achievements and progress toward locked ones

    Returns all unlocked achievements and shows progress toward achievements
    the user is close to unlocking.
    """
    try:
        user_id = ctx.deps.telegram_id

        # Get achievements with progress
        achievements_data = await get_user_achievements(user_id, include_locked=True)

        if achievements_data['total_unlocked'] == 0:
            message = """🏆 **YOUR ACHIEVEMENTS**

No achievements unlocked yet! Keep tracking your health to earn achievements.

**Available achievements:**
- 👣 First Steps: Complete your first activity
- 🔥 Week Warrior: Maintain a 7-day streak
- 🥉 Bronze Tier: Reach level 5
- And many more!

Start tracking to unlock achievements! 💪"""
            return AchievementStatusResult(
                success=True,
                message=message,
                user_id=user_id,
                total_unlocked=0,
                total_achievements=achievements_data['total_achievements'],
                total_xp_from_achievements=0,
                recent_unlocks=[]
            )

        # Format achievements
        achievement_display = format_achievement_display(achievements_data)

        # Get recommendations (close to completion)
        recommendations = await get_achievement_recommendations(user_id, limit=3)

        rec_text = ""
        if recommendations:
            rec_text = "\n\n📍 **CLOSE TO UNLOCKING:**\n"
            for rec in recommendations:
                prog = rec['progress']
                rec_text += f"{rec['icon']} {rec['name']}: {prog['description']} ({prog['percentage']}%)\n"

        message = f"""{achievement_display}{rec_text}"""

        # Get recent unlocks (up to 5)
        recent = achievements_data['unlocked'][:5]

        return AchievementStatusResult(
            success=True,
            message=message,
            user_id=user_id,
            total_unlocked=achievements_data['total_unlocked'],
            total_achievements=achievements_data['total_achievements'],
            total_xp_from_achievements=achievements_data['total_xp_from_achievements'],
            recent_unlocks=[{
                'name': ach['name'],
                'icon': ach['icon'],
                'xp_reward': ach['xp_reward']
            } for ach in recent]
        )

    except Exception as e:
        logger.error(f"Error getting achievement status: {e}", exc_info=True)
        return AchievementStatusResult(
            success=False,
            message="Sorry, I couldn't retrieve your achievements right now. Please try again later.",
            user_id=ctx.deps.telegram_id,
            total_unlocked=0,
            total_achievements=0,
            total_xp_from_achievements=0,
            recent_unlocks=[]
        )


async def get_xp_history_tool(ctx: RunContext, limit: int = 10) -> XPHistoryResult:
    """
    Get user's recent XP transaction history

    Shows recent XP awards from health activities, streaks, and achievements.

    Args:
        limit: Number of recent transactions to retrieve (default: 10)
    """
    try:
        user_id = ctx.deps.telegram_id

        # Get recent transactions
        from src.gamification import mock_store
        transactions = mock_store.get_xp_transactions(user_id, limit=limit)

        if not transactions:
            message = """📜 **XP HISTORY**

No XP transactions yet. Start tracking your health activities to earn XP!

**Ways to earn XP:**
- Complete medication reminders: 10 XP
- Log meals: 5 XP
- Complete sleep quiz: 20 XP
- Track exercise: 10-15 XP
- Streak milestones: 50-500 XP
- Unlock achievements: 25-500 XP"""

            return XPHistoryResult(
                success=True,
                message=message,
                user_id=user_id,
                recent_transactions=[],
                total_transactions=0
            )

        # Format transactions
        history_lines = ["📜 **RECENT XP HISTORY**\n"]

        for tx in transactions:
            # Format timestamp
            awarded_time = tx['awarded_at'].strftime("%b %d, %H:%M")

            # Format source
            source_emoji = {
                'reminder': '💊',
                'nutrition': '🍎',
                'sleep': '😴',
                'exercise': '🏃',
                'tracking': '📊',
                'streak_milestone': '🔥',
                'achievement': '🏆'
            }
            emoji = source_emoji.get(tx['source_type'], '⭐')

            history_lines.append(
                f"{emoji} +{tx['amount']} XP - {tx['reason']} ({awarded_time})"
            )

        message = "\n".join(history_lines)

        return XPHistoryResult(
            success=True,
            message=message,
            user_id=user_id,
            recent_transactions=[{
                'amount': tx['amount'],
                'source_type': tx['source_type'],
                'reason': tx['reason'],
                'awarded_at': tx['awarded_at'].isoformat()
            } for tx in transactions],
            total_transactions=len(transactions)
        )

    except Exception as e:
        logger.error(f"Error getting XP history: {e}", exc_info=True)
        return XPHistoryResult(
            success=False,
            message="Sorry, I couldn't retrieve your XP history right now. Please try again later.",
            user_id=ctx.deps.telegram_id,
            recent_transactions=[],
            total_transactions=0
        )


async def get_progress_summary_tool(ctx: RunContext) -> str:
    """
    Get a comprehensive progress summary (XP, streaks, achievements)

    Provides a complete overview of the user's gamification status
    in a single, formatted message.
    """
    try:
        user_id = ctx.deps.telegram_id

        # Get all data
        xp_data = await get_user_xp(user_id)
        streaks = await get_user_streaks(user_id)
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

        # Build summary
        summary_lines = [
            "📊 **YOUR HEALTH JOURNEY PROGRESS**\n",
            f"**Level {xp_data['current_level']}** {tier_symbol} {tier.title()}",
            f"XP: {xp_data['total_xp']} (+{xp_data['xp_to_next_level']} to next level)\n"
        ]

        # Streaks section
        if streaks:
            summary_lines.append("🔥 **ACTIVE STREAKS:**")
            for streak in streaks[:3]:  # Top 3 streaks
                summary_lines.append(
                    f"  {streak['current_streak']}-day {streak['streak_type']} streak"
                )
            if len(streaks) > 3:
                summary_lines.append(f"  ... and {len(streaks) - 3} more")
        else:
            summary_lines.append("🔥 No active streaks yet - start tracking!")

        summary_lines.append("")  # Blank line

        # Achievements section
        if achievements_data['total_unlocked'] > 0:
            summary_lines.append(
                f"🏆 **ACHIEVEMENTS:** {achievements_data['total_unlocked']}/{achievements_data['total_achievements']} unlocked"
            )
            summary_lines.append(
                f"  Total XP from achievements: {achievements_data['total_xp_from_achievements']}"
            )
        else:
            summary_lines.append("🏆 No achievements yet - keep tracking to unlock!")

        summary_lines.append("\n💪 Keep up the great work!")

        return "\n".join(summary_lines)

    except Exception as e:
        logger.error(f"Error getting progress summary: {e}", exc_info=True)
        return "Sorry, I couldn't retrieve your progress summary right now. Please try again later."
