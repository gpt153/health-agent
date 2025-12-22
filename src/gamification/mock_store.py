"""
Temporary Mock Store for Challenges

FIXME: This is a temporary stub to prevent import errors.
The challenge system needs to be migrated to use PostgreSQL instead.

This file should be removed once challenges are fully database-backed.
See issue #22 implementation plan Phase 2 for proper database migration.
"""

import logging

logger = logging.getLogger(__name__)


class MockStore:
    """Temporary in-memory store for challenges"""

    def __init__(self):
        self._user_challenges = {}
        logger.warning(
            "MockStore initialized - challenges are NOT persisted! "
            "This is a temporary workaround until PostgreSQL migration is complete."
        )

    def save_user_challenge(self, user_challenge):
        """Save user challenge (temporary - not persisted)"""
        key = f"{user_challenge.user_id}_{user_challenge.challenge_id}"
        self._user_challenges[key] = user_challenge
        logger.debug(f"Saved challenge {key} to mock store (NOT PERSISTED)")

    def get_user_challenge(self, user_id: str, challenge_id: str):
        """Get user challenge"""
        key = f"{user_id}_{challenge_id}"
        return self._user_challenges.get(key)

    def get_all_user_challenges(self, user_id: str):
        """Get all user challenges"""
        return [
            uc for uc in self._user_challenges.values()
            if uc.user_id == user_id
        ]


# Global instance (TEMPORARY)
mock_store = MockStore()
