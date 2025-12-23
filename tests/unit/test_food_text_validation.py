"""Tests for text-based food logging with validation"""
import pytest
from datetime import datetime
from src.utils.food_text_parser import parse_food_description
from src.models.food import FoodItem, FoodMacros


@pytest.mark.asyncio
async def test_parse_simple_food_description():
    """Test parsing a simple food description"""
    result = await parse_food_description(
        description="150g chicken breast",
        quantity="150g"
    )

    assert result is not None
    assert len(result.foods) >= 1
    assert any("chicken" in f.name.lower() for f in result.foods)

    # Find chicken item
    chicken = next((f for f in result.foods if "chicken" in f.name.lower()), None)
    assert chicken is not None

    # Should be reasonable calories for 150g chicken breast (approx 250-280 cal)
    assert 200 <= chicken.calories <= 350
    assert chicken.macros.protein > 40  # High protein
    assert chicken.verification_source == "ai_text_parse"


@pytest.mark.asyncio
async def test_parse_conservative_salad():
    """Test that small salad estimates are conservative (not 450 cal!)"""
    result = await parse_food_description(
        description="small salad",
        quantity=None
    )

    assert result is not None
    assert len(result.foods) >= 1

    salad = result.foods[0]

    # CRITICAL: Small salad should be 50-200 cal, NOT 450!
    assert salad.calories < 250, f"Salad calories too high: {salad.calories} (should be <250)"
    assert 30 <= salad.calories <= 250  # Reasonable range


@pytest.mark.asyncio
async def test_parse_combined_meal():
    """Test parsing a meal with multiple items"""
    result = await parse_food_description(
        description="170g chicken breast and a small salad"
    )

    assert result is not None
    assert len(result.foods) >= 2  # Should break down into 2+ items

    # Should identify chicken and salad separately
    food_names = " ".join([f.name.lower() for f in result.foods])
    assert "chicken" in food_names
    assert "salad" in food_names

    total_cal = sum(f.calories for f in result.foods)
    # 170g chicken (~280 cal) + small salad (~50-100 cal) = 330-380 cal
    assert 250 <= total_cal <= 500


@pytest.mark.asyncio
async def test_parse_with_clarifying_questions():
    """Test that ambiguous descriptions generate clarifying questions"""
    result = await parse_food_description(
        description="Chipotle bowl"
    )

    assert result is not None
    # Might ask for details about protein, toppings, etc.
    # Or might break down into estimated components
    assert result.confidence in ["low", "medium", "high"]

    # If confidence is low, should have clarifying questions
    if result.confidence == "low":
        assert len(result.clarifying_questions) > 0


@pytest.mark.asyncio
async def test_fallback_on_parse_error():
    """Test that parser has safe fallback on errors"""
    # Invalid/corrupted input
    result = await parse_food_description(
        description="~~~INVALID~~~",
        quantity=None
    )

    # Should return fallback, not crash
    assert result is not None
    assert len(result.foods) >= 1
    assert result.confidence == "low"
    assert len(result.clarifying_questions) > 0


@pytest.mark.asyncio
async def test_parse_quantity_override():
    """Test that quantity parameter is used"""
    result = await parse_food_description(
        description="grilled chicken",
        quantity="200g"
    )

    assert result is not None
    assert len(result.foods) >= 1

    chicken = result.foods[0]
    # Should reference 200g
    assert "200" in chicken.quantity or "200g" in chicken.quantity.lower()


@pytest.mark.asyncio
async def test_conservative_estimates_avoid_overestimation():
    """Test that estimates are conservative, not inflated"""

    # Test case from issue: "small salad" should NOT be 450 cal
    salad_result = await parse_food_description("small salad")
    salad = salad_result.foods[0]
    assert salad.calories < 200, f"Small salad over-estimated: {salad.calories} cal"

    # Test case from issue: "chicken breast" without size should be reasonable
    # Default to medium chicken breast (150-200g), not 300g
    chicken_result = await parse_food_description("chicken breast")
    chicken = chicken_result.foods[0]
    assert chicken.calories < 400, f"Chicken breast over-estimated: {chicken.calories} cal"
    # Reasonable range for medium chicken breast (150-180g)
    assert 200 <= chicken.calories <= 350
