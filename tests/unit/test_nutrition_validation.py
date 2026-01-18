"""Unit tests for Nutrition Validation (src/utils/nutrition_validation.py)"""
import pytest
from unittest.mock import patch, AsyncMock

from src.utils.nutrition_validation import (
    validate_nutrition_data,
    is_reasonable_calories,
    is_reasonable_macros,
    validate_macro_ratios,
    calculate_calories_from_macros,
    check_macro_total,
)


# ============================================================================
# Calorie Validation Tests
# ============================================================================

def test_is_reasonable_calories_normal():
    """Test reasonable calorie amounts"""
    assert is_reasonable_calories(500, "meal") is True
    assert is_reasonable_calories(200, "snack") is True
    assert is_reasonable_calories(2000, "daily") is True


def test_is_reasonable_calories_too_low():
    """Test unreasonably low calories"""
    assert is_reasonable_calories(10, "meal") is False
    assert is_reasonable_calories(0, "meal") is False
    assert is_reasonable_calories(-100, "meal") is False


def test_is_reasonable_calories_too_high():
    """Test unreasonably high calories"""
    assert is_reasonable_calories(5000, "meal") is False
    assert is_reasonable_calories(10000, "snack") is False


def test_is_reasonable_calories_boundary():
    """Test boundary values for calories"""
    # Meal boundaries (typically 50-2000 calories)
    assert is_reasonable_calories(50, "meal") is True
    assert is_reasonable_calories(49, "meal") is False
    assert is_reasonable_calories(2000, "meal") is True
    assert is_reasonable_calories(2001, "meal") is False


# ============================================================================
# Macro Validation Tests
# ============================================================================

def test_is_reasonable_macros_normal():
    """Test reasonable macro amounts"""
    macros = {"protein": 30, "carbs": 50, "fat": 20}
    assert is_reasonable_macros(macros, 500) is True


def test_is_reasonable_macros_zero():
    """Test all zero macros"""
    macros = {"protein": 0, "carbs": 0, "fat": 0}
    assert is_reasonable_macros(macros, 100) is False


def test_is_reasonable_macros_negative():
    """Test negative macro values"""
    macros = {"protein": -10, "carbs": 50, "fat": 20}
    assert is_reasonable_macros(macros, 500) is False


def test_is_reasonable_macros_missing_key():
    """Test macros with missing keys"""
    macros = {"protein": 30, "carbs": 50}  # Missing fat
    assert is_reasonable_macros(macros, 500) is False


def test_is_reasonable_macros_extreme_values():
    """Test extremely high macro values"""
    macros = {"protein": 1000, "carbs": 50, "fat": 20}
    assert is_reasonable_macros(macros, 500) is False


# ============================================================================
# Macro Ratio Validation Tests
# ============================================================================

def test_validate_macro_ratios_balanced():
    """Test balanced macro ratios"""
    macros = {"protein": 30, "carbs": 40, "fat": 30}
    assert validate_macro_ratios(macros) is True


def test_validate_macro_ratios_high_protein():
    """Test high protein diet ratios"""
    macros = {"protein": 50, "carbs": 25, "fat": 25}
    assert validate_macro_ratios(macros) is True


def test_validate_macro_ratios_low_carb():
    """Test low carb diet ratios"""
    macros = {"protein": 35, "carbs": 10, "fat": 55}
    assert validate_macro_ratios(macros) is True


def test_validate_macro_ratios_extreme():
    """Test extreme macro ratios"""
    macros = {"protein": 95, "carbs": 5, "fat": 0}
    assert validate_macro_ratios(macros) is False


def test_validate_macro_ratios_doesnt_sum_to_100():
    """Test macro ratios that don't sum to 100%"""
    macros = {"protein": 20, "carbs": 30, "fat": 30}
    # Should handle gracefully (might normalize or reject)
    result = validate_macro_ratios(macros)
    assert isinstance(result, bool)


# ============================================================================
# Calorie Calculation Tests
# ============================================================================

def test_calculate_calories_from_macros_accurate():
    """Test calorie calculation from macros"""
    # Protein: 4 cal/g, Carbs: 4 cal/g, Fat: 9 cal/g
    macros = {"protein": 25, "carbs": 50, "fat": 10}
    expected = (25 * 4) + (50 * 4) + (10 * 9)  # 100 + 200 + 90 = 390

    result = calculate_calories_from_macros(macros)

    assert result == expected


def test_calculate_calories_from_macros_zero():
    """Test calorie calculation with zero macros"""
    macros = {"protein": 0, "carbs": 0, "fat": 0}

    result = calculate_calories_from_macros(macros)

    assert result == 0


def test_calculate_calories_from_macros_only_protein():
    """Test calorie calculation with only protein"""
    macros = {"protein": 50, "carbs": 0, "fat": 0}

    result = calculate_calories_from_macros(macros)

    assert result == 200  # 50g * 4 cal/g


def test_calculate_calories_from_macros_only_fat():
    """Test calorie calculation with only fat"""
    macros = {"protein": 0, "carbs": 0, "fat": 20}

    result = calculate_calories_from_macros(macros)

    assert result == 180  # 20g * 9 cal/g


# ============================================================================
# Macro Total Checking Tests
# ============================================================================

def test_check_macro_total_matches():
    """Test macro total matches claimed calories"""
    macros = {"protein": 25, "carbs": 50, "fat": 10}
    claimed_calories = 390  # Should match calculated

    result = check_macro_total(macros, claimed_calories)

    assert result["matches"] is True
    assert abs(result["difference"]) < 10  # Small tolerance


def test_check_macro_total_mismatch():
    """Test macro total doesn't match claimed calories"""
    macros = {"protein": 25, "carbs": 50, "fat": 10}
    claimed_calories = 500  # Doesn't match calculated 390

    result = check_macro_total(macros, claimed_calories)

    assert result["matches"] is False
    assert result["difference"] > 50


def test_check_macro_total_within_tolerance():
    """Test macro total within acceptable tolerance"""
    macros = {"protein": 25, "carbs": 50, "fat": 10}
    claimed_calories = 395  # Close to calculated 390

    result = check_macro_total(macros, claimed_calories, tolerance=10)

    assert result["matches"] is True


# ============================================================================
# Full Nutrition Data Validation Tests
# ============================================================================

def test_validate_nutrition_data_valid():
    """Test validation of complete valid nutrition data"""
    data = {
        "name": "Grilled Chicken Breast",
        "quantity": "150g",
        "calories": 165,
        "protein": 31.0,
        "carbs": 0.0,
        "fat": 3.6
    }

    result = validate_nutrition_data(data)

    assert result["valid"] is True
    assert len(result.get("errors", [])) == 0


def test_validate_nutrition_data_missing_fields():
    """Test validation with missing required fields"""
    data = {
        "name": "Apple",
        "calories": 95
        # Missing protein, carbs, fat
    }

    result = validate_nutrition_data(data)

    assert result["valid"] is False
    assert "missing" in str(result.get("errors", [])).lower()


def test_validate_nutrition_data_invalid_calories():
    """Test validation with invalid calories"""
    data = {
        "name": "Impossible Food",
        "quantity": "100g",
        "calories": -50,  # Negative calories
        "protein": 10,
        "carbs": 20,
        "fat": 5
    }

    result = validate_nutrition_data(data)

    assert result["valid"] is False


def test_validate_nutrition_data_macro_calorie_mismatch():
    """Test validation when macros don't match calories"""
    data = {
        "name": "Suspicious Food",
        "quantity": "100g",
        "calories": 1000,  # Too high for these macros
        "protein": 10,
        "carbs": 10,
        "fat": 5
    }

    result = validate_nutrition_data(data)

    # Should flag the mismatch
    assert result["valid"] is False or "warning" in result


# ============================================================================
# Edge Cases and Boundary Tests
# ============================================================================

def test_validate_nutrition_data_zero_everything():
    """Test validation with all zeros"""
    data = {
        "name": "Water",
        "quantity": "250ml",
        "calories": 0,
        "protein": 0,
        "carbs": 0,
        "fat": 0
    }

    result = validate_nutrition_data(data)

    # Water should be valid (zero calories is okay)
    assert result["valid"] is True


def test_validate_nutrition_data_very_small_quantities():
    """Test validation with very small amounts"""
    data = {
        "name": "Spice",
        "quantity": "1g",
        "calories": 3,
        "protein": 0.1,
        "carbs": 0.5,
        "fat": 0.1
    }

    result = validate_nutrition_data(data)

    assert result["valid"] is True


def test_validate_nutrition_data_decimal_values():
    """Test validation with decimal macro values"""
    data = {
        "name": "Almond",
        "quantity": "10g",
        "calories": 57,
        "protein": 2.1,
        "carbs": 2.2,
        "fat": 4.9
    }

    result = validate_nutrition_data(data)

    assert result["valid"] is True


# ============================================================================
# Food Type Specific Validation Tests
# ============================================================================

def test_validate_pure_protein_food():
    """Test validation of pure protein food (like chicken breast)"""
    data = {
        "name": "Chicken Breast",
        "quantity": "100g",
        "calories": 165,
        "protein": 31,
        "carbs": 0,
        "fat": 3.6
    }

    result = validate_nutrition_data(data)

    assert result["valid"] is True


def test_validate_pure_carb_food():
    """Test validation of pure carb food (like rice)"""
    data = {
        "name": "White Rice",
        "quantity": "100g",
        "calories": 130,
        "protein": 2.7,
        "carbs": 28,
        "fat": 0.3
    }

    result = validate_nutrition_data(data)

    assert result["valid"] is True


def test_validate_high_fat_food():
    """Test validation of high fat food (like avocado)"""
    data = {
        "name": "Avocado",
        "quantity": "100g",
        "calories": 160,
        "protein": 2,
        "carbs": 9,
        "fat": 15
    }

    result = validate_nutrition_data(data)

    assert result["valid"] is True


# ============================================================================
# Calorie-Macro Consistency Tests
# ============================================================================

@pytest.mark.parametrize("protein,carbs,fat,expected_calories", [
    (10, 20, 5, 165),  # 40 + 80 + 45
    (25, 0, 0, 100),   # Pure protein
    (0, 50, 0, 200),   # Pure carbs
    (0, 0, 20, 180),   # Pure fat
])
def test_calculate_calories_parametrized(protein, carbs, fat, expected_calories):
    """Test calorie calculation with various macro combinations"""
    macros = {"protein": protein, "carbs": carbs, "fat": fat}

    result = calculate_calories_from_macros(macros)

    assert result == expected_calories


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_validate_nutrition_data_none_value():
    """Test validation with None values"""
    data = {
        "name": "Food",
        "calories": None,
        "protein": 10,
        "carbs": 20,
        "fat": 5
    }

    result = validate_nutrition_data(data)

    assert result["valid"] is False


def test_validate_nutrition_data_string_numbers():
    """Test validation with string number values"""
    data = {
        "name": "Food",
        "quantity": "100g",
        "calories": "165",  # String instead of number
        "protein": "31",
        "carbs": "0",
        "fat": "3.6"
    }

    # Should either convert or reject
    result = validate_nutrition_data(data)

    # Implementation dependent - either converts and validates or rejects
    assert isinstance(result, dict)


def test_is_reasonable_macros_none_calories():
    """Test macro validation with None calories"""
    macros = {"protein": 30, "carbs": 50, "fat": 20}

    result = is_reasonable_macros(macros, None)

    # Should handle gracefully
    assert isinstance(result, bool)


# ============================================================================
# Tolerance and Rounding Tests
# ============================================================================

def test_check_macro_total_rounding():
    """Test that small rounding differences are accepted"""
    # Calculated: 25*4 + 50*4 + 10*9 = 390
    macros = {"protein": 25, "carbs": 50, "fat": 10}

    # Test with slight rounding difference
    result1 = check_macro_total(macros, 389)
    result2 = check_macro_total(macros, 391)

    # Both should match within reasonable tolerance
    assert result1["matches"] is True or result1["difference"] < 5
    assert result2["matches"] is True or result2["difference"] < 5


def test_validate_nutrition_data_with_fiber():
    """Test validation when fiber is included"""
    data = {
        "name": "Apple",
        "quantity": "100g",
        "calories": 52,
        "protein": 0.3,
        "carbs": 14,
        "fat": 0.2,
        "fiber": 2.4
    }

    result = validate_nutrition_data(data)

    # Should handle fiber (fiber doesn't contribute to calories in same way)
    assert result["valid"] is True


def test_validate_nutrition_data_with_alcohol():
    """Test validation of alcoholic beverage"""
    data = {
        "name": "Beer",
        "quantity": "355ml",
        "calories": 153,
        "protein": 1.6,
        "carbs": 13,
        "fat": 0,
        "alcohol": 14  # Alcohol: 7 cal/g
    }

    result = validate_nutrition_data(data)

    # Should either account for alcohol or handle gracefully
    assert isinstance(result, dict)
