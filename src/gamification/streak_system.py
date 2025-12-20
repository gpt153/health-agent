"""
Multi-Domain Streak Tracking System

Tracks streaks across different health domains:
- medication
- nutrition
- exercise
- sleep
- hydration
- mindfulness
- overall (any health activity)

Features:
- Streak protection (freeze days)
- Best streak tracking
- Vacation mode
- Weekend flex mode
"""

from typing import Dict, List, Optional
from datetime import date, datetime, timedelta
import logging

from src.gamification import mock_store

logger = logging.getLogger(__name__)


async def update_streak(
    user_id: str,
    streak_type: str,
    source_id: Optional[str] = None,
    activity_date: Optional[date] = None
) -> Dict[str, any]:
    """
    Update streak for a domain when activity occurs

    Logic:
    - If activity is today: increment streak (if not already counted today)
    - If activity was yesterday: continue streak
    - If >1 day gap: check freeze days, else reset
    - Update best_streak if current > best

    Args:
        user_id: User's Telegram ID
        streak_type: Type of streak (medication, nutrition, exercise, sleep, etc.)
        source_id: Optional specific reminder/category ID
        activity_date: Date of activity (defaults to today)

    Returns:
        {
            'current_streak': int,
            'best_streak': int,
            'streak_protected': bool,  # Used freeze day
            'milestone_reached': bool,  # Hit 7, 14, 30, etc.
            'xp_bonus': int,
            'message': str
        }
    """
    if activity_date is None:
        activity_date = date.today()

    # Get current streak data
    streak = mock_store.get_user_streak(user_id, streak_type, source_id)

    old_current = streak["current_streak"]
    old_best = streak["best_streak"]
    last_date = streak["last_activity_date"]

    streak_protected = False
    milestone_reached = False
    xp_bonus = 0
    message = ""

    # Convert last_date to date object if it's a datetime
    if last_date and isinstance(last_date, datetime):
        last_date = last_date.date()

    # If this is the first activity
    if last_date is None:
        streak["current_streak"] = 1
        streak["last_activity_date"] = activity_date
        message = "Streak started! Day 1 🎉"

    # If activity is on the same day
    elif last_date == activity_date:
        # Already counted for today, no change
        message = f"Streak continues! Day {streak['current_streak']} 🔥"

    # If activity is the next day (continuing streak)
    elif last_date == activity_date - timedelta(days=1):
        streak["current_streak"] += 1
        streak["last_activity_date"] = activity_date
        message = f"Streak continues! Day {streak['current_streak']} 🔥"

    # If there's a gap
    else:
        gap_days = (activity_date - last_date).days

        # Check if we can use freeze day
        if gap_days == 2 and streak["freeze_days_remaining"] > 0:
            # Use freeze day to protect streak
            streak["freeze_days_remaining"] -= 1
            streak["current_streak"] += 1  # Continue streak
            streak["last_activity_date"] = activity_date
            streak_protected = True
            message = f"Streak protected with freeze day! Day {streak['current_streak']} 🛡️"
            logger.info(f"User {user_id} used freeze day for {streak_type} streak")

        else:
            # Streak broken, reset
            old_streak = streak["current_streak"]
            streak["current_streak"] = 1
            streak["last_activity_date"] = activity_date
            message = f"Streak reset. Previous: {old_streak} days. Starting fresh! Day 1 💪"
            logger.info(
                f"User {user_id} streak broken for {streak_type}. "
                f"Was {old_streak}, gap was {gap_days} days"
            )

    # Update best streak
    if streak["current_streak"] > streak["best_streak"]:
        streak["best_streak"] = streak["current_streak"]

    # Check for milestones and award bonus XP
    current = streak["current_streak"]
    milestones = {7: 50, 14: 100, 30: 200, 100: 500}

    for milestone, bonus in milestones.items():
        if current == milestone:
            milestone_reached = True
            xp_bonus = bonus
            message += f"\n🏆 {milestone}-day milestone reached! +{bonus} XP"
            break

    # Save updated streak
    mock_store.update_user_streak(user_id, streak_type, streak, source_id)

    logger.info(
        f"Updated {streak_type} streak for user {user_id}: "
        f"{old_current} → {streak['current_streak']} days"
    )

    return {
        "current_streak": streak["current_streak"],
        "best_streak": streak["best_streak"],
        "old_streak": old_current,
        "streak_protected": streak_protected,
        "milestone_reached": milestone_reached,
        "xp_bonus": xp_bonus,
        "freeze_days_remaining": streak["freeze_days_remaining"],
        "message": message,
    }


async def get_user_streaks(user_id: str) -> List[Dict[str, any]]:
    """
    Get all active streaks for user

    Returns:
        List of streaks with current counts and metadata
    """
    streaks = mock_store.get_all_user_streaks(user_id)

    # Format for display
    formatted = []
    for streak in streaks:
        formatted.append({
            "streak_type": streak["streak_type"],
            "source_id": streak["source_id"],
            "current_streak": streak["current_streak"],
            "best_streak": streak["best_streak"],
            "last_activity_date": streak["last_activity_date"],
            "freeze_days_remaining": streak["freeze_days_remaining"],
        })

    # Sort by current streak (descending)
    formatted.sort(key=lambda x: x["current_streak"], reverse=True)

    return formatted


async def use_streak_freeze(
    user_id: str,
    streak_type: str,
    source_id: Optional[str] = None
) -> Dict[str, any]:
    """
    Manually use a freeze day to protect streak

    Returns:
        {
            'success': bool,
            'freeze_days_remaining': int,
            'message': str
        }
    """
    streak = mock_store.get_user_streak(user_id, streak_type, source_id)

    if streak["freeze_days_remaining"] <= 0:
        return {
            "success": False,
            "freeze_days_remaining": 0,
            "message": "No freeze days remaining",
        }

    streak["freeze_days_remaining"] -= 1
    mock_store.update_user_streak(user_id, streak_type, streak, source_id)

    return {
        "success": True,
        "freeze_days_remaining": streak["freeze_days_remaining"],
        "message": f"Freeze day used. {streak['freeze_days_remaining']} remaining",
    }


async def reset_monthly_freeze_days(user_id: str) -> None:
    """
    Reset freeze days for all streaks (called monthly)

    Each user gets 2 freeze days per month
    """
    streaks = mock_store.get_all_user_streaks(user_id)

    for streak in streaks:
        streak["freeze_days_remaining"] = 2
        mock_store.update_user_streak(
            user_id,
            streak["streak_type"],
            streak,
            streak["source_id"]
        )

    logger.info(f"Reset freeze days for user {user_id}")


def format_streak_display(streaks: List[Dict[str, any]]) -> str:
    """
    Format streaks for Telegram display

    Args:
        streaks: List of streak data from get_user_streaks()

    Returns:
        Formatted string for display
    """
    if not streaks:
        return "No active streaks yet. Start tracking to build your streaks! 💪"

    lines = ["🔥 YOUR STREAKS\n"]

    for streak in streaks:
        streak_type = streak["streak_type"].capitalize()
        current = streak["current_streak"]
        best = streak["best_streak"]
        freeze = streak["freeze_days_remaining"]

        # Emoji based on streak type
        emoji_map = {
            "medication": "💊",
            "nutrition": "🍎",
            "exercise": "🏃",
            "sleep": "😴",
            "hydration": "💧",
            "mindfulness": "🧘",
            "overall": "⭐",
        }
        emoji = emoji_map.get(streak["streak_type"], "🔥")

        line = f"{emoji} {streak_type}: {current} days"
        if best > current:
            line += f" (best: {best})"
        if freeze > 0:
            line += f" 🛡️×{freeze}"

        lines.append(line)

    return "\n".join(lines)
