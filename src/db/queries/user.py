"""User management database queries"""
import json
import logging
from typing import Optional
from datetime import datetime
from src.db.connection import db
from src.models.user import UserProfile

logger = logging.getLogger(__name__)


# User operations
async def create_user(telegram_id: str) -> None:
    """Create new user in database"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO users (telegram_id) VALUES (%s) ON CONFLICT (telegram_id) DO NOTHING",
                (telegram_id,)
            )
            await conn.commit()
    logger.info(f"Created user: {telegram_id}")


async def user_exists(telegram_id: str) -> bool:
    """Check if user exists"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM users WHERE telegram_id = %s",
                (telegram_id,)
            )
            return await cur.fetchone() is not None


# Invite code operations
async def create_invite_code(
    code: str,
    created_by: str,
    max_uses: Optional[int] = None,
    tier: str = 'free',
    trial_days: int = 0,
    expires_at: Optional[datetime] = None,
    is_master_code: bool = False,
    description: Optional[str] = None
) -> str:
    """Create a new invite code (supports master codes with unlimited uses)"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO invite_codes (code, created_by, max_uses, tier, trial_days, expires_at, is_master_code, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (code, created_by, max_uses, tier, trial_days, expires_at, is_master_code, description)
            )
            result = await cur.fetchone()
            await conn.commit()

            if is_master_code:
                logger.info(f"Created MASTER CODE: {code} - {description}")
            else:
                logger.info(f"Created invite code: {code}")

            return str(result['id'])


async def validate_invite_code(code: str) -> Optional[dict]:
    """
    Validate an invite code and return its details if valid
    Returns None if code is invalid, expired, or used up
    Master codes bypass max_uses check and can be used indefinitely
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, code, max_uses, uses_count, tier, trial_days, expires_at, active, is_master_code, description
                FROM invite_codes
                WHERE code = %s
                """,
                (code,)
            )
            result = await cur.fetchone()

            if not result:
                return None

            code_id, code_str, max_uses, uses_count, tier, trial_days, expires_at, active, is_master_code, description = result

            # Check if code is active
            if not active:
                logger.warning(f"Invite code {code} is inactive")
                return None

            # Check if code has expired
            if expires_at and datetime.now() > expires_at:
                logger.warning(f"Invite code {code} has expired")
                return None

            # Check if code has remaining uses (SKIP for master codes)
            if not is_master_code:
                if max_uses is not None and uses_count >= max_uses:
                    logger.warning(f"Invite code {code} has reached max uses ({max_uses})")
                    return None
            else:
                logger.info(f"Validating MASTER CODE: {code} (unlimited uses, current count: {uses_count})")

            return {
                'id': str(code_id),
                'code': code_str,
                'tier': tier,
                'trial_days': trial_days,
                'is_master_code': is_master_code,
                'description': description
            }


async def use_invite_code(code: str, telegram_id: str) -> bool:
    """
    Mark invite code as used and activate user
    Returns True if successful, False otherwise
    Supports both regular codes and master codes (unlimited uses)
    """
    # Validate code FIRST (before incrementing)
    code_details = await validate_invite_code(code)
    if not code_details:
        return False

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Increment uses_count
            await cur.execute(
                """
                UPDATE invite_codes
                SET uses_count = uses_count + 1
                WHERE code = %s
                RETURNING uses_count, is_master_code, max_uses
                """,
                (code,)
            )
            usage_info = await cur.fetchone()

            if usage_info:
                uses_count, is_master_code, max_uses = usage_info
                if is_master_code:
                    logger.info(f"Master code {code} used (total uses: {uses_count}, unlimited)")
                else:
                    logger.info(f"Invite code {code} used ({uses_count}/{max_uses or 'unlimited'})")

            # Activate user with appropriate subscription
            trial_days = code_details['trial_days']
            tier = code_details['tier']

            if trial_days > 0:
                # Set trial subscription
                from datetime import timedelta
                end_date = datetime.now() + timedelta(days=trial_days)
                await cur.execute(
                    """
                    UPDATE users
                    SET subscription_status = 'trial',
                        subscription_tier = %s,
                        subscription_start_date = NOW(),
                        subscription_end_date = %s,
                        activated_at = NOW(),
                        invite_code_used = %s
                    WHERE telegram_id = %s
                    """,
                    (tier, end_date, code, telegram_id)
                )
            else:
                # Set active subscription (no expiry)
                await cur.execute(
                    """
                    UPDATE users
                    SET subscription_status = 'active',
                        subscription_tier = %s,
                        subscription_start_date = NOW(),
                        activated_at = NOW(),
                        invite_code_used = %s
                    WHERE telegram_id = %s
                    """,
                    (tier, code, telegram_id)
                )

            await conn.commit()
            logger.info(f"User {telegram_id} activated with code {code}")
            return True


async def get_user_subscription_status(telegram_id: str) -> Optional[dict]:
    """Get user's subscription status"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT subscription_status, subscription_tier, subscription_start_date,
                       subscription_end_date, activated_at, invite_code_used
                FROM users
                WHERE telegram_id = %s
                """,
                (telegram_id,)
            )
            result = await cur.fetchone()

            if not result:
                return None

            status, tier, start_date, end_date, activated_at, code_used = result

            return {
                'status': status,
                'tier': tier,
                'start_date': start_date,
                'end_date': end_date,
                'activated_at': activated_at,
                'invite_code_used': code_used
            }


async def get_master_codes() -> list:
    """Get all active master codes"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT code, tier, trial_days, description, uses_count, created_at, active
                FROM invite_codes
                WHERE is_master_code = true
                ORDER BY created_at DESC
                """
            )
            return await cur.fetchall()


async def deactivate_invite_code(code: str) -> bool:
    """
    Deactivate an invite code (sets active=false)
    Used to disable compromised or unwanted codes
    Returns True if successful, False if code not found
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE invite_codes
                SET active = false
                WHERE code = %s
                RETURNING id, is_master_code
                """,
                (code,)
            )
            result = await cur.fetchone()
            await conn.commit()

            if result:
                code_id, is_master = result
                code_type = "MASTER CODE" if is_master else "invite code"
                logger.warning(f"Deactivated {code_type}: {code}")
                return True
            else:
                logger.warning(f"Attempted to deactivate non-existent code: {code}")
                return False


# ==========================================
# Onboarding State Management
# ==========================================

async def get_onboarding_state(user_id: str) -> Optional[dict]:
    """Get current onboarding state for user"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT onboarding_path, current_step, step_data,
                       completed_steps, started_at, completed_at, last_interaction_at
                FROM user_onboarding_state
                WHERE user_id = %s
                """,
                (user_id,)
            )
            row = await cur.fetchone()
            return dict(row) if row else None


async def start_onboarding(user_id: str, path: str) -> None:
    """
    Initialize or update onboarding state for a user

    Args:
        user_id: Telegram user ID
        path: Onboarding path - "pending" (initial), "quick", "full", or "chat"

    Note: Only sets current_step to 'path_selection' when path is "pending".
    When path is quick/full/chat, only updates the path without resetting current_step.
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            if path == "pending":
                # Initial state: user hasn't selected a path yet
                await cur.execute(
                    """
                    INSERT INTO user_onboarding_state (user_id, onboarding_path, current_step)
                    VALUES (%s, %s, 'path_selection')
                    ON CONFLICT (user_id) DO UPDATE SET
                        onboarding_path = EXCLUDED.onboarding_path,
                        current_step = 'path_selection',
                        started_at = CURRENT_TIMESTAMP,
                        last_interaction_at = CURRENT_TIMESTAMP
                    """,
                    (user_id, path)
                )
            else:
                # User selected a path: update path but DON'T reset current_step
                await cur.execute(
                    """
                    INSERT INTO user_onboarding_state (user_id, onboarding_path, current_step)
                    VALUES (%s, %s, 'path_selection')
                    ON CONFLICT (user_id) DO UPDATE SET
                        onboarding_path = EXCLUDED.onboarding_path,
                        last_interaction_at = CURRENT_TIMESTAMP
                    """,
                    (user_id, path)
                )
            await conn.commit()
    logger.info(f"Started onboarding for {user_id} on path: {path}")


async def update_onboarding_step(
    user_id: str,
    new_step: str,
    step_data: dict = None,
    mark_complete: str = None
) -> None:
    """Update user's current onboarding step and optionally mark previous step complete"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            if mark_complete:
                # Mark previous step as complete and advance
                await cur.execute(
                    """
                    UPDATE user_onboarding_state
                    SET current_step = %s,
                        step_data = %s,
                        completed_steps = array_append(completed_steps, %s),
                        last_interaction_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                    """,
                    (new_step, json.dumps(step_data or {}), mark_complete, user_id)
                )
            else:
                # Just update current step
                await cur.execute(
                    """
                    UPDATE user_onboarding_state
                    SET current_step = %s,
                        step_data = %s,
                        last_interaction_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                    """,
                    (new_step, json.dumps(step_data or {}), user_id)
                )
            await conn.commit()
    logger.info(f"Updated onboarding step for {user_id}: {new_step}")


async def complete_onboarding(user_id: str) -> None:
    """Mark onboarding as completed"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE user_onboarding_state
                SET current_step = 'completed',
                    completed_at = CURRENT_TIMESTAMP,
                    last_interaction_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                """,
                (user_id,)
            )
            await conn.commit()
    logger.info(f"Completed onboarding for {user_id}")


async def log_feature_discovery(
    user_id: str,
    feature_name: str,
    discovery_method: str = "contextual"
) -> None:
    """Log when a user discovers a feature"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO feature_discovery_log
                (user_id, feature_name, discovery_method)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, feature_name) DO NOTHING
                """,
                (user_id, feature_name, discovery_method)
            )
            await conn.commit()
    logger.info(f"Logged feature discovery: {user_id} -> {feature_name}")


async def log_feature_usage(user_id: str, feature_name: str) -> None:
    """Log when a user actually uses a feature"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO feature_discovery_log
                (user_id, feature_name, first_used_at, usage_count, last_used_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, feature_name)
                DO UPDATE SET
                    first_used_at = COALESCE(feature_discovery_log.first_used_at, CURRENT_TIMESTAMP),
                    usage_count = feature_discovery_log.usage_count + 1,
                    last_used_at = CURRENT_TIMESTAMP
                """,
                (user_id, feature_name)
            )
            await conn.commit()
    logger.info(f"Logged feature usage: {user_id} used {feature_name}")


# Profile and Preference Audit Functions
async def audit_profile_update(
    user_id: str,
    field_name: str,
    old_value: Optional[str],
    new_value: str,
    updated_by: str = "user"
) -> None:
    """
    Log profile field update to audit table

    Args:
        user_id: User's Telegram ID
        field_name: Name of the profile field being updated
        old_value: Previous value (None if new field)
        new_value: New value being set
        updated_by: Source of update ('user' or 'auto')

    Purpose:
        Creates audit trail for profile changes to track data modifications
        and help debug issues where user data changes unexpectedly.
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO profile_update_audit (user_id, field_name, old_value, new_value, updated_by)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, field_name, old_value, new_value, updated_by)
            )
            await conn.commit()
    logger.info(f"Audited profile update for user {user_id}: {field_name}")


async def audit_preference_update(
    user_id: str,
    preference_name: str,
    old_value: Optional[str],
    new_value: str,
    updated_by: str = "user"
) -> None:
    """
    Log preference change to audit table

    Args:
        user_id: User's Telegram ID
        preference_name: Name of the preference being updated
        old_value: Previous value (None if new preference)
        new_value: New value being set
        updated_by: Source of update ('user' or 'auto')

    Purpose:
        Creates audit trail for preference changes to track modifications
        and understand user behavior patterns.
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO preference_update_audit (user_id, preference_name, old_value, new_value, updated_by)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, preference_name, old_value, new_value, updated_by)
            )
            await conn.commit()
    logger.info(f"Audited preference update for user {user_id}: {preference_name}")
