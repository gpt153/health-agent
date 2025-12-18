"""Food-related Pydantic models"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class FoodMacros(BaseModel):
    """Macronutrient breakdown"""
    protein: float  # grams
    carbs: float  # grams
    fat: float  # grams


class FoodItem(BaseModel):
    """Individual food item"""
    name: str
    quantity: str  # "1 cup", "100g", "1 medium apple"
    calories: int
    macros: FoodMacros


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
