"""
Gamification Integration Hooks

This module provides integration functions to connect gamification systems
with existing health tracking features. Call these functions after health
actions (reminder completions, meal logging, etc.) to award XP, update
streaks, and check for achievement unlocks.

Usage:
    from src.gamification.integrations import handle_reminder_completion_gamification

    # After saving reminder completion
    await handle_reminder_completion_gamification(user_id, reminder_id, completed_at)
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Optional, TypedDict, Any

from src.gamification import (
    award_xp,
    update_streak,
    check_and_award_achievements,
)
from src.gamification.motivation_profiles import (
    get_or_detect_profile,
    get_motivational_message,
)

logger = logging.getLogger(__name__)


# TypedDict for gamification results
class GamificationResult(TypedDict):
    """Result of gamification processing"""
    xp_awarded: int
    level_up: bool
    new_level: int
    streak_updated: bool
    current_streak: int
    achievements_unlocked: List[Dict[str, Any]]
    message: str


async def handle_reminder_completion_gamification(
    user_id: str,
    reminder_id: str,
    completed_at: datetime,
    scheduled_time: str
) -> GamificationResult:
    """
    Handle gamification for reminder completion

    Args:
        user_id: Telegram user ID
        reminder_id: Reminder UUID
        completed_at: When reminder was completed
        scheduled_time: Scheduled time (HH:MM format)

    Returns:
        {
            'xp_awarded': int,
            'level_up': bool,
            'new_level': int,
            'streak_updated': bool,
            'current_streak': int,
            'achievements_unlocked': list,
            'message': str  # User-facing message
        }
    """
    logger.info(f"[GAMIFICATION] handle_reminder_completion_gamification called: user={user_id}, reminder={reminder_id}")

    try:
        result = {
            'xp_awarded': 0,
            'level_up': False,
            'new_level': 1,
            'streak_updated': False,
            'current_streak': 0,
            'achievements_unlocked': [],
            'message': ''
        }

        # Calculate XP bonuses
        base_xp = 10  # Base XP for reminder completion
        bonus_xp = 0

        # On-time bonus: +5 XP if completed within 30 minutes
        try:
            hour, minute = map(int, scheduled_time.split(":"))
            scheduled_minutes = hour * 60 + minute
            actual_minutes = completed_at.hour * 60 + completed_at.minute
            diff_minutes = abs(actual_minutes - scheduled_minutes)

            if diff_minutes <= 30:
                bonus_xp += 5
        except Exception as e:
            logger.warning(f"Could not calculate on-time bonus: {e}")

        total_xp = base_xp + bonus_xp

        # Award XP
        xp_result = await award_xp(
            user_id=user_id,
            amount=total_xp,
            source_type="reminder",
            source_id=reminder_id,
            reason="Completed medication reminder"
        )

        result['xp_awarded'] = xp_result['xp_awarded']
        result['level_up'] = xp_result['leveled_up']
        result['new_level'] = xp_result['new_level']

        # Update medication streak
        streak_result = await update_streak(
            user_id=user_id,
            streak_type="medication",
            source_id=reminder_id,
            activity_date=completed_at.date()
        )

        result['streak_updated'] = True
        result['current_streak'] = streak_result['current_streak']

        # Award streak bonus XP if milestone reached
        if streak_result.get('milestone_reached'):
            milestone_xp = streak_result.get('xp_bonus', 0)
            if milestone_xp > 0:
                await award_xp(
                    user_id=user_id,
                    amount=milestone_xp,
                    source_type="streak_milestone",
                    source_id=reminder_id,
                    reason=f"Streak milestone: {result['current_streak']} days"
                )
                result['xp_awarded'] += milestone_xp

        # Check for achievements
        achievements = await check_and_award_achievements(
            user_id=user_id,
            trigger_type="completion",
            context={
                'source_type': 'reminder',
                'reminder_id': reminder_id,
                'streak_count': result['current_streak']
            }
        )

        # Award achievement XP
        for achievement in achievements:
            ach_xp = achievement['xp_reward']
            await award_xp(
                user_id=user_id,
                amount=ach_xp,
                source_type="achievement",
                reason=f"Achievement: {achievement['name']}"
            )
            result['achievements_unlocked'].append(achievement)
            result['xp_awarded'] += ach_xp

        # Get user's motivation profile for personalized messaging
        profile = await get_or_detect_profile(user_id)

        # Build user-facing message with adaptive personalization
        message_parts = []

        # Personalized completion message based on motivation profile
        if result['level_up']:
            # Milestone context: leveled up
            motivational_msg = get_motivational_message(
                profile,
                context='milestone',
                xp_earned=total_xp
            )
            message_parts.append(motivational_msg)
        elif streak_result.get('milestone_reached'):
            # Milestone context: streak milestone
            motivational_msg = get_motivational_message(
                profile,
                context='milestone',
                streak_count=result['current_streak']
            )
            message_parts.append(motivational_msg)
        elif achievements:
            # Milestone context: achievement unlocked
            motivational_msg = get_motivational_message(
                profile,
                context='milestone',
                achievement_name=achievements[0]['name']
            )
            message_parts.append(motivational_msg)
        else:
            # Regular completion context
            motivational_msg = get_motivational_message(
                profile,
                context='completion',
                xp_earned=total_xp
            )
            message_parts.append(motivational_msg)

        # Add detailed stats below motivational message
        stats_parts = []

        # XP details
        if bonus_xp > 0:
            stats_parts.append(f"⭐ +{total_xp} XP (+{bonus_xp} on-time bonus)")
        else:
            stats_parts.append(f"⭐ +{total_xp} XP")

        # Level details
        if result['level_up']:
            tier_emoji = {
                'bronze': '🥉',
                'silver': '🥈',
                'gold': '🥇',
                'platinum': '💫'
            }
            tier = xp_result.get('new_tier', 'bronze')
            tier_symbol = tier_emoji.get(tier, '⭐')
            stats_parts.append(f"{tier_symbol} Level {result['new_level']} reached")

        # Streak details
        if result['current_streak'] > 0:
            if streak_result.get('milestone_reached'):
                stats_parts.append(
                    f"🔥 {result['current_streak']}-day streak "
                    f"(+{streak_result.get('xp_bonus', 0)} XP)"
                )
            else:
                stats_parts.append(f"🔥 {result['current_streak']}-day streak")

        # Achievement details
        for achievement in achievements:
            stats_parts.append(
                f"{achievement['icon']} {achievement['name']} "
                f"(+{achievement['xp_reward']} XP)"
            )

        # Combine: motivational message + stats
        if stats_parts:
            message_parts.append('\n' + '\n'.join(stats_parts))

        result['message'] = '\n'.join(message_parts)

        logger.info(
            f"Gamification processed for reminder completion: user={user_id}, "
            f"xp={result['xp_awarded']}, streak={result['current_streak']}, "
            f"achievements={len(achievements)}"
        )

        return result

    except Exception as e:
        logger.error(f"[GAMIFICATION] ERROR in reminder completion gamification: {type(e).__name__}: {e}", exc_info=True)
        # Return minimal result with user notification
        return {
            'xp_awarded': 0,
            'level_up': False,
            'new_level': 1,
            'streak_updated': False,
            'current_streak': 0,
            'achievements_unlocked': [],
            'message': '⚠️ Gamification temporarily unavailable. Your completion was recorded!'
        }


async def handle_food_entry_gamification(
    user_id: str,
    food_entry_id: str,
    logged_at: datetime,
    meal_type: str
) -> GamificationResult:
    """
    Handle gamification for food logging

    Args:
        user_id: Telegram user ID
        food_entry_id: Food entry UUID
        logged_at: When food was logged
        meal_type: breakfast, lunch, dinner, snack

    Returns:
        Gamification result dict
    """
    # DEBUG logging to expose silent failures (Issue #121)
    logger.info(f"[GAMIFICATION] handle_food_entry_gamification called: user={user_id}, meal={meal_type}")

    try:
        result = {
            'xp_awarded': 0,
            'level_up': False,
            'new_level': 1,
            'streak_updated': False,
            'current_streak': 0,
            'achievements_unlocked': [],
            'message': ''
        }

        # Award XP for food logging
        base_xp = 5
        logger.info(f"[GAMIFICATION] Awarding {base_xp} XP to user {user_id}")
        xp_result = await award_xp(
            user_id=user_id,
            amount=base_xp,
            source_type="nutrition",
            source_id=food_entry_id,
            reason=f"Logged {meal_type}"
        )
        logger.info(f"[GAMIFICATION] XP award successful: {xp_result}")

        result['xp_awarded'] = xp_result['xp_awarded']
        result['level_up'] = xp_result['leveled_up']
        result['new_level'] = xp_result['new_level']

        # Update nutrition streak
        logger.info(f"[GAMIFICATION] Updating nutrition streak for user {user_id}")
        streak_result = await update_streak(
            user_id=user_id,
            streak_type="nutrition",
            activity_date=logged_at.date()
        )
        logger.info(f"[GAMIFICATION] Streak update successful: current={streak_result['current_streak']}")

        result['streak_updated'] = True
        result['current_streak'] = streak_result['current_streak']

        # Award streak milestone XP
        if streak_result.get('milestone_reached'):
            milestone_xp = streak_result.get('xp_bonus', 0)
            if milestone_xp > 0:
                await award_xp(
                    user_id=user_id,
                    amount=milestone_xp,
                    source_type="streak_milestone",
                    reason=f"Nutrition streak: {result['current_streak']} days"
                )
                result['xp_awarded'] += milestone_xp

        # Check achievements
        logger.info(f"[GAMIFICATION] Checking achievements for user {user_id}")
        achievements = await check_and_award_achievements(
            user_id=user_id,
            trigger_type="completion",
            context={
                'source_type': 'nutrition',
                'meal_type': meal_type
            }
        )
        logger.info(f"[GAMIFICATION] Achievement check complete: {len(achievements)} unlocked")

        for achievement in achievements:
            ach_xp = achievement['xp_reward']
            await award_xp(
                user_id=user_id,
                amount=ach_xp,
                source_type="achievement",
                reason=f"Achievement: {achievement['name']}"
            )
            result['achievements_unlocked'].append(achievement)
            result['xp_awarded'] += ach_xp

        # Build message
        message_parts = [f"⭐ +{result['xp_awarded']} XP"]

        if result['level_up']:
            message_parts.append(f"🎉 Level {result['new_level']}!")

        if result['current_streak'] > 0:
            message_parts.append(f"🔥 {result['current_streak']}-day nutrition streak")

        result['message'] = '\n'.join(message_parts)

        logger.info(f"[GAMIFICATION] Food entry gamification complete: {result}")
        return result

    except Exception as e:
        # FIX for Issue #121: Expose failures to user instead of silent failure
        logger.error(f"[GAMIFICATION] ERROR in food entry gamification: {type(e).__name__}: {e}", exc_info=True)

        # Return result with user notification
        return {
            'xp_awarded': 0,
            'level_up': False,
            'new_level': 1,
            'streak_updated': False,
            'current_streak': 0,
            'achievements_unlocked': [],
            'message': '⚠️ Gamification temporarily unavailable. Your food was logged successfully!'
        }


async def handle_sleep_quiz_gamification(
    user_id: str,
    sleep_entry_id: str,
    logged_at: datetime
) -> GamificationResult:
    """
    Handle gamification for sleep quiz completion

    Args:
        user_id: Telegram user ID
        sleep_entry_id: Sleep entry UUID
        logged_at: When quiz was completed

    Returns:
        Gamification result dict
    """
    logger.info(f"[GAMIFICATION] handle_sleep_quiz_gamification called: user={user_id}")

    try:
        result = {
            'xp_awarded': 0,
            'level_up': False,
            'new_level': 1,
            'streak_updated': False,
            'current_streak': 0,
            'achievements_unlocked': [],
            'message': ''
        }

        # Award XP for sleep quiz (higher because it's more detailed)
        base_xp = 20
        xp_result = await award_xp(
            user_id=user_id,
            amount=base_xp,
            source_type="sleep",
            source_id=sleep_entry_id,
            reason="Completed sleep quiz"
        )

        result['xp_awarded'] = xp_result['xp_awarded']
        result['level_up'] = xp_result['leveled_up']
        result['new_level'] = xp_result['new_level']

        # Update sleep streak
        streak_result = await update_streak(
            user_id=user_id,
            streak_type="sleep",
            activity_date=logged_at.date()
        )

        result['streak_updated'] = True
        result['current_streak'] = streak_result['current_streak']

        # Award streak milestone XP
        if streak_result.get('milestone_reached'):
            milestone_xp = streak_result.get('xp_bonus', 0)
            if milestone_xp > 0:
                await award_xp(
                    user_id=user_id,
                    amount=milestone_xp,
                    source_type="streak_milestone",
                    reason=f"Sleep tracking streak: {result['current_streak']} days"
                )
                result['xp_awarded'] += milestone_xp

        # Check achievements
        achievements = await check_and_award_achievements(
            user_id=user_id,
            trigger_type="completion",
            context={'source_type': 'sleep'}
        )

        for achievement in achievements:
            ach_xp = achievement['xp_reward']
            await award_xp(
                user_id=user_id,
                amount=ach_xp,
                source_type="achievement",
                reason=f"Achievement: {achievement['name']}"
            )
            result['achievements_unlocked'].append(achievement)
            result['xp_awarded'] += ach_xp

        # Build message
        message_parts = [f"⭐ +{result['xp_awarded']} XP"]

        if result['level_up']:
            message_parts.append(f"🎉 Level {result['new_level']}!")

        if result['current_streak'] > 0:
            message_parts.append(f"🔥 {result['current_streak']}-day sleep tracking streak")

        result['message'] = '\n'.join(message_parts)

        return result

    except Exception as e:
        logger.error(f"[GAMIFICATION] ERROR in sleep quiz gamification: {type(e).__name__}: {e}", exc_info=True)
        return {
            'xp_awarded': 0,
            'level_up': False,
            'new_level': 1,
            'streak_updated': False,
            'current_streak': 0,
            'achievements_unlocked': [],
            'message': '⚠️ Gamification temporarily unavailable. Your sleep data was logged successfully!'
        }


async def handle_tracking_entry_gamification(
    user_id: str,
    tracking_entry_id: str,
    category_name: str,
    logged_at: datetime
) -> GamificationResult:
    """
    Handle gamification for custom tracking entries

    Args:
        user_id: Telegram user ID
        tracking_entry_id: Tracking entry UUID
        category_name: Name of tracking category
        logged_at: When entry was logged

    Returns:
        Gamification result dict
    """
    logger.info(f"[GAMIFICATION] handle_tracking_entry_gamification called: user={user_id}, category={category_name}")

    try:
        result = {
            'xp_awarded': 0,
            'level_up': False,
            'new_level': 1,
            'streak_updated': False,
            'current_streak': 0,
            'achievements_unlocked': [],
            'message': ''
        }

        # Award XP for tracking
        base_xp = 10
        xp_result = await award_xp(
            user_id=user_id,
            amount=base_xp,
            source_type="tracking",
            source_id=tracking_entry_id,
            reason=f"Logged {category_name}"
        )

        result['xp_awarded'] = xp_result['xp_awarded']
        result['level_up'] = xp_result['leveled_up']
        result['new_level'] = xp_result['new_level']

        # Determine streak type based on category name
        # Map common category names to streak types
        category_lower = category_name.lower()
        if 'exercise' in category_lower or 'workout' in category_lower or 'activity' in category_lower:
            streak_type = 'exercise'
        elif 'water' in category_lower or 'hydration' in category_lower:
            streak_type = 'hydration'
        elif 'meditation' in category_lower or 'mindfulness' in category_lower:
            streak_type = 'mindfulness'
        else:
            # Generic "overall" streak for other categories
            streak_type = 'overall'

        # Update streak
        streak_result = await update_streak(
            user_id=user_id,
            streak_type=streak_type,
            activity_date=logged_at.date()
        )

        result['streak_updated'] = True
        result['current_streak'] = streak_result['current_streak']

        # Award streak milestone XP
        if streak_result.get('milestone_reached'):
            milestone_xp = streak_result.get('xp_bonus', 0)
            if milestone_xp > 0:
                await award_xp(
                    user_id=user_id,
                    amount=milestone_xp,
                    source_type="streak_milestone",
                    reason=f"{category_name} streak: {result['current_streak']} days"
                )
                result['xp_awarded'] += milestone_xp

        # Check achievements
        achievements = await check_and_award_achievements(
            user_id=user_id,
            trigger_type="completion",
            context={
                'source_type': 'tracking',
                'category': category_name
            }
        )

        for achievement in achievements:
            ach_xp = achievement['xp_reward']
            await award_xp(
                user_id=user_id,
                amount=ach_xp,
                source_type="achievement",
                reason=f"Achievement: {achievement['name']}"
            )
            result['achievements_unlocked'].append(achievement)
            result['xp_awarded'] += ach_xp

        # Build message
        message_parts = [f"⭐ +{result['xp_awarded']} XP"]

        if result['level_up']:
            message_parts.append(f"🎉 Level {result['new_level']}!")

        if result['current_streak'] > 0:
            message_parts.append(f"🔥 {result['current_streak']}-day streak")

        result['message'] = '\n'.join(message_parts)

        return result

    except Exception as e:
        logger.error(f"[GAMIFICATION] ERROR in tracking entry gamification: {type(e).__name__}: {e}", exc_info=True)
        return {
            'xp_awarded': 0,
            'level_up': False,
            'new_level': 1,
            'streak_updated': False,
            'current_streak': 0,
            'achievements_unlocked': [],
            'message': '⚠️ Gamification temporarily unavailable. Your tracking entry was logged successfully!'
        }
