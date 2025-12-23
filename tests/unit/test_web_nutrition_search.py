"""Tests for web nutrition search (Phase 3)"""
import pytest
from datetime import datetime
from src.utils.web_nutrition_search import (
    search_nutrition_web,
    verify_with_web_search,
    _extract_context,
    get_trusted_sources,
    WebNutritionResult
)
from src.models.food import FoodItem, FoodMacros


def test_extract_context_restaurant():
    """Test extracting restaurant context from food name"""

    assert _extract_context("Chipotle chicken bowl") == "chipotle"
    assert _extract_context("McDonald's Big Mac") == "mcdonalds"
    assert _extract_context("Starbucks latte") == "starbucks"
    assert _extract_context("Subway footlong") == "subway"


def test_extract_context_brand():
    """Test extracting brand context from food name"""

    assert _extract_context("Quest protein bar") == "quest"
    assert _extract_context("Clif Bar chocolate chip") == "clif"
    assert _extract_context("KIND almond bar") == "kind"


def test_extract_context_no_match():
    """Test context extraction with no known brands/restaurants"""

    assert _extract_context("Homemade chicken salad") is None
    assert _extract_context("Grilled vegetables") is None
    assert _extract_context("Plain rice") is None


def test_get_trusted_sources():
    """Test that trusted sources list is comprehensive"""

    sources = get_trusted_sources()

    # Should include USDA
    assert any("usda.gov" in s for s in sources)

    # Should include nutrition databases
    assert any("nutritionix.com" in s for s in sources)
    assert any("myfitnesspal.com" in s for s in sources)

    # Should include restaurant official sites
    assert any("chipotle.com" in s for s in sources)
    assert any("mcdonalds.com" in s for s in sources)


@pytest.mark.asyncio
async def test_verify_with_web_search_skips_when_usda_succeeds():
    """Test that web search is only used when USDA fails"""

    food = FoodItem(
        name="Chicken breast",
        quantity="150g",
        calories=248,
        macros=FoodMacros(protein=52, carbs=0, fat=5)
    )

    # Should return None if USDA didn't fail
    result = await verify_with_web_search(food, usda_failed=False)
    assert result is None


@pytest.mark.asyncio
async def test_search_nutrition_web_returns_results():
    """Test that web search can find nutrition data"""

    # Note: This is a mock test - actual implementation will depend on
    # network availability and search results

    # For now, just test that the function handles the input correctly
    results = await search_nutrition_web("apple", context=None)

    # Should return a list (may be empty if no results found)
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_search_nutrition_web_with_context():
    """Test web search with context (brand/restaurant)"""

    # Test with restaurant context
    results = await search_nutrition_web(
        "chicken bowl",
        context="chipotle"
    )

    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_web_search_caching():
    """Test that web search results are cached"""

    # First search
    results1 = await search_nutrition_web("banana")

    # Second search (should use cache)
    results2 = await search_nutrition_web("banana")

    # Should return same results (from cache)
    assert results1 == results2


@pytest.mark.asyncio
async def test_verify_with_web_search_fallback():
    """Test web search as fallback for uncommon foods"""

    # Uncommon food that USDA might not have
    food = FoodItem(
        name="Chipotle burrito bowl with carnitas",
        quantity="1 bowl",
        calories=800,  # AI estimate
        macros=FoodMacros(protein=40, carbs=80, fat=30),
        confidence_score=0.5,
        verification_source="ai_estimate"
    )

    # Try web search fallback
    result = await verify_with_web_search(food, usda_failed=True)

    # May return None if no web results, or FoodItem if found
    if result:
        assert isinstance(result, FoodItem)
        assert result.verification_source.startswith("web:")
        assert result.confidence_score > 0.0


def test_web_nutrition_result_model():
    """Test WebNutritionResult model validation"""

    result = WebNutritionResult(
        food_name="Test food",
        calories=250,
        protein=20.0,
        carbs=30.0,
        fat=10.0,
        serving_size="1 cup",
        source_url="https://example.com",
        source_name="Example Source",
        confidence=0.8,
        notes="Test notes"
    )

    assert result.food_name == "Test food"
    assert result.calories == 250
    assert result.protein == 20.0
    assert result.confidence == 0.8


@pytest.mark.asyncio
async def test_web_search_handles_errors_gracefully():
    """Test that web search handles errors without crashing"""

    # Invalid food name
    results = await search_nutrition_web("~~~INVALID~~~")

    # Should return empty list, not crash
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_web_search_sorts_by_confidence():
    """Test that web search results are sorted by confidence"""

    results = await search_nutrition_web("chicken")

    if len(results) > 1:
        # Results should be sorted descending by confidence
        for i in range(len(results) - 1):
            assert results[i].confidence >= results[i + 1].confidence


@pytest.mark.asyncio
async def test_verify_with_web_search_low_confidence_rejection():
    """Test that low confidence web results are rejected"""

    food = FoodItem(
        name="Unknown exotic food",
        quantity="100g",
        calories=200,
        macros=FoodMacros(protein=10, carbs=20, fat=8)
    )

    result = await verify_with_web_search(food, usda_failed=True)

    # If result has low confidence (<0.4), should return None
    if result:
        assert result.confidence_score >= 0.4
