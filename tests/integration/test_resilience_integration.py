"""Integration tests for resilience patterns"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import pybreaker
import httpx
from src.utils.vision import analyze_food_photo
from src.utils.nutrition_search import verify_food_items
from src.models.food import FoodItem, FoodMacros
from src.resilience.circuit_breaker import OPENAI_BREAKER, ANTHROPIC_BREAKER, USDA_BREAKER
from src.db.nutrition_cache import get_from_cache, add_to_cache, init_nutrition_cache


@pytest.fixture(autouse=True)
def reset_circuit_breakers():
    """Reset all circuit breakers before each test"""
    for breaker in [OPENAI_BREAKER, ANTHROPIC_BREAKER, USDA_BREAKER]:
        breaker._state = pybreaker.STATE_CLOSED
        breaker._failure_count = 0
    yield


@pytest.fixture
def mock_food_item():
    """Create a mock food item for testing"""
    return FoodItem(
        name="Chicken breast",
        quantity="100g",
        calories=165,
        macros=FoodMacros(protein=31.0, carbs=0.0, fat=3.6)
    )


@pytest.fixture
def mock_vision_result():
    """Create a mock vision analysis result"""
    from src.models.food import VisionAnalysisResult
    return VisionAnalysisResult(
        foods=[FoodItem(
            name="Apple",
            quantity="1 medium",
            calories=95,
            macros=FoodMacros(protein=0.5, carbs=25.0, fat=0.3)
        )],
        confidence="high",
        clarifying_questions=[]
    )


@pytest.mark.asyncio
async def test_vision_fallback_to_alternative_model(mock_vision_result, tmp_path):
    """Test vision AI falls back to alternative model when primary fails"""

    # Create a temporary test image
    test_image = tmp_path / "test.jpg"
    test_image.write_bytes(b"fake image data")

    with patch('src.utils.vision.analyze_with_openai', side_effect=Exception("OpenAI down")):
        with patch('src.utils.vision.analyze_with_anthropic', return_value=mock_vision_result):
            result = await analyze_food_photo(str(test_image), caption="apple")

            assert result.foods[0].name == "Apple"
            assert result.confidence == "high"


@pytest.mark.asyncio
async def test_vision_fallback_to_mock(tmp_path):
    """Test vision AI falls back to mock when both APIs fail"""

    # Create a temporary test image
    test_image = tmp_path / "test.jpg"
    test_image.write_bytes(b"fake image data")

    with patch('src.utils.vision.analyze_with_openai', side_effect=Exception("OpenAI down")):
        with patch('src.utils.vision.analyze_with_anthropic', side_effect=Exception("Anthropic down")):
            result = await analyze_food_photo(str(test_image), caption="food")

            # Should return mock result
            assert result.confidence == "low"
            assert len(result.foods) > 0


@pytest.mark.asyncio
async def test_usda_fallback_to_local_cache(mock_food_item):
    """Test USDA falls back to local cache when API fails"""

    # Initialize the cache
    init_nutrition_cache()

    # Add test data to cache
    await add_to_cache("chicken breast", {
        "description": "Test chicken",
        "calories_per_100g": 165,
        "protein_per_100g": 31.0,
        "carbs_per_100g": 0.0,
        "fat_per_100g": 3.6,
        "fiber_per_100g": 0.0,
        "sodium_per_100g": 74,
        "source": "test"
    })

    with patch('src.utils.nutrition_search.search_usda', side_effect=Exception("USDA down")):
        result = await verify_food_items([mock_food_item])

        assert len(result) == 1
        assert result[0].verification_source == "local_cache"
        assert result[0].confidence_score == 0.8


@pytest.mark.asyncio
async def test_usda_circuit_breaker_opens_on_repeated_failures(mock_food_item):
    """Test that USDA circuit breaker opens after repeated failures"""

    # Mock USDA to always fail
    with patch('httpx.AsyncClient.get', side_effect=httpx.TimeoutException("Timeout")):
        # Trigger 5 failures to open circuit
        for _ in range(5):
            try:
                await verify_food_items([mock_food_item])
            except Exception:
                pass  # Expected to fail

        # Circuit should now be OPEN
        assert USDA_BREAKER.current_state == pybreaker.STATE_OPEN


@pytest.mark.asyncio
async def test_vision_circuit_breaker_opens_on_repeated_failures(tmp_path):
    """Test that vision circuit breaker opens after repeated failures"""

    # Create a temporary test image
    test_image = tmp_path / "test.jpg"
    test_image.write_bytes(b"fake image data")

    # Mock OpenAI to always fail (and Anthropic too, to prevent fallback)
    with patch('src.utils.vision.analyze_with_openai', side_effect=httpx.TimeoutException("Timeout")):
        with patch('src.utils.vision.analyze_with_anthropic', side_effect=httpx.TimeoutException("Timeout")):
            # Trigger 5 failures to open circuit
            for _ in range(5):
                try:
                    await analyze_food_photo(str(test_image))
                except Exception:
                    pass  # Expected to fail

            # OpenAI circuit should now be OPEN
            assert OPENAI_BREAKER.current_state == pybreaker.STATE_OPEN


@pytest.mark.asyncio
async def test_local_cache_preloaded_foods():
    """Test that local cache contains preloaded common foods"""

    # Initialize the cache
    init_nutrition_cache()

    # Check for common foods
    common_foods = ["chicken breast", "egg", "rice", "banana", "apple"]

    for food in common_foods:
        cached_data = await get_from_cache(food)
        assert cached_data is not None, f"{food} should be in cache"
        assert cached_data["calories_per_100g"] > 0
        assert cached_data["protein_per_100g"] >= 0


@pytest.mark.asyncio
async def test_resilience_end_to_end_vision(tmp_path, mock_vision_result):
    """End-to-end test of vision resilience: retry, fallback, circuit breaker"""

    # Create a temporary test image
    test_image = tmp_path / "test.jpg"
    test_image.write_bytes(b"fake image data")

    # Simulate flaky primary API (fails twice, then succeeds)
    call_count = 0

    async def flaky_openai(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.TimeoutException("Temporary failure")
        return mock_vision_result

    with patch('src.utils.vision.analyze_with_openai', side_effect=flaky_openai):
        result = await analyze_food_photo(str(test_image), caption="apple")

        # Should succeed after retries
        assert result.foods[0].name == "Apple"
        # Should have been called 3 times (initial + 2 retries)
        assert call_count == 3


@pytest.mark.asyncio
async def test_resilience_end_to_end_usda(mock_food_item):
    """End-to-end test of USDA resilience: retry, fallback, circuit breaker"""

    # Simulate flaky USDA API (fails twice, then succeeds)
    call_count = 0

    def flaky_usda_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.TimeoutException("Temporary failure")

        # Return mock USDA response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "foods": [{
                "description": "Chicken, broilers or fryers, breast, meat only, cooked, roasted",
                "score": 95,
                "foodNutrients": [
                    {"nutrientName": "Energy", "value": 165},
                    {"nutrientName": "Protein", "value": 31.0},
                    {"nutrientName": "Carbohydrate, by difference", "value": 0.0},
                    {"nutrientName": "Total lipid (fat)", "value": 3.6},
                ]
            }],
            "totalHits": 1
        }
        return mock_response

    with patch('httpx.AsyncClient.get', side_effect=flaky_usda_get):
        result = await verify_food_items([mock_food_item])

        # Should succeed after retries
        assert len(result) == 1
        # Should have been called 3 times (initial + 2 retries)
        assert call_count == 3


@pytest.mark.asyncio
async def test_metrics_recorded_on_success(mock_food_item):
    """Test that metrics are recorded on successful API calls"""

    from src.resilience.metrics import api_calls_total

    # Get initial count
    initial_count = api_calls_total.labels(api="usda", status="success")._value.get() or 0

    # Mock successful USDA response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "foods": [{
            "description": "Test food",
            "score": 95,
            "foodNutrients": [
                {"nutrientName": "Energy", "value": 100},
                {"nutrientName": "Protein", "value": 10.0},
                {"nutrientName": "Carbohydrate, by difference", "value": 15.0},
                {"nutrientName": "Total lipid (fat)", "value": 5.0},
            ]
        }],
        "totalHits": 1
    }

    with patch('httpx.AsyncClient.get', return_value=mock_response):
        await verify_food_items([mock_food_item])

        # Check that success metric was incremented
        final_count = api_calls_total.labels(api="usda", status="success")._value.get()
        assert final_count > initial_count


@pytest.mark.asyncio
async def test_metrics_recorded_on_failure(mock_food_item):
    """Test that metrics are recorded on failed API calls"""

    from src.resilience.metrics import api_calls_total

    # Get initial count
    initial_count = api_calls_total.labels(api="usda", status="failure")._value.get() or 0

    with patch('httpx.AsyncClient.get', side_effect=httpx.TimeoutException("Timeout")):
        try:
            await verify_food_items([mock_food_item])
        except Exception:
            pass  # Expected to fail

        # Check that failure metric was incremented
        # Note: May be incremented multiple times due to retries
        final_count = api_calls_total.labels(api="usda", status="failure")._value.get()
        assert final_count > initial_count
