"""Services module for business logic and external integrations"""

from src.services.image_embedding import get_embedding_service, ImageEmbeddingService
from src.services.visual_food_search import get_visual_search_service, VisualFoodSearchService
from src.services.plate_recognition import get_plate_recognition_service, PlateRecognitionService
from src.services.formula_detection import FormulaDetectionService, get_formula_detection_service
from src.services.formula_suggestions import FormulaSuggestionService, get_suggestion_service

__all__ = [
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
