"""
Service Layer Package

This package contains business logic services that separate concerns between
the presentation layer (Telegram handlers) and the data access layer (database queries).

Core Services (Service Layer Architecture):
- UserService: User management, onboarding, preferences, subscriptions
- FoodService: Food analysis, meal logging, nutrition validation
- GamificationService: XP, streaks, achievements, leaderboards
- HealthService: Tracking, reminders, trends, health reports

External Integration Services:
- ImageEmbeddingService: Image embedding for visual food search
- VisualFoodSearchService: Visual similarity search for food items
- PlateRecognitionService: Plate and portion recognition
- FormulaDetectionService: Detect food preparation formulas
- FormulaSuggestionService: Suggest formulas based on patterns
"""

from src.services.container import ServiceContainer, get_container, init_container, set_reminder_manager
from src.services.image_embedding import get_embedding_service, ImageEmbeddingService
from src.services.visual_food_search import get_visual_search_service, VisualFoodSearchService
from src.services.plate_recognition import get_plate_recognition_service, PlateRecognitionService
from src.services.formula_detection import FormulaDetectionService, get_formula_detection_service
from src.services.formula_suggestions import FormulaSuggestionService, get_suggestion_service

__all__ = [
    # Service Layer Container
    "ServiceContainer",
    "get_container",
    "init_container",
    "set_reminder_manager",
    # External Integration Services
    "get_embedding_service",
    "ImageEmbeddingService",
    "get_visual_search_service",
    "VisualFoodSearchService",
    "get_plate_recognition_service",
    "PlateRecognitionService",
    "FormulaDetectionService",
    "get_formula_detection_service",
    "FormulaSuggestionService",
    "get_suggestion_service",
]
