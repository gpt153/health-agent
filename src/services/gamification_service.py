"""
GamificationService - Gamification Business Logic

Handles XP, streaks, achievements, and gamification integrations.
Extracts business logic from src/gamification/integrations.py.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, date

from src.gamification import (
    award_xp,
    update_streak,
    check_and_award_achievements,
    get_user_xp,
    get_user_streaks,
)
from src.gamification.motivation_profiles import (
    get_or_detect_profile,
    get_motivational_message,
)

logger = logging.getLogger(__name__)


class GamificationService:
    """
    Service for gamification features.

    Responsibilities:
    - XP calculation and awarding
    - Streak tracking and updates
    - Achievement checking and unlocking
    - Integration with health activities
    - Motivation profile-based messaging
    """

    def __init__(self, db_connection):
        """
        Initialize GamificationService.

        Args:
            db_connection: Database connection instance
        """
        self.db = db_connection
        logger.debug("GamificationService initialized")

    async def process_reminder_completion(
        self,
        user_id: str,
        reminder_id: str,
        completed_at: datetime,
        scheduled_time: str
    ) -> Dict[str, Any]:
        """
        Process gamification for reminder completion.

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

            # Calculate XP with on-time bonus
            base_xp, bonus_xp = self._calculate_reminder_xp(completed_at, scheduled_time)
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

            # Award streak milestone XP if reached
            if streak_result.get('milestone_reached'):
                milestone_xp = await self._award_streak_milestone_xp(
                    user_id, reminder_id, result['current_streak']
                )
                result['xp_awarded'] += milestone_xp

            # Check and award achievements
            achievements_xp = await self._process_achievements(
                user_id=user_id,
                trigger_type="completion",
                context={
                    'source_type': 'reminder',
                    'reminder_id': reminder_id,
                    'streak_count': result['current_streak']
                },
                result=result
            )
            result['xp_awarded'] += achievements_xp

            # Build personalized message
            result['message'] = await self._build_reminder_message(
                user_id=user_id,
                result=result,
                streak_result=streak_result,
                bonus_xp=bonus_xp,
                total_xp=total_xp,
                xp_result=xp_result
            )

            logger.info(
                f"Gamification processed for reminder completion: user={user_id}, "
                f"xp={result['xp_awarded']}, streak={result['current_streak']}, "
                f"achievements={len(result['achievements_unlocked'])}"
            )

            return result

        except Exception as e:
            logger.error(f"Error in reminder completion gamification: {e}", exc_info=True)
            return self._empty_result()

    async def process_food_entry(
        self,
        user_id: str,
        food_entry_id: str,
        logged_at: datetime,
        meal_type: str
    ) -> Dict[str, Any]:
        """
        Process gamification for food logging.

        Args:
            user_id: Telegram user ID
            food_entry_id: Food entry UUID
            logged_at: When food was logged
            meal_type: breakfast, lunch, dinner, snack

        Returns:
            Gamification result dict
        """
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
            xp_result = await award_xp(
                user_id=user_id,
                amount=base_xp,
                source_type="nutrition",
                source_id=food_entry_id,
                reason=f"Logged {meal_type}"
            )

            result['xp_awarded'] = xp_result['xp_awarded']
            result['level_up'] = xp_result['leveled_up']
            result['new_level'] = xp_result['new_level']

            # Update nutrition streak
            streak_result = await update_streak(
                user_id=user_id,
                streak_type="nutrition",
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
                        reason=f"Nutrition streak: {result['current_streak']} days"
                    )
                    result['xp_awarded'] += milestone_xp

            # Check achievements
            achievements_xp = await self._process_achievements(
                user_id=user_id,
                trigger_type="completion",
                context={
                    'source_type': 'nutrition',
                    'meal_type': meal_type
                },
                result=result
            )
            result['xp_awarded'] += achievements_xp

            # Build message
            result['message'] = self._build_food_message(result)

            logger.info(
                f"Gamification processed for food entry: user={user_id}, "
                f"xp={result['xp_awarded']}, streak={result['current_streak']}"
            )

            return result

        except Exception as e:
            logger.error(f"Error in food entry gamification: {e}", exc_info=True)
            return self._empty_result()

    async def process_sleep_quiz(
        self,
        user_id: str,
        sleep_entry_id: str,
        logged_at: datetime
    ) -> Dict[str, Any]:
        """
        Process gamification for sleep quiz completion.

        Args:
            user_id: Telegram user ID
            sleep_entry_id: Sleep entry UUID
            logged_at: When quiz was completed

        Returns:
            Gamification result dict
        """
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
            achievements_xp = await self._process_achievements(
                user_id=user_id,
                trigger_type="completion",
                context={'source_type': 'sleep'},
                result=result
            )
            result['xp_awarded'] += achievements_xp

            # Build message
            result['message'] = self._build_sleep_message(result)

            logger.info(
                f"Gamification processed for sleep quiz: user={user_id}, "
                f"xp={result['xp_awarded']}, streak={result['current_streak']}"
            )

            return result

        except Exception as e:
            logger.error(f"Error in sleep quiz gamification: {e}", exc_info=True)
            return self._empty_result()

    async def process_tracking_entry(
        self,
        user_id: str,
        tracking_entry_id: str,
        category_name: str,
        logged_at: datetime
    ) -> Dict[str, Any]:
        """
        Process gamification for custom tracking entries.

        Args:
            user_id: Telegram user ID
            tracking_entry_id: Tracking entry UUID
            category_name: Name of tracking category
            logged_at: When entry was logged

        Returns:
            Gamification result dict
        """
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
            streak_type = self._map_category_to_streak_type(category_name)

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
            achievements_xp = await self._process_achievements(
                user_id=user_id,
                trigger_type="completion",
                context={
                    'source_type': 'tracking',
                    'category': category_name
                },
                result=result
            )
            result['xp_awarded'] += achievements_xp

            # Build message
            result['message'] = self._build_tracking_message(result)

            logger.info(
                f"Gamification processed for tracking entry: user={user_id}, "
                f"category={category_name}, xp={result['xp_awarded']}"
            )

            return result

        except Exception as e:
            logger.error(f"Error in tracking entry gamification: {e}", exc_info=True)
            return self._empty_result()

    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive gamification stats for a user.

        Args:
            user_id: Telegram user ID

        Returns:
            {
                'xp': dict with current_xp, level, tier, progress
                'streaks': dict with all active streaks
                'achievements': list of all achievements
            }
        """
        try:
            # Get XP stats
            xp_data = await get_user_xp(user_id)

            # Get streaks
            streaks_data = await get_user_streaks(user_id)

            return {
                'xp': xp_data,
                'streaks': streaks_data,
                'success': True
            }

        except Exception as e:
            logger.error(f"Error getting user stats for {user_id}: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    # Private helper methods

    def _calculate_reminder_xp(self, completed_at: datetime, scheduled_time: str) -> tuple[int, int]:
        """Calculate base and bonus XP for reminder completion."""
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

        return base_xp, bonus_xp

    async def _award_streak_milestone_xp(
        self,
        user_id: str,
        source_id: str,
        streak_count: int
    ) -> int:
        """Award XP for reaching a streak milestone."""
        # Get milestone XP from streak result
        milestone_xp = 50  # Default milestone XP

        await award_xp(
            user_id=user_id,
            amount=milestone_xp,
            source_type="streak_milestone",
            source_id=source_id,
            reason=f"Streak milestone: {streak_count} days"
        )

        return milestone_xp

    async def _process_achievements(
        self,
        user_id: str,
        trigger_type: str,
        context: Dict,
        result: Dict
    ) -> int:
        """
        Check for achievements and award XP.
        Returns total achievement XP awarded.
        """
        achievements = await check_and_award_achievements(
            user_id=user_id,
            trigger_type=trigger_type,
            context=context
        )

        total_achievement_xp = 0
        for achievement in achievements:
            ach_xp = achievement['xp_reward']
            await award_xp(
                user_id=user_id,
                amount=ach_xp,
                source_type="achievement",
                reason=f"Achievement: {achievement['name']}"
            )
            result['achievements_unlocked'].append(achievement)
            total_achievement_xp += ach_xp

        return total_achievement_xp

    async def _build_reminder_message(
        self,
        user_id: str,
        result: Dict,
        streak_result: Dict,
        bonus_xp: int,
        total_xp: int,
        xp_result: Dict
    ) -> str:
        """Build personalized reminder completion message."""
        # Get user's motivation profile for personalized messaging
        profile = await get_or_detect_profile(user_id)

        message_parts = []

        # Personalized completion message based on motivation profile
        if result['level_up']:
            motivational_msg = get_motivational_message(
                profile,
                context='milestone',
                xp_earned=total_xp
            )
            message_parts.append(motivational_msg)
        elif streak_result.get('milestone_reached'):
            motivational_msg = get_motivational_message(
                profile,
                context='milestone',
                streak_count=result['current_streak']
            )
            message_parts.append(motivational_msg)
        elif result['achievements_unlocked']:
            motivational_msg = get_motivational_message(
                profile,
                context='milestone',
                achievement_name=result['achievements_unlocked'][0]['name']
            )
            message_parts.append(motivational_msg)
        else:
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
        for achievement in result['achievements_unlocked']:
            stats_parts.append(
                f"{achievement['icon']} {achievement['name']} "
                f"(+{achievement['xp_reward']} XP)"
            )

        # Combine: motivational message + stats
        if stats_parts:
            message_parts.append('\n' + '\n'.join(stats_parts))

        return '\n'.join(message_parts)

    def _build_food_message(self, result: Dict) -> str:
        """Build simple food entry gamification message."""
        message_parts = [f"⭐ +{result['xp_awarded']} XP"]

        if result['level_up']:
            message_parts.append(f"🎉 Level {result['new_level']}!")

        if result['current_streak'] > 0:
            message_parts.append(f"🔥 {result['current_streak']}-day nutrition streak")

        return '\n'.join(message_parts)

    def _build_sleep_message(self, result: Dict) -> str:
        """Build simple sleep quiz gamification message."""
        message_parts = [f"⭐ +{result['xp_awarded']} XP"]

        if result['level_up']:
            message_parts.append(f"🎉 Level {result['new_level']}!")

        if result['current_streak'] > 0:
            message_parts.append(f"🔥 {result['current_streak']}-day sleep tracking streak")

        return '\n'.join(message_parts)

    def _build_tracking_message(self, result: Dict) -> str:
        """Build simple tracking entry gamification message."""
        message_parts = [f"⭐ +{result['xp_awarded']} XP"]

        if result['level_up']:
            message_parts.append(f"🎉 Level {result['new_level']}!")

        if result['current_streak'] > 0:
            message_parts.append(f"🔥 {result['current_streak']}-day streak")

        return '\n'.join(message_parts)

    def _map_category_to_streak_type(self, category_name: str) -> str:
        """Map category name to streak type."""
        category_lower = category_name.lower()

        if 'exercise' in category_lower or 'workout' in category_lower or 'activity' in category_lower:
            return 'exercise'
        elif 'water' in category_lower or 'hydration' in category_lower:
            return 'hydration'
        elif 'meditation' in category_lower or 'mindfulness' in category_lower:
            return 'mindfulness'
        else:
            # Generic "overall" streak for other categories
            return 'overall'

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty gamification result for error cases."""
        return {
            'xp_awarded': 0,
            'level_up': False,
            'new_level': 1,
            'streak_updated': False,
            'current_streak': 0,
            'achievements_unlocked': [],
            'message': ''
        }
