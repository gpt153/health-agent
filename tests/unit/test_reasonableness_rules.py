"""Tests for nutrition reasonableness rules"""
import pytest
from src.utils.reasonableness_rules import (
    categorize_food,
    parse_quantity_to_grams,
    check_reasonableness,
    validate_food_items,
)
from src.models.food import FoodItem, FoodMacros


def test_categorize_salad():
    """Test salad categorization"""
    assert categorize_food("Caesar Salad") == "salad"
    assert categorize_food("Mixed greens") == "leafy_greens"
    assert categorize_food("Spinach salad") == "salad"  # Salad takes priority over leafy_greens


def test_categorize_protein():
    """Test protein categorization"""
    assert categorize_food("Chicken Breast") == "chicken_breast"
    assert categorize_food("Grilled chicken") == "chicken"
    assert categorize_food("Beef steak") == "beef"
    assert categorize_food("Salmon fillet") == "fish"


def test_categorize_dairy():
    """Test dairy categorization"""
    assert categorize_food("Cottage Cheese") == "cottage_cheese"
    assert categorize_food("Keso") == "cottage_cheese"  # Swedish
    assert categorize_food("Quark") == "quark"
    assert categorize_food("Kvarg") == "quark"  # Swedish


def test_parse_quantity_grams():
    """Test parsing gram quantities"""
    assert parse_quantity_to_grams("100g") == 100.0
    assert parse_quantity_to_grams("250 grams") == 250.0
    assert parse_quantity_to_grams("0.5kg") == 500.0


def test_parse_quantity_items():
    """Test parsing item quantities"""
    assert parse_quantity_to_grams("2 eggs") == 100.0  # 2 * 50g
    assert parse_quantity_to_grams("1 chicken breast") == 150.0
    assert parse_quantity_to_grams("1 apple") == 180.0


def test_check_reasonableness_salad_too_high():
    """Test detection of unreasonably high calorie salad"""
    # 450 cal for a "small salad" - unreasonable!
    salad = FoodItem(
        name="Small Salad",
        quantity="200g",  # Small salad
        calories=450,  # Way too high!
        macros=FoodMacros(protein=5.0, carbs=10.0, fat=40.0)
    )

    is_reasonable, warnings = check_reasonableness(salad)

    assert not is_reasonable
    assert len(warnings) > 0
    assert "HIGH" in warnings[0]


def test_check_reasonableness_chicken_too_high():
    """Test detection of unreasonably high calorie chicken"""
    # 650 cal for chicken breast - unreasonable!
    chicken = FoodItem(
        name="Chicken Breast",
        quantity="100g",
        calories=650,  # Way too high for 100g!
        macros=FoodMacros(protein=25.0, carbs=0.0, fat=60.0)
    )

    is_reasonable, warnings = check_reasonableness(chicken)

    assert not is_reasonable
    assert len(warnings) > 0
    assert "HIGH" in warnings[0]


def test_check_reasonableness_good_estimates():
    """Test that reasonable estimates pass"""
    # Realistic chicken breast: ~165 cal per 100g
    chicken = FoodItem(
        name="Chicken Breast",
        quantity="100g",
        calories=165,
        macros=FoodMacros(protein=31.0, carbs=0.0, fat=3.6)
    )

    is_reasonable, warnings = check_reasonableness(chicken)

    assert is_reasonable
    assert len(warnings) == 0


def test_check_reasonableness_salad_good():
    """Test that reasonable salad passes"""
    # Realistic salad: ~50 cal for 200g
    salad = FoodItem(
        name="Mixed Salad",
        quantity="200g",
        calories=50,
        macros=FoodMacros(protein=2.0, carbs=8.0, fat=0.5)
    )

    is_reasonable, warnings = check_reasonableness(salad)

    assert is_reasonable
    assert len(warnings) == 0


def test_macro_calorie_mismatch():
    """Test detection of macro/calorie mismatch"""
    # Macros don't match total calories
    food = FoodItem(
        name="Mystery Food",
        quantity="100g",
        calories=500,  # Claims 500 cal
        macros=FoodMacros(
            protein=10.0,  # 40 cal
            carbs=10.0,    # 40 cal
            fat=10.0       # 90 cal
        )  # Total from macros: only 170 cal, but claims 500!
    )

    is_reasonable, warnings = check_reasonableness(food)

    assert not is_reasonable
    assert any("don't match" in w for w in warnings)


def test_validate_food_items_list():
    """Test validation of multiple items"""
    foods = [
        FoodItem(
            name="Salad",
            quantity="200g",
            calories=450,  # Too high!
            macros=FoodMacros(protein=5.0, carbs=10.0, fat=40.0)
        ),
        FoodItem(
            name="Chicken Breast",
            quantity="100g",
            calories=165,  # Good
            macros=FoodMacros(protein=31.0, carbs=0.0, fat=3.6)
        ),
    ]

    validated_foods, all_warnings = validate_food_items(foods)

    assert len(validated_foods) == 2  # Both items returned
    assert len(all_warnings) > 0  # Warnings for the salad
    assert any("Salad" in w for w in all_warnings)


def test_unknown_category():
    """Test that unknown categories don't fail"""
    unknown = FoodItem(
        name="Rare Exotic Fruit",
        quantity="100g",
        calories=1000,  # Could be anything
        macros=FoodMacros(protein=1.0, carbs=200.0, fat=5.0)
    )

    is_reasonable, warnings = check_reasonableness(unknown)

    # Should pass - we don't know what's reasonable for unknown foods
    assert is_reasonable
    assert len(warnings) == 0


def test_parse_quantity_edge_cases():
    """Test edge cases in quantity parsing"""
    assert parse_quantity_to_grams("1 cup") == 150.0  # Rough average
    assert parse_quantity_to_grams("invalid") == None  # Can't parse
    assert parse_quantity_to_grams("") == None  # Empty string
