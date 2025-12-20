"""Achievement checking and unlocking logic"""
import logging
from typing import List
from src.db.queries import (
    get_all_achievements,
    get_user_achievements,
    unlock_achievement,
    count_user_completions,
    count_early_completions,
    count_active_reminders,
    count_perfect_completion_days,
    check_recovery_pattern,
    count_stats_views,
    calculate_current_streak,
    calculate_best_streak,
    get_active_reminders,
)

logger = logging.getLogger(__name__)


async def check_and_unlock_achievements(
    user_id: str,
    reminder_id: str = None,
    event_type: str = "completion"
) -> List[dict]:
    """
    Check if user has unlocked any new achievements

    Args:
        user_id: User's Telegram ID
        reminder_id: Optional reminder ID for context
        event_type: 'completion', 'stats_view', 'reminder_created'

    Returns:
        List of newly unlocked achievement dicts
    """
    try:
        # Get all achievement definitions
        all_achievements = await get_all_achievements()

        # Get already unlocked achievements
        unlocked = await get_user_achievements(user_id)
        unlocked_ids = {a['achievement_id'] for a in unlocked}

        newly_unlocked = []

        for achievement in all_achievements:
            # Skip if already unlocked
            if achievement['id'] in unlocked_ids:
                continue

            # Check criteria
            meets_criteria = await check_achievement_criteria(
                user_id,
                achievement,
                reminder_id
            )

            if meets_criteria:
                # Unlock achievement
                success = await unlock_achievement(
                    user_id,
                    achievement['id'],
                    {"reminder_id": reminder_id, "event_type": event_type}
                )

                if success:
                    newly_unlocked.append(achievement)
                    logger.info(f"User {user_id} unlocked achievement: {achievement['id']}")

        return newly_unlocked

    except Exception as e:
        logger.error(f"Error checking achievements: {e}", exc_info=True)
        return []


async def check_achievement_criteria(
    user_id: str,
    achievement: dict,
    reminder_id: str = None
) -> bool:
    """
    Check if user meets achievement criteria

    Args:
        user_id: User's Telegram ID
        achievement: Achievement dict with criteria
        reminder_id: Optional reminder ID for streak checks

    Returns:
        True if user meets criteria, False otherwise
    """
    try:
        criteria = achievement['criteria']
        criteria_type = criteria.get("type")
        criteria_value = criteria.get("value")

        # Total completions
        if criteria_type == "total_completions":
            total = await count_user_completions(user_id)
            return total >= criteria_value

        # Streak achievement
        if criteria_type == "streak":
            if reminder_id:
                # Check specific reminder's streak
                current_streak, best_streak = await calculate_current_streak(user_id, reminder_id)
                return current_streak >= criteria_value or best_streak >= criteria_value
            else:
                # Check best streak across all reminders
                reminders = await get_active_reminders(user_id)
                for r in reminders:
                    current, best = await calculate_current_streak(user_id, r['id'])
                    if current >= criteria_value or best >= criteria_value:
                        return True
                return False

        # Perfect days (100% completion)
        if criteria_type == "perfect_days":
            perfect_days = await count_perfect_completion_days(user_id)
            return perfect_days >= criteria_value

        # Early completions
        if criteria_type == "early_completions":
            count = await count_early_completions(user_id)
            return count >= criteria_value

        # Active reminders
        if criteria_type == "active_reminders":
            count = await count_active_reminders(user_id, tracking_enabled=True)
            return count >= criteria_value

        # Recovery (comeback)
        if criteria_type == "recovery":
            threshold = criteria.get('threshold', 0.8)
            return await check_recovery_pattern(user_id, threshold)

        # Stats views
        if criteria_type == "stats_views":
            count = await count_stats_views(user_id)
            return count >= criteria_value

        return False

    except Exception as e:
        logger.error(f"Error checking criteria for {achievement['id']}: {e}")
        return False


def format_achievement_unlock(achievement: dict) -> str:
    """
    Format achievement unlock notification

    Args:
        achievement: Achievement dict

    Returns:
        Formatted Markdown string
    """
    tier_emoji = {
        "bronze": "🥉",
        "silver": "🥈",
        "gold": "🥇",
        "platinum": "💎"
    }

    return f"""
🎉 **ACHIEVEMENT UNLOCKED!** 🎉

{achievement['icon']} **{achievement['name']}** {tier_emoji.get(achievement['tier'], '')}

{achievement['description']}

Keep up the great work! 💪
"""


async def format_user_achievements_display(user_id: str) -> str:
    """
    Display all user achievements

    Args:
        user_id: User's Telegram ID

    Returns:
        Formatted Markdown string
    """
    unlocked = await get_user_achievements(user_id)
    all_achievements = await get_all_achievements()

    total_achievements = len(all_achievements)
    unlocked_count = len(unlocked)

    message = f"🏆 **Your Achievements** ({unlocked_count}/{total_achievements})\n\n"

    # Group by category
    by_category = {}
    for achievement_data in unlocked:
        category = achievement_data['category']
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(achievement_data)

    # Display by category
    category_names = {
        "consistency": "🔥 Consistency",
        "milestones": "🎯 Milestones",
        "recovery": "💪 Recovery",
        "exploration": "📊 Exploration"
    }

    for category, achievements in by_category.items():
        message += f"**{category_names.get(category, category.title())}** ({len(achievements)})\n"
        for achievement in achievements:
            tier_emoji = {
                "bronze": "🥉",
                "silver": "🥈",
                "gold": "🥇",
                "platinum": "💎"
            }.get(achievement['tier'], '')
            message += f"{achievement['icon']} {achievement['name']} {tier_emoji}\n"
        message += "\n"

    # Show locked achievements (teaser)
    locked_ids = {a['id'] for a in all_achievements} - {a['achievement_id'] for a in unlocked}
    if locked_ids:
        message += "🔒 **Locked** (Keep going!)\n"
        # Show one random locked achievement as teaser
        for achievement in all_achievements:
            if achievement['id'] in locked_ids:
                message += f"❓ {achievement['name']} - {achievement['description']}\n"
                break
        if len(locked_ids) > 1:
            message += f"\n...and {len(locked_ids) - 1} more to unlock!\n"

    return message
