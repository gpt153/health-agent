"""
Service Layer Package

This package contains business logic services that separate concerns between
the presentation layer (Telegram handlers) and the data access layer (database queries).

Services:
- UserService: User management, onboarding, preferences, subscriptions
- FoodService: Food analysis, meal logging, nutrition validation
- GamificationService: XP, streaks, achievements, leaderboards
- HealthService: Tracking, reminders, trends, health reports
"""

from src.services.container import ServiceContainer, get_container, init_container

__all__ = [
    "ServiceContainer",
    "get_container",
    "init_container",
]
