"""
Service Container - Dependency Injection Container

Simple DI container for managing service instances and their dependencies.
Uses lazy loading to only instantiate services when first accessed.
"""

from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ServiceContainer:
    """
    Simple dependency injection container for services.

    Services are lazy-loaded on first access via properties.
    Infrastructure dependencies (db, memory_manager, reminder_manager) are injected.
    """

    # Infrastructure dependencies (injected)
    db: object  # DatabaseConnection instance
    memory_manager: object  # MemoryFileManager instance
    reminder_manager: Optional[object] = None  # ReminderManager (optional, set after bot creation)

    # Services (lazy-loaded via properties)
    _user_service: Optional[object] = field(default=None, init=False, repr=False)
    _food_service: Optional[object] = field(default=None, init=False, repr=False)
    _gamification_service: Optional[object] = field(default=None, init=False, repr=False)
    _health_service: Optional[object] = field(default=None, init=False, repr=False)

    @property
    def user_service(self):
        """Get UserService instance (lazy-loaded)"""
        if self._user_service is None:
            from src.services.user_service import UserService
            self._user_service = UserService(self.db, self.memory_manager)
            logger.debug("UserService instantiated")
        return self._user_service

    @property
    def food_service(self):
        """Get FoodService instance (lazy-loaded)"""
        if self._food_service is None:
            from src.services.food_service import FoodService
            self._food_service = FoodService(self.db, self.memory_manager)
            logger.debug("FoodService instantiated")
        return self._food_service

    @property
    def gamification_service(self):
        """Get GamificationService instance (lazy-loaded)"""
        if self._gamification_service is None:
            from src.services.gamification_service import GamificationService
            self._gamification_service = GamificationService(self.db)
            logger.debug("GamificationService instantiated")
        return self._gamification_service

    @property
    def health_service(self):
        """Get HealthService instance (lazy-loaded)"""
        if self._health_service is None:
            from src.services.health_service import HealthService
            self._health_service = HealthService(
                self.db,
                self.memory_manager,
                self.reminder_manager
            )
            logger.debug("HealthService instantiated")
        return self._health_service


# Global container instance (initialized in main.py)
_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """
    Get the global service container.

    Returns:
        ServiceContainer: The global container instance

    Raises:
        RuntimeError: If container not initialized (call init_container first)
    """
    if _container is None:
        raise RuntimeError(
            "Service container not initialized. "
            "Call init_container() in main.py before using services."
        )
    return _container


def init_container(
    db: object,
    memory_manager: object,
    reminder_manager: Optional[object] = None
) -> ServiceContainer:
    """
    Initialize the global service container.

    Should be called once in main.py after infrastructure setup.

    Args:
        db: Database connection instance
        memory_manager: MemoryFileManager instance
        reminder_manager: Optional ReminderManager instance (can be set later)

    Returns:
        ServiceContainer: The initialized container
    """
    global _container

    _container = ServiceContainer(
        db=db,
        memory_manager=memory_manager,
        reminder_manager=reminder_manager
    )

    logger.info("Service container initialized")
    return _container


def set_reminder_manager(reminder_manager: object) -> None:
    """
    Set the reminder manager on the global container.

    Called after bot creation since reminder_manager needs bot application.

    Args:
        reminder_manager: ReminderManager instance
    """
    if _container is None:
        raise RuntimeError("Service container not initialized")

    _container.reminder_manager = reminder_manager
    logger.info("ReminderManager set on service container")
