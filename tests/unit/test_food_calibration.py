"""Tests for food calibration system (Phase 4)"""
import pytest
from datetime import datetime
from src.utils.food_calibration import (
    detect_correction_intent,
    extract_corrected_calories,
    categorize_food,
    save_correction,
    get_user_corrections,
    apply_calibration,
    calibrate_foods,
    get_correction_summary,
    CorrectionPattern
)
from src.models.food import FoodItem, FoodMacros


def test_detect_correction_intent_positive():
    """Test detecting correction phrases"""

    assert detect_correction_intent("that's wrong, it should be 220 cal") == True
    assert detect_correction_intent("actually it was 180 calories") == True
    assert detect_correction_intent("too high, more like 150") == True
    assert detect_correction_intent("incorrect, really 200 cal") == True
    assert detect_correction_intent("that's not right") == True
    assert detect_correction_intent("way off, should be 250") == True
    assert detect_correction_intent("update it to 300 calories") == True


def test_detect_correction_intent_negative():
    """Test not detecting non-correction phrases"""

    assert detect_correction_intent("I ate chicken for lunch") == False
    assert detect_correction_intent("How many calories in an apple?") == False
    assert detect_correction_intent("Great job, thanks!") == False
    assert detect_correction_intent("What should I eat for dinner?") == False


def test_extract_corrected_calories():
    """Test extracting calorie values from correction messages"""

    assert extract_corrected_calories("should be 220 cal") == 220
    assert extract_corrected_calories("actually 180 calories") == 180
    assert extract_corrected_calories("more like 150") == 150
    assert extract_corrected_calories("really 200 cal") == 200
    assert extract_corrected_calories("update to 300 calories") == 300
    assert extract_corrected_calories("450") == 450


def test_extract_corrected_calories_no_value():
    """Test extraction when no calorie value present"""

    assert extract_corrected_calories("that's wrong") is None
    assert extract_corrected_calories("too high") is None
    assert extract_corrected_calories("incorrect") is None


def test_categorize_food_protein():
    """Test food categorization for protein sources"""

    assert categorize_food("Chicken breast") == "protein_meat"
    assert categorize_food("Grilled salmon") == "protein_meat"
    assert categorize_food("Beef steak") == "protein_meat"
    assert categorize_food("Turkey burger") == "protein_meat"
    assert categorize_food("Scrambled eggs") == "protein_other"
    assert categorize_food("Tofu stir fry") == "protein_other"


def test_categorize_food_vegetables():
    """Test food categorization for vegetables"""

    assert categorize_food("Mixed green salad") == "salad_greens"
    assert categorize_food("Caesar salad") == "salad_greens"
    assert categorize_food("Spinach") == "salad_greens"
    assert categorize_food("Grilled vegetables") == "vegetables"
    assert categorize_food("Steamed broccoli") == "vegetables"


def test_categorize_food_grains():
    """Test food categorization for grains"""

    assert categorize_food("White rice") == "grains"
    assert categorize_food("Pasta with sauce") == "grains"
    assert categorize_food("Quinoa bowl") == "grains"
    assert categorize_food("Whole wheat bread") == "bread"
    assert categorize_food("Sourdough toast") == "bread"


def test_categorize_food_restaurant():
    """Test food categorization for restaurant items"""

    assert categorize_food("Chipotle burrito bowl") == "restaurant_fast_food"
    assert categorize_food("McDonald's Big Mac") == "restaurant_fast_food"
    assert categorize_food("Pepperoni pizza") == "prepared_meal"
    assert categorize_food("Chicken sandwich") == "prepared_meal"


@pytest.mark.asyncio
async def test_save_and_retrieve_correction():
    """Test saving and retrieving user corrections"""

    user_id = "test_user_123"
    food_name = "Chicken breast"
    original_cal = 300
    corrected_cal = 220

    # Save correction
    await save_correction(
        user_id=user_id,
        food_name=food_name,
        original_calories=original_cal,
        corrected_calories=corrected_cal
    )

    # Retrieve corrections
    corrections = await get_user_corrections(user_id)

    assert len(corrections) >= 1
    assert any(c["food_name"] == food_name for c in corrections)


@pytest.mark.asyncio
async def test_apply_calibration_no_data():
    """Test calibration when no correction data exists"""

    food = FoodItem(
        name="Rare exotic food",
        quantity="100g",
        calories=200,
        macros=FoodMacros(protein=10, carbs=20, fat=8),
        verification_source="ai_estimate"
    )

    # Should return unchanged
    calibrated = await apply_calibration(food, user_id="new_user")

    assert calibrated.calories == 200
    assert calibrated.verification_source == "ai_estimate"


@pytest.mark.asyncio
async def test_apply_calibration_with_global_pattern():
    """Test calibration using global correction patterns"""

    # Salad category has pre-seeded correction factor of 0.6
    food = FoodItem(
        name="Mixed green salad",
        quantity="1 cup",
        calories=100,  # AI estimate
        macros=FoodMacros(protein=2, carbs=8, fat=1),
        verification_source="ai_estimate"
    )

    calibrated = await apply_calibration(food)

    # Should apply 0.6 factor (100 * 0.6 = 60)
    assert calibrated.calories < 100
    assert "calibrated" in calibrated.verification_source


@pytest.mark.asyncio
async def test_apply_calibration_with_user_corrections():
    """Test calibration using user-specific corrections"""

    user_id = "test_user_456"
    food_name = "Grilled chicken"

    # Save multiple user corrections (chicken is too high)
    await save_correction(user_id, food_name, 300, 220)  # -27%
    await save_correction(user_id, food_name, 280, 210)  # -25%

    # Try to calibrate new chicken entry
    food = FoodItem(
        name=food_name,
        quantity="150g",
        calories=300,
        macros=FoodMacros(protein=52, carbs=0, fat=6),
        verification_source="ai_estimate"
    )

    calibrated = await apply_calibration(food, user_id=user_id)

    # Should apply user's correction pattern (~0.74 factor)
    assert calibrated.calories < 300
    assert calibrated.calories > 200
    assert "user_calibrated" in calibrated.verification_source


@pytest.mark.asyncio
async def test_calibrate_foods_list():
    """Test calibrating a list of foods"""

    foods = [
        FoodItem(
            name="Mixed salad",
            quantity="1 cup",
            calories=100,
            macros=FoodMacros(protein=2, carbs=8, fat=1),
            verification_source="ai_estimate"
        ),
        FoodItem(
            name="Chicken breast",
            quantity="150g",
            calories=250,
            macros=FoodMacros(protein=52, carbs=0, fat=5),
            verification_source="ai_estimate"
        )
    ]

    calibrated = await calibrate_foods(foods)

    assert len(calibrated) == 2
    # Salad should be calibrated down (0.6 factor)
    assert calibrated[0].calories < foods[0].calories


@pytest.mark.asyncio
async def test_get_correction_summary_empty():
    """Test correction summary with no corrections"""

    summary = get_correction_summary("new_user_789")

    assert summary["total_corrections"] == 0
    assert summary["categories"] == {}
    assert summary["avg_correction_factor"] == 1.0


@pytest.mark.asyncio
async def test_get_correction_summary_with_data():
    """Test correction summary with correction data"""

    user_id = "test_user_summary"

    # Save various corrections
    await save_correction(user_id, "Chicken breast", 300, 250)  # 0.83
    await save_correction(user_id, "Grilled salmon", 280, 220)  # 0.79
    await save_correction(user_id, "Mixed salad", 100, 60)      # 0.60

    summary = get_correction_summary(user_id)

    assert summary["total_corrections"] >= 3
    assert len(summary["categories"]) > 0
    assert 0.5 < summary["avg_correction_factor"] < 1.0


def test_correction_pattern_model():
    """Test CorrectionPattern dataclass"""

    pattern = CorrectionPattern(
        food_category="protein_meat",
        avg_correction_factor=0.85,
        correction_count=10,
        last_updated=datetime.now(),
        confidence=1.0
    )

    assert pattern.food_category == "protein_meat"
    assert pattern.avg_correction_factor == 0.85
    assert pattern.correction_count == 10
    assert pattern.confidence == 1.0


@pytest.mark.asyncio
async def test_correction_factor_calculation():
    """Test that correction factors are calculated correctly"""

    user_id = "test_calc_user"

    # User consistently corrects chicken down by 20%
    await save_correction(user_id, "Chicken breast", 300, 240)  # 0.80
    await save_correction(user_id, "Chicken thigh", 320, 256)   # 0.80
    await save_correction(user_id, "Grilled chicken", 280, 224) # 0.80

    corrections = await get_user_corrections(user_id)

    # All should have factor ~0.80
    for c in corrections:
        assert 0.79 <= c["correction_factor"] <= 0.81


@pytest.mark.asyncio
async def test_minimum_corrections_threshold():
    """Test that calibration requires minimum number of corrections"""

    user_id = "test_threshold_user"

    # Only 1 correction - not enough to apply calibration
    await save_correction(user_id, "Test food", 200, 150)

    food = FoodItem(
        name="Test food",
        quantity="100g",
        calories=200,
        macros=FoodMacros(protein=10, carbs=20, fat=8),
        verification_source="ai_estimate"
    )

    calibrated = await apply_calibration(food, user_id=user_id)

    # Should NOT be calibrated (need 2+ corrections)
    assert calibrated.calories == 200


@pytest.mark.asyncio
async def test_over_correction_and_under_correction():
    """Test handling of both over and under-corrections"""

    user_id = "test_both_directions"

    # Over-correction (AI under-estimated)
    await save_correction(user_id, "Restaurant burger", 800, 1000)  # 1.25

    # Under-correction (AI over-estimated)
    await save_correction(user_id, "Small salad", 200, 100)  # 0.50

    corrections = await get_user_corrections(user_id)

    # Should have both types
    factors = [c["correction_factor"] for c in corrections]
    assert any(f > 1.0 for f in factors)  # Over-correction
    assert any(f < 1.0 for f in factors)  # Under-correction
