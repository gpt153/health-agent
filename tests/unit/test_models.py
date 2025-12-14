"""Unit tests for Pydantic models"""
import pytest
from datetime import datetime
from uuid import uuid4
from src.models.user import UserProfile, UserPreferences
from src.models.food import FoodItem, FoodMacros, VisionAnalysisResult
from src.models.tracking import TrackingCategory, TrackingEntry, TrackingField


def test_user_preferences_defaults():
    """Test UserPreferences with defaults"""
    prefs = UserPreferences()

    assert prefs.brevity == "medium"
    assert prefs.tone == "friendly"
    assert prefs.humor is True
    assert prefs.coaching_style == "supportive"


def test_user_profile_creation():
    """Test creating UserProfile"""
    profile = UserProfile(
        telegram_id="123456",
        name="John Doe",
        age=30,
        height_cm=180.0,
        current_weight_kg=80.0,
        target_weight_kg=75.0,
        goal_type="lose_weight",
    )

    assert profile.telegram_id == "123456"
    assert profile.name == "John Doe"
    assert profile.age == 30
    assert profile.goal_type == "lose_weight"


def test_food_macros_validation():
    """Test FoodMacros model"""
    macros = FoodMacros(protein=30.0, carbs=50.0, fat=20.0)

    assert macros.protein == 30.0
    assert macros.carbs == 50.0
    assert macros.fat == 20.0


def test_food_item_creation():
    """Test FoodItem model"""
    food = FoodItem(
        name="Chicken Breast",
        quantity="200g",
        calories=330,
        macros=FoodMacros(protein=62.0, carbs=0.0, fat=7.0),
    )

    assert food.name == "Chicken Breast"
    assert food.calories == 330
    assert food.macros.protein == 62.0


def test_vision_analysis_result():
    """Test VisionAnalysisResult model"""
    foods = [
        FoodItem(
            name="Apple",
            quantity="1 medium",
            calories=95,
            macros=FoodMacros(protein=0.5, carbs=25.0, fat=0.3),
        )
    ]

    result = VisionAnalysisResult(
        foods=foods, confidence="high", clarifying_questions=["Is it a Granny Smith?"]
    )

    assert len(result.foods) == 1
    assert result.confidence == "high"
    assert len(result.clarifying_questions) == 1


def test_tracking_field():
    """Test TrackingField model"""
    field = TrackingField(
        type="number", label="Hours of Sleep", min_value=0.0, max_value=24.0, required=True
    )

    assert field.type == "number"
    assert field.label == "Hours of Sleep"
    assert field.min_value == 0.0
    assert field.max_value == 24.0


def test_tracking_category():
    """Test TrackingCategory model"""
    field = TrackingField(type="number", label="Hours", required=True)

    category = TrackingCategory(
        user_id="123456",
        name="Sleep Tracking",
        fields={"hours": field},
        active=True,
    )

    assert category.user_id == "123456"
    assert category.name == "Sleep Tracking"
    assert "hours" in category.fields
    assert category.active is True


def test_tracking_entry():
    """Test TrackingEntry model"""
    category_id = uuid4()

    entry = TrackingEntry(
        user_id="123456",
        category_id=category_id,
        data={"hours": 8.5, "quality": "good"},
        notes="Slept well",
    )

    assert entry.user_id == "123456"
    assert entry.category_id == category_id
    assert entry.data["hours"] == 8.5
    assert entry.notes == "Slept well"


def test_user_profile_optional_fields():
    """Test UserProfile with only required fields"""
    profile = UserProfile(telegram_id="123456")

    assert profile.telegram_id == "123456"
    assert profile.name is None
    assert profile.age is None
    assert profile.height_cm is None


def test_model_serialization():
    """Test that models can be serialized to dict"""
    prefs = UserPreferences(brevity="brief", tone="casual")
    prefs_dict = prefs.model_dump()

    assert isinstance(prefs_dict, dict)
    assert prefs_dict["brevity"] == "brief"
    assert prefs_dict["tone"] == "casual"
