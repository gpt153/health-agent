"""Telegram authentication utilities"""
import logging
from src.db.connection import db

logger = logging.getLogger(__name__)


async def is_authorized(telegram_id: str) -> bool:
    """
    Check if telegram user is authorized based on subscription status

    Returns True if user has active, trial, or cancelled (but not expired) subscription
    Returns False if user is pending, expired, or doesn't exist
    """
    try:
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT subscription_status, subscription_end_date
                    FROM users
                    WHERE telegram_id = %s
                    """,
                    (telegram_id,)
                )
                result = await cur.fetchone()

                if not result:
                    return False

                status = result['subscription_status']
                end_date = result.get('subscription_end_date')

                # Allow active and trial users
                if status in ('active', 'trial'):
                    return True

                # Allow cancelled users if they still have time left
                if status == 'cancelled' and end_date:
                    from datetime import datetime
                    if datetime.now() < end_date:
                        return True

                # pending and expired users cannot use bot
                return False

    except Exception as e:
        logger.error(f"Error checking authorization for {telegram_id}: {e}")
        return False


def is_admin(telegram_id: str) -> bool:
    """Check if user is admin"""
    ADMIN_USER_ID = "7376426503"
    return telegram_id == ADMIN_USER_ID
