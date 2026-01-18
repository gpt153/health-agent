"""Food-related Pydantic models"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from uuid import UUID, uuid4
import logging

logger = logging.getLogger(__name__)


class Micronutrients(BaseModel):
    """Micronutrient breakdown"""
    fiber: Optional[float] = None  # grams
    sodium: Optional[float] = None  # milligrams
    sugar: Optional[float] = None  # grams
    vitamin_c: Optional[float] = None  # milligrams
    calcium: Optional[float] = None  # milligrams
    iron: Optional[float] = None  # milligrams

    @field_validator('fiber', 'sodium', 'sugar', 'vitamin_c', 'calcium', 'iron')
    @classmethod
    def no_negatives(cls, v: Optional[float]) -> Optional[float]:
        """Ensure no negative micronutrient values"""
        if v is not None and v < 0:
            raise ValueError("Micronutrient values cannot be negative")
        return v


class FoodMacros(BaseModel):
    """Macronutrient breakdown with validation"""
    protein: float = Field(ge=0, le=300, description="Protein in grams")
    carbs: float = Field(ge=0, le=500, description="Carbohydrates in grams")
    fat: float = Field(ge=0, le=200, description="Fat in grams")
    micronutrients: Optional[Micronutrients] = None

    @field_validator('protein', 'carbs', 'fat')
    @classmethod
    def no_negatives(cls, v: float) -> float:
        """Ensure no negative macro values"""
        if v < 0:
            raise ValueError("Macro values cannot be negative")
        return v


class FoodItem(BaseModel):
    """Individual food item with validation"""
    name: str = Field(min_length=1, max_length=200, description="Food name")
    quantity: str = Field(min_length=1, max_length=100, description="Quantity description")
    calories: int = Field(ge=0, le=5000, description="Calories in kcal")
    macros: FoodMacros
    verification_source: Optional[str] = None  # "usda", "ai_estimate", etc.
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)  # 0.0-1.0 for verification quality
    food_category: Optional[str] = None  # "protein", "vegetables", "grains", etc.
    confidence: Optional[str] = None  # "high", "medium", "low" - for individual food confidence

    @field_validator('calories')
    @classmethod
    def reasonable_calories(cls, v: int) -> int:
        """Log warning for unusually high calories"""
        if v > 3000:
            logger.warning(f"Very high calorie value detected: {v} kcal")
        return v

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Trim and validate food name"""
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Food name cannot be empty or only whitespace")
        return trimmed

    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v: str) -> str:
        """Trim and validate quantity description"""
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Quantity cannot be empty or only whitespace")
        return trimmed


class FoodEntry(BaseModel):
    """Complete food log entry"""
    id: UUID = Field(default_factory=uuid4)
    user_id: str  # telegram_id
    timestamp: datetime = Field(default_factory=datetime.now)
    photo_path: Optional[str] = None
    foods: list[FoodItem]
    total_calories: int = Field(ge=0, le=10000, description="Total calories for entry")
    total_macros: FoodMacros
    meal_type: Optional[str] = None  # breakfast, lunch, dinner, snack
    notes: Optional[str] = Field(None, max_length=4000, description="Optional notes")

    @field_validator('notes')
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        """Validate notes field"""
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                return None  # Empty notes become None
            return trimmed
        return v

    @field_validator('foods')
    @classmethod
    def validate_foods_list(cls, v: list[FoodItem]) -> list[FoodItem]:
        """Ensure at least one food item"""
        if not v:
            raise ValueError("Food entry must contain at least one food item")
        return v


class VisionAnalysisResult(BaseModel):
    """Result from vision AI food analysis"""
    foods: list[FoodItem]
    confidence: str  # high, medium, low
    clarifying_questions: list[str] = Field(default_factory=list)
    timestamp: Optional[datetime] = None  # When the food was actually eaten (if mentioned in caption)
