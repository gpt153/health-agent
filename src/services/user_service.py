"""
UserService - User Management Business Logic

Handles user lifecycle, authentication, onboarding, preferences, and subscriptions.
Separates business logic from Telegram handlers and database layer.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from src.db import queries

logger = logging.getLogger(__name__)


class UserService:
    """
    Service for user management and preferences.

    Responsibilities:
    - User lifecycle management (create, update, authenticate)
    - Onboarding flow orchestration
    - User preferences and settings management
    - Subscription/activation handling
    """

    def __init__(self, db_connection, memory_manager):
        """
        Initialize UserService.

        Args:
            db_connection: Database connection instance
            memory_manager: MemoryFileManager instance for user files
        """
        self.db = db_connection
        self.memory = memory_manager

    async def create_user(self, telegram_id: str) -> Dict[str, Any]:
        """
        Create a new user with default settings.

        Args:
            telegram_id: Telegram user ID

        Returns:
            dict: {
                'success': bool,
                'telegram_id': str,
                'message': str
            }
        """
        try:
            # Check if user already exists
            if await queries.user_exists(telegram_id):
                logger.info(f"User {telegram_id} already exists")
                return {
                    'success': True,
                    'telegram_id': telegram_id,
                    'message': 'User already exists',
                    'existing': True
                }

            # Create user in database
            await queries.create_user(telegram_id)

            # Create user memory files
            await self.memory.create_user_files(telegram_id)

            logger.info(f"Created new user: {telegram_id}")

            return {
                'success': True,
                'telegram_id': telegram_id,
                'message': 'User created successfully',
                'existing': False
            }

        except Exception as e:
            logger.error(f"Error creating user {telegram_id}: {e}", exc_info=True)
            return {
                'success': False,
                'telegram_id': telegram_id,
                'message': f'Error creating user: {str(e)}',
                'error': str(e)
            }

    async def get_user(self, telegram_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by telegram ID.

        Args:
            telegram_id: Telegram user ID

        Returns:
            User data dict if exists, None otherwise
        """
        try:
            exists = await queries.user_exists(telegram_id)
            if not exists:
                return None

            # Get subscription status
            subscription = await queries.get_user_subscription_status(telegram_id)

            return {
                'telegram_id': telegram_id,
                'exists': True,
                'subscription': subscription
            }

        except Exception as e:
            logger.error(f"Error getting user {telegram_id}: {e}", exc_info=True)
            return None

    async def user_exists(self, telegram_id: str) -> bool:
        """
        Check if user exists.

        Args:
            telegram_id: Telegram user ID

        Returns:
            True if user exists, False otherwise
        """
        try:
            return await queries.user_exists(telegram_id)
        except Exception as e:
            logger.error(f"Error checking user existence {telegram_id}: {e}", exc_info=True)
            return False

    async def activate_user(
        self,
        telegram_id: str,
        invite_code: str
    ) -> Dict[str, Any]:
        """
        Activate user with invite code.

        Args:
            telegram_id: Telegram user ID
            invite_code: Invite code to validate and use

        Returns:
            dict: {
                'success': bool,
                'message': str,
                'subscription': dict (if successful)
            }
        """
        try:
            # Validate invite code
            code_details = await queries.validate_invite_code(invite_code)

            if not code_details:
                logger.warning(f"Invalid invite code for user {telegram_id}: {invite_code}")
                return {
                    'success': False,
                    'message': 'Invalid or expired invite code'
                }

            # Use the invite code (activates user)
            success = await queries.use_invite_code(invite_code, telegram_id)

            if not success:
                return {
                    'success': False,
                    'message': 'Failed to activate user with invite code'
                }

            # Get updated subscription status
            subscription = await queries.get_user_subscription_status(telegram_id)

            logger.info(f"User {telegram_id} activated with code {invite_code}")

            return {
                'success': True,
                'message': 'User activated successfully',
                'subscription': subscription,
                'code_details': code_details
            }

        except Exception as e:
            logger.error(f"Error activating user {telegram_id}: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'Error activating user: {str(e)}',
                'error': str(e)
            }

    async def is_authorized(self, telegram_id: str) -> bool:
        """
        Check if user is authorized to use the bot.

        A user is authorized if they have an active or trial subscription.

        Args:
            telegram_id: Telegram user ID

        Returns:
            True if authorized, False otherwise
        """
        try:
            subscription = await queries.get_user_subscription_status(telegram_id)

            if not subscription:
                return False

            status = subscription.get('status')

            # User is authorized if status is 'active' or 'trial'
            return status in ('active', 'trial')

        except Exception as e:
            logger.error(f"Error checking authorization for {telegram_id}: {e}", exc_info=True)
            return False

    async def get_onboarding_state(
        self,
        telegram_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get current onboarding state for user.

        Args:
            telegram_id: Telegram user ID

        Returns:
            Onboarding state dict if exists, None otherwise
        """
        try:
            return await queries.get_onboarding_state(telegram_id)
        except Exception as e:
            logger.error(f"Error getting onboarding state for {telegram_id}: {e}", exc_info=True)
            return None

    async def update_onboarding_state(
        self,
        telegram_id: str,
        state: Dict[str, Any]
    ) -> bool:
        """
        Update onboarding progress.

        Args:
            telegram_id: Telegram user ID
            state: Onboarding state data to update

        Returns:
            True if successful, False otherwise
        """
        try:
            await queries.update_onboarding_state(telegram_id, state)
            logger.info(f"Updated onboarding state for {telegram_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating onboarding state for {telegram_id}: {e}", exc_info=True)
            return False

    async def complete_onboarding(self, telegram_id: str) -> bool:
        """
        Mark onboarding as complete.

        Args:
            telegram_id: Telegram user ID

        Returns:
            True if successful, False otherwise
        """
        try:
            await queries.complete_onboarding(telegram_id)
            logger.info(f"Completed onboarding for {telegram_id}")
            return True
        except Exception as e:
            logger.error(f"Error completing onboarding for {telegram_id}: {e}", exc_info=True)
            return False

    async def update_preferences(
        self,
        telegram_id: str,
        preference_key: str,
        preference_value: Any
    ) -> bool:
        """
        Update user preferences.

        Args:
            telegram_id: Telegram user ID
            preference_key: Preference key (e.g., 'timezone', 'units')
            preference_value: Preference value

        Returns:
            True if successful, False otherwise
        """
        try:
            await self.memory.update_preferences(
                telegram_id,
                preference_key,
                preference_value
            )
            logger.info(f"Updated preference {preference_key} for {telegram_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating preferences for {telegram_id}: {e}", exc_info=True)
            return False

    async def get_preferences(self, telegram_id: str) -> Dict[str, Any]:
        """
        Get user preferences.

        Args:
            telegram_id: Telegram user ID

        Returns:
            Preferences dict
        """
        try:
            user_memory = await self.memory.load_user_memory(telegram_id)
            prefs_content = user_memory.get("preferences", "")

            # Parse preferences from markdown content
            # For now, return raw content (can be enhanced later)
            return {
                'raw_content': prefs_content,
                'telegram_id': telegram_id
            }
        except Exception as e:
            logger.error(f"Error getting preferences for {telegram_id}: {e}", exc_info=True)
            return {}

    async def get_subscription_status(
        self,
        telegram_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user subscription details.

        Args:
            telegram_id: Telegram user ID

        Returns:
            Subscription dict with status, tier, dates, etc.
        """
        try:
            return await queries.get_user_subscription_status(telegram_id)
        except Exception as e:
            logger.error(f"Error getting subscription for {telegram_id}: {e}", exc_info=True)
            return None

    async def set_timezone(
        self,
        telegram_id: str,
        timezone: str
    ) -> bool:
        """
        Set user's timezone.

        Args:
            telegram_id: Telegram user ID
            timezone: Timezone string (e.g., 'America/New_York')

        Returns:
            True if successful, False otherwise
        """
        return await self.update_preferences(telegram_id, 'timezone', timezone)

    async def get_timezone(self, telegram_id: str) -> Optional[str]:
        """
        Get user's timezone.

        Args:
            telegram_id: Telegram user ID

        Returns:
            Timezone string if set, None otherwise
        """
        try:
            from src.utils.timezone_helper import get_timezone_from_profile
            return get_timezone_from_profile(telegram_id)
        except Exception as e:
            logger.error(f"Error getting timezone for {telegram_id}: {e}", exc_info=True)
            return None
