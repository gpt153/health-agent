"""Gamification database queries"""
import json
import logging
from typing import Optional
from datetime import datetime, timedelta
from src.db.connection import db

logger = logging.getLogger(__name__)


# ==========================================
# XP System Functions
# ==========================================

async def get_user_xp_data(user_id: str) -> dict:
    """
    Get user XP data (creates if doesn't exist)

    Returns:
        {
            'user_id': str,
            'total_xp': int,
            'current_level': int,
            'xp_to_next_level': int,
            'level_tier': str,
            'created_at': datetime,
            'updated_at': datetime
        }
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT user_id, total_xp, current_level, xp_to_next_level, level_tier, created_at, updated_at
                FROM user_xp
                WHERE user_id = %s
                """,
                (user_id,)
            )
            row = await cur.fetchone()

            if not row:
                # Create new user XP record with defaults
                await cur.execute(
                    """
                    INSERT INTO user_xp (user_id, total_xp, current_level, xp_to_next_level, level_tier)
                    VALUES (%s, 0, 1, 100, 'bronze')
                    RETURNING user_id, total_xp, current_level, xp_to_next_level, level_tier, created_at, updated_at
                    """,
                    (user_id,)
                )
                row = await cur.fetchone()
                await conn.commit()
                logger.info(f"Created new XP record for user {user_id}")

            return dict(row) if row else None


async def update_user_xp(user_id: str, xp_data: dict) -> None:
    """
    Update user XP data

    Args:
        user_id: User's Telegram ID
        xp_data: Dict with total_xp, current_level, xp_to_next_level, level_tier
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE user_xp
                SET total_xp = %s,
                    current_level = %s,
                    xp_to_next_level = %s,
                    level_tier = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                """,
                (
                    xp_data['total_xp'],
                    xp_data['current_level'],
                    xp_data['xp_to_next_level'],
                    xp_data['level_tier'],
                    user_id
                )
            )
            await conn.commit()


async def add_xp_transaction(
    user_id: str,
    amount: int,
    source_type: str,
    source_id: Optional[str],
    reason: str
) -> str:
    """
    Add XP transaction

    Args:
        user_id: User's Telegram ID
        amount: XP amount
        source_type: 'reminder', 'meal', 'exercise', 'sleep', 'tracking', 'achievement', 'streak_milestone'
        source_id: Optional UUID of source activity
        reason: Human-readable description

    Returns:
        Transaction ID (UUID string)
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO xp_transactions (user_id, amount, source_type, source_id, reason)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (user_id, amount, source_type, source_id, reason)
            )
            result = await cur.fetchone()
            await conn.commit()
            return str(result['id']) if result else None


async def get_xp_transactions(user_id: str, limit: int = 50) -> list[dict]:
    """
    Get recent XP transactions for user

    Args:
        user_id: User's Telegram ID
        limit: Maximum number of transactions to return

    Returns:
        List of transactions ordered by awarded_at DESC
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, amount, source_type, source_id, reason, awarded_at
                FROM xp_transactions
                WHERE user_id = %s
                ORDER BY awarded_at DESC
                LIMIT %s
                """,
                (user_id, limit)
            )
            rows = await cur.fetchall()
            return [dict(row) for row in rows]


async def get_user_xp_level(user_id: str) -> dict:
    """
    Wrapper for API compatibility - returns XP data in expected format

    Converts get_user_xp_data() output to match API endpoint expectations.

    Returns:
        {
            'xp': int,               # total_xp
            'level': int,            # current_level
            'tier': str,             # level_tier
            'xp_to_next_level': int  # xp_to_next_level
        }
    """
    xp_data = await get_user_xp_data(user_id)
    return {
        'xp': xp_data['total_xp'],
        'level': xp_data['current_level'],
        'tier': xp_data['level_tier'],
        'xp_to_next_level': xp_data['xp_to_next_level']
    }


# ==========================================
# Streak System Functions
# ==========================================

async def get_user_streak(user_id: str, streak_type: str, source_id: Optional[str] = None) -> dict:
    """
    Get specific streak for user (creates if doesn't exist)

    Args:
        user_id: User's Telegram ID
        streak_type: 'medication', 'nutrition', 'exercise', 'sleep', 'hydration', 'mindfulness', 'overall'
        source_id: Optional specific reminder/category ID

    Returns:
        Streak data dict
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, streak_type, source_id, current_streak, best_streak,
                       last_activity_date, freeze_days_remaining, created_at, updated_at
                FROM user_streaks
                WHERE user_id = %s AND streak_type = %s AND (source_id = %s OR (source_id IS NULL AND %s IS NULL))
                """,
                (user_id, streak_type, source_id, source_id)
            )
            row = await cur.fetchone()

            if not row:
                # Create new streak record
                await cur.execute(
                    """
                    INSERT INTO user_streaks (user_id, streak_type, source_id, current_streak, best_streak, freeze_days_remaining)
                    VALUES (%s, %s, %s, 0, 0, 2)
                    RETURNING id, user_id, streak_type, source_id, current_streak, best_streak,
                              last_activity_date, freeze_days_remaining, created_at, updated_at
                    """,
                    (user_id, streak_type, source_id)
                )
                row = await cur.fetchone()
                await conn.commit()
                logger.info(f"Created new streak for user {user_id}: {streak_type}")

            return dict(row) if row else None


async def update_user_streak(user_id: str, streak_type: str, streak_data: dict, source_id: Optional[str] = None) -> None:
    """
    Update streak data

    Args:
        user_id: User's Telegram ID
        streak_type: Streak type
        streak_data: Dict with current_streak, best_streak, last_activity_date, freeze_days_remaining
        source_id: Optional source ID
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE user_streaks
                SET current_streak = %s,
                    best_streak = %s,
                    last_activity_date = %s,
                    freeze_days_remaining = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s AND streak_type = %s AND (source_id = %s OR (source_id IS NULL AND %s IS NULL))
                """,
                (
                    streak_data['current_streak'],
                    streak_data['best_streak'],
                    streak_data['last_activity_date'],
                    streak_data['freeze_days_remaining'],
                    user_id,
                    streak_type,
                    source_id,
                    source_id
                )
            )
            await conn.commit()


async def get_all_user_streaks(user_id: str) -> list[dict]:
    """
    Get all streaks for user

    Args:
        user_id: User's Telegram ID

    Returns:
        List of all user streaks
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, streak_type, source_id, current_streak, best_streak,
                       last_activity_date, freeze_days_remaining, created_at, updated_at
                FROM user_streaks
                WHERE user_id = %s
                ORDER BY current_streak DESC
                """,
                (user_id,)
            )
            rows = await cur.fetchall()
            return [dict(row) for row in rows]


async def get_user_streaks(user_id: str) -> list[dict]:
    """
    Wrapper for API compatibility - alias to get_all_user_streaks

    Returns all streaks for the user.
    """
    return await get_all_user_streaks(user_id)


# ==========================================
# Achievement System Functions
# ==========================================

async def get_all_achievements() -> list[dict]:
    """
    Get all achievement definitions

    Returns:
        List of all achievements
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, achievement_key, name, description, icon, category, criteria, xp_reward, tier, sort_order
                FROM achievements
                ORDER BY sort_order, name
                """
            )
            rows = await cur.fetchall()
            return [dict(row) for row in rows]


async def get_achievement_by_key(key: str) -> Optional[dict]:
    """
    Get achievement by key

    Args:
        key: Achievement key (e.g., 'week_warrior')

    Returns:
        Achievement dict or None
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, achievement_key, name, description, icon, category, criteria, xp_reward, tier, sort_order
                FROM achievements
                WHERE achievement_key = %s
                """,
                (key,)
            )
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_user_achievement_unlocks(user_id: str) -> list[dict]:
    """
    Get user's unlocked achievements

    Args:
        user_id: User's Telegram ID

    Returns:
        List of unlocked achievements with progress
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, achievement_id, unlocked_at, progress
                FROM user_achievements
                WHERE user_id = %s
                ORDER BY unlocked_at DESC
                """,
                (user_id,)
            )
            rows = await cur.fetchall()
            return [dict(row) for row in rows]


async def add_user_achievement(user_id: str, achievement_id: str, progress: Optional[dict] = None) -> bool:
    """
    Add achievement unlock for user

    Args:
        user_id: User's Telegram ID
        achievement_id: Achievement UUID
        progress: Optional progress data

    Returns:
        True if newly unlocked, False if already unlocked
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Try to insert, ignore if already exists
            await cur.execute(
                """
                INSERT INTO user_achievements (user_id, achievement_id, progress)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, achievement_id) DO NOTHING
                RETURNING id
                """,
                (user_id, achievement_id, json.dumps(progress) if progress else None)
            )
            result = await cur.fetchone()
            await conn.commit()

            if result:
                logger.info(f"User {user_id} unlocked achievement {achievement_id}")
                return True
            return False


async def has_user_unlocked_achievement(user_id: str, achievement_id: str) -> bool:
    """
    Check if user has unlocked achievement

    Args:
        user_id: User's Telegram ID
        achievement_id: Achievement UUID

    Returns:
        True if unlocked, False otherwise
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT COUNT(*)
                FROM user_achievements
                WHERE user_id = %s AND achievement_id = %s
                """,
                (user_id, achievement_id)
            )
            result = await cur.fetchone()
            return result['count'] > 0 if result else False


async def get_user_achievements(user_id: str) -> list[dict]:
    """Alias for get_user_achievement_unlocks"""
    return await get_user_achievement_unlocks(user_id)


async def unlock_user_achievement(user_id: str, achievement_id: str) -> bool:
    """Alias for add_user_achievement"""
    return await add_user_achievement(user_id, achievement_id)


async def unlock_achievement(
    user_id: str,
    achievement_id: str,
    metadata: dict = None
) -> bool:
    """
    Unlock an achievement for a user

    Returns True if unlocked (new), False if already unlocked
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Try to insert
            await cur.execute(
                """
                INSERT INTO user_achievements (user_id, achievement_id, metadata)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, achievement_id) DO NOTHING
                RETURNING id
                """,
                (user_id, achievement_id, json.dumps(metadata) if metadata else None)
            )

            result = await cur.fetchone()
            await conn.commit()

            return result is not None  # True if inserted, False if already existed


# ==========================================
# Achievement Helper Functions
# ==========================================

async def count_user_completions(user_id: str) -> int:
    """Count total completions across all reminders"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT COUNT(*)
                FROM reminder_completions
                WHERE user_id = %s
                """,
                (user_id,)
            )

            return (await cur.fetchone())[0]


async def count_early_completions(user_id: str) -> int:
    """Count completions that were early (before scheduled time)"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT COUNT(*)
                FROM reminder_completions
                WHERE user_id = %s
                AND completed_at < scheduled_time
                """,
                (user_id,)
            )

            return (await cur.fetchone())[0]


async def count_active_reminders(user_id: str, tracking_enabled: bool = None) -> int:
    """Count active reminders for user"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            if tracking_enabled is not None:
                await cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM reminders
                    WHERE user_id = %s
                    AND active = true
                    AND enable_completion_tracking = %s
                    """,
                    (user_id, tracking_enabled)
                )
            else:
                await cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM reminders
                    WHERE user_id = %s
                    AND active = true
                    """,
                    (user_id,)
                )

            return (await cur.fetchone())[0]


async def count_perfect_completion_days(user_id: str) -> int:
    """
    Count consecutive days with 100% completion rate

    A perfect day = all scheduled reminders were completed
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # This is a simplified version
            # Full implementation would check daily completion rates
            await cur.execute(
                """
                WITH daily_stats AS (
                    SELECT
                        DATE(scheduled_time) as day,
                        COUNT(*) as scheduled,
                        COUNT(completed_at) as completed
                    FROM reminder_completions
                    WHERE user_id = %s
                    GROUP BY DATE(scheduled_time)
                )
                SELECT COUNT(*)
                FROM daily_stats
                WHERE completed = scheduled
                """,
                (user_id,)
            )

            return (await cur.fetchone())[0]


async def check_recovery_pattern(user_id: str, threshold: float) -> bool:
    """
    Check if user recovered from low completion rate

    Returns True if user had a week <60% then recovered to >threshold
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Get recent weekly completion rates
            await cur.execute(
                """
                WITH weekly_rates AS (
                    SELECT
                        DATE_TRUNC('week', scheduled_time) as week,
                        COUNT(CASE WHEN completed_at IS NOT NULL THEN 1 END)::float /
                        COUNT(*)::float as rate
                    FROM reminder_completions
                    WHERE user_id = %s
                    AND scheduled_time > NOW() - INTERVAL '60 days'
                    GROUP BY DATE_TRUNC('week', scheduled_time)
                    ORDER BY week DESC
                    LIMIT 4
                )
                SELECT rate FROM weekly_rates
                """,
                (user_id,)
            )

            rates = [row[0] for row in await cur.fetchall()]

            if len(rates) < 2:
                return False

            # Check if most recent week is above threshold
            # and previous week(s) were below 60%
            current_rate = rates[0]
            had_low_week = any(r < 0.6 for r in rates[1:])

            return current_rate >= threshold and had_low_week


async def count_stats_views(user_id: str) -> int:
    """
    Count how many times user has viewed statistics

    Note: This would need a tracking table in production.
    For now, estimate based on reminder analytics calls.
    """
    # Placeholder - in production, track this in a separate table
    return 0  # TODO: Implement stats view tracking
