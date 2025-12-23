"""Food-related Pydantic models"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class Micronutrients(BaseModel):
    """Micronutrient breakdown"""
    fiber: Optional[float] = None  # grams
    sodium: Optional[float] = None  # milligrams
    sugar: Optional[float] = None  # grams
    vitamin_c: Optional[float] = None  # milligrams
    calcium: Optional[float] = None  # milligrams
    iron: Optional[float] = None  # milligrams


class FoodMacros(BaseModel):
    """Macronutrient breakdown"""
    protein: float  # grams
    carbs: float  # grams
    fat: float  # grams
    micronutrients: Optional[Micronutrients] = None


class FoodItem(BaseModel):
    """Individual food item"""
    name: str
    quantity: str  # "1 cup", "100g", "1 medium apple"
    calories: int
    macros: FoodMacros
    verification_source: Optional[str] = None  # "usda", "ai_estimate", etc.
    confidence_score: Optional[float] = None  # 0.0-1.0 for verification quality
    food_category: Optional[str] = None  # "protein", "vegetables", "grains", etc.
    confidence: Optional[str] = None  # "high", "medium", "low" - for individual food confidence


class FoodEntry(BaseModel):
    """Complete food log entry"""
    id: UUID = Field(default_factory=uuid4)
    user_id: str  # telegram_id
    timestamp: datetime = Field(default_factory=datetime.now)
    photo_path: Optional[str] = None
    foods: list[FoodItem]
    total_calories: int
    total_macros: FoodMacros
    meal_type: Optional[str] = None  # breakfast, lunch, dinner, snack
    notes: Optional[str] = None


class VisionAnalysisResult(BaseModel):
    """Result from vision AI food analysis"""
    foods: list[FoodItem]
    confidence: str  # high, medium, low
    clarifying_questions: list[str] = Field(default_factory=list)
    timestamp: Optional[datetime] = None  # When the food was actually eaten (if mentioned in caption)
