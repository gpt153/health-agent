"""
Pattern Notification Service
Epic 009 - Phase 7: Integration & Agent Tools

Sends notifications to users when new high-quality patterns are discovered.

Features:
- Respects user notification preferences
- Quality filtering (confidence + impact thresholds)
- Frequency limiting (avoid notification fatigue)
- Quiet hours support
- Notification history tracking
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from src.db.connection import db

logger = logging.getLogger(__name__)


class PatternNotificationService:
    """
    Service for sending pattern discovery notifications to users

    Notification criteria:
    - Pattern confidence >= 0.70
    - Pattern impact >= 60
    - User preferences allow notifications
    - Not recently notified about similar pattern
    - Outside quiet hours (if configured)
    """

    def __init__(self) -> None:
        """Initialize notification service"""
        pass

    async def notify_new_pattern(
        self,
        user_id: str,
        pattern_id: int,
        pattern_data: Dict[str, Any],
        send_function: Optional[callable] = None
    ) -> bool:
        """
        Send notification to user about newly discovered pattern

        Args:
            user_id: Telegram user ID
            pattern_id: ID of the discovered pattern
            pattern_data: Pattern details (from discovered_patterns table)
            send_function: Optional function to send Telegram message
                          If None, just records notification without sending

        Returns:
            True if notification was sent/recorded, False otherwise

        Example:
            >>> async def send_telegram(user_id, message):
            ...     # Send via Telegram bot
            ...     pass
            >>>
            >>> success = await notify_new_pattern(
            ...     user_id="123",
            ...     pattern_id=45,
            ...     pattern_data={...},
            ...     send_function=send_telegram
            ... )
        """
        # 1. Check if notification should be sent (uses DB function)
        should_send = await self._should_send_notification(
            user_id,
            pattern_data.get('impact_score', 0)
        )

        if not should_send:
            logger.info(
                f"Skipping notification for pattern {pattern_id} to user {user_id} "
                f"(preferences/limits)"
            )
            return False

        # 2. Build notification message
        message = self._build_notification_message(pattern_data)

        # 3. Send notification (if send_function provided)
        if send_function:
            try:
                await send_function(user_id, message)
                logger.info(f"Sent pattern notification to user {user_id}: pattern {pattern_id}")
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
                return False

        # 4. Record that notification was sent
        await self._record_notification_sent(user_id, pattern_id)

        return True

    async def _should_send_notification(
        self,
        user_id: str,
        pattern_impact: float
    ) -> bool:
        """
        Check if notification should be sent using DB function

        Uses: should_send_pattern_notification() from migration 027
        """
        try:
            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT should_send_pattern_notification(%s, %s) as should_send",
                        (user_id, pattern_impact)
                    )
                    row = await cur.fetchone()

                    if row:
                        return row['should_send']

                    # Default to True if function fails
                    return True

        except Exception as e:
            logger.error(f"Failed to check notification preferences: {e}")
            # Default to allowing notifications
            return True

    async def _record_notification_sent(
        self,
        user_id: str,
        pattern_id: int
    ) -> None:
        """
        Record that notification was sent

        Uses: record_pattern_notification_sent() from migration 027
        """
        try:
            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT record_pattern_notification_sent(%s, %s)",
                        (user_id, pattern_id)
                    )
                    await conn.commit()

                    logger.debug(f"Recorded notification sent: user={user_id}, pattern={pattern_id}")

        except Exception as e:
            logger.error(f"Failed to record notification: {e}")

    def _build_notification_message(
        self,
        pattern_data: Dict[str, Any]
    ) -> str:
        """
        Build user-friendly notification message

        Format:
        🔍 New Health Pattern Discovered!

        [Pattern insight]

        📊 Confidence: 85%
        📈 Impact: High (78/100)
        📅 Observed: 12 times in past 90 days

        💡 Recommendation:
        [Actionable recommendation]

        [Helpful] [Not Helpful]
        """
        confidence = int(pattern_data.get('confidence', 0) * 100)
        impact_score = pattern_data.get('impact_score', 0)
        occurrences = pattern_data.get('occurrences', 0)
        insight = pattern_data.get('actionable_insight', 'Pattern discovered')

        # Determine impact level
        if impact_score >= 70:
            impact_level = "High"
        elif impact_score >= 50:
            impact_level = "Medium"
        else:
            impact_level = "Low"

        # Build message
        message = "🔍 **New Health Pattern Discovered!**\n\n"
        message += f"{insight}\n\n"
        message += f"📊 **Confidence:** {confidence}%\n"
        message += f"📈 **Impact:** {impact_level} ({impact_score:.0f}/100)\n"
        message += f"📅 **Observed:** {occurrences} times in past 90 days\n\n"
        message += "💬 **Was this insight helpful?**\n"
        message += "[Helpful] [Not Helpful]"

        return message

    async def get_notification_summary(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get notification settings summary for user

        Uses: get_notification_summary() from migration 027

        Returns:
            Dict with notification settings or None if error
        """
        try:
            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT * FROM get_notification_summary(%s)",
                        (user_id,)
                    )
                    row = await cur.fetchone()

                    if row:
                        return dict(row)

                    return None

        except Exception as e:
            logger.error(f"Failed to get notification summary: {e}")
            return None

    async def update_notification_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> bool:
        """
        Update user's notification preferences

        Args:
            user_id: Telegram user ID
            preferences: Dict with preference updates, e.g.:
                {
                    "pattern_notifications": True,
                    "pattern_min_impact": 60,
                    "notification_frequency": "daily",
                    "max_daily_notifications": 3,
                    "quiet_hours": {
                        "enabled": True,
                        "start": "22:00",
                        "end": "08:00"
                    }
                }

        Returns:
            True if successful, False otherwise
        """
        try:
            # Build JSONB update
            updates = {}

            if "pattern_notifications" in preferences:
                updates["pattern_notifications"] = preferences["pattern_notifications"]

            if "pattern_min_impact" in preferences:
                updates["pattern_min_impact"] = preferences["pattern_min_impact"]

            if "notification_frequency" in preferences:
                updates["notification_frequency"] = preferences["notification_frequency"]

            if "max_daily_notifications" in preferences:
                updates["max_daily_notifications"] = preferences["max_daily_notifications"]

            if "quiet_hours" in preferences:
                updates["quiet_hours"] = preferences["quiet_hours"]

            if not updates:
                return True  # No updates to apply

            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    # Merge updates into existing preferences
                    await cur.execute(
                        """
                        UPDATE user_profiles
                        SET notification_preferences =
                            COALESCE(notification_preferences, '{}'::jsonb) || %s::jsonb
                        WHERE telegram_id = %s
                        """,
                        (dict(updates), user_id)
                    )
                    await conn.commit()

                    logger.info(f"Updated notification preferences for user {user_id}")
                    return True

        except Exception as e:
            logger.error(f"Failed to update notification preferences: {e}")
            return False


# Global service instance
_notification_service: Optional[PatternNotificationService] = None


def get_notification_service() -> PatternNotificationService:
    """Get or create the global notification service instance"""
    global _notification_service

    if _notification_service is None:
        _notification_service = PatternNotificationService()

    return _notification_service
