"""Unit tests for USDA nutrition search and verification"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from src.utils.nutrition_search import (
    normalize_food_name,
    parse_quantity,
    search_usda,
    scale_nutrients,
    verify_food_items,
    _cache,
    CACHE_DURATION
)
from src.models.food import FoodItem, FoodMacros, Micronutrients


class TestNormalizeFoodName:
    """Test food name normalization"""

    def test_lowercase_conversion(self):
        assert normalize_food_name("CHICKEN BREAST") == "chicken breast"

    def test_remove_qualifiers(self):
        assert normalize_food_name("Organic Fresh Chicken") == "chicken"
        assert normalize_food_name("Grilled Large Salmon") == "salmon"
        assert normalize_food_name("Baked Medium Potato") == "potato"

    def test_whitespace_cleanup(self):
        assert normalize_food_name("  chicken   breast  ") == "chicken breast"

    def test_complex_name(self):
        result = normalize_food_name("Organic Fresh Grilled Large Chicken Breast")
        assert result == "chicken breast"


class TestParseQuantity:
    """Test quantity parsing"""

    def test_grams(self):
        assert parse_quantity("100g") == (100.0, 'g')
        assert parse_quantity("100 grams") == (100.0, 'g')
        assert parse_quantity("170g") == (170.0, 'g')

    def test_ounces(self):
        assert parse_quantity("4oz") == (4.0, 'oz')

    def test_pounds(self):
        assert parse_quantity("1lb") == (1.0, 'lb')

    def test_cups(self):
        assert parse_quantity("1 cup") == (1.0, 'cup')
        assert parse_quantity("2 cups") == (2.0, 'cup')

    def test_items(self):
        assert parse_quantity("2 eggs") == (2.0, 'item')
        assert parse_quantity("1 apple") == (1.0, 'item')

    def test_tablespoons(self):
        assert parse_quantity("2 tbsp") == (2.0, 'tbsp')

    def test_teaspoons(self):
        assert parse_quantity("1 tsp") == (1.0, 'tsp')

    def test_decimal_amounts(self):
        assert parse_quantity("1.5 cups") == (1.5, 'cup')
        assert parse_quantity("0.5kg") == (0.5, 'kg')

    def test_default_fallback(self):
        amount, unit = parse_quantity("some random string")
        assert amount == 100.0
        assert unit == 'g'


@pytest.mark.asyncio
class TestSearchUSDA:
    """Test USDA API search functionality"""

    async def test_verification_disabled(self):
        """Should return None when verification is disabled"""
        with patch('src.utils.nutrition_search.ENABLE_NUTRITION_VERIFICATION', False):
            result = await search_usda("chicken")
            assert result is None

    async def test_cache_hit(self):
        """Should return cached data if available and not expired"""
        # Setup cache
        cache_key = "chicken:3"
        cached_data = {"foods": [{"description": "Chicken, broilers or fryers"}]}
        cached_time = datetime.now()
        _cache[cache_key] = (cached_data, cached_time)

        try:
            with patch('src.utils.nutrition_search.ENABLE_NUTRITION_VERIFICATION', True):
                result = await search_usda("chicken")
                assert result == cached_data
        finally:
            # Cleanup
            _cache.clear()

    async def test_cache_expired(self):
        """Should make new API call if cache is expired"""
        # Setup expired cache
        cache_key = "chicken:3"
        cached_data = {"foods": []}
        expired_time = datetime.now() - CACHE_DURATION - timedelta(hours=1)
        _cache[cache_key] = (cached_data, expired_time)

        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"foods": [{"description": "Fresh chicken"}], "totalHits": 1})
        mock_response.raise_for_status = MagicMock()

        try:
            with patch('src.utils.nutrition_search.ENABLE_NUTRITION_VERIFICATION', True):
                with patch('httpx.AsyncClient') as mock_client:
                    mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
                    result = await search_usda("chicken")
                    assert result["totalHits"] == 1
                    assert "chicken" in cache_key
        finally:
            # Cleanup
            _cache.clear()

    async def test_api_timeout(self):
        """Should return None on API timeout"""
        import httpx

        with patch('src.utils.nutrition_search.ENABLE_NUTRITION_VERIFICATION', True):
            with patch('httpx.AsyncClient') as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    side_effect=httpx.TimeoutException("Timeout")
                )
                result = await search_usda("chicken")
                assert result is None

    async def test_api_http_error(self):
        """Should return None on HTTP error"""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"

        with patch('src.utils.nutrition_search.ENABLE_NUTRITION_VERIFICATION', True):
            with patch('httpx.AsyncClient') as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    side_effect=httpx.HTTPStatusError("Error", request=MagicMock(), response=mock_response)
                )
                result = await search_usda("chicken")
                assert result is None

    async def test_successful_api_call(self):
        """Should return and cache API response on success"""
        mock_data = {
            "foods": [
                {
                    "fdcId": 123456,
                    "description": "Chicken, broilers or fryers, breast, meat only, cooked, roasted",
                    "score": 750.0
                }
            ],
            "totalHits": 100
        }

        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=mock_data)
        mock_response.raise_for_status = MagicMock()

        try:
            with patch('src.utils.nutrition_search.ENABLE_NUTRITION_VERIFICATION', True):
                with patch('httpx.AsyncClient') as mock_client:
                    mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
                    result = await search_usda("chicken breast")
                    assert result == mock_data
                    assert result["totalHits"] == 100
                    # Check cache
                    assert "chicken breast:3" in _cache
        finally:
            # Cleanup
            _cache.clear()


class TestScaleNutrients:
    """Test nutrient scaling logic"""

    def test_scale_to_grams(self):
        """Should scale nutrients based on gram amount"""
        usda_food = {
            "foodNutrients": [
                {"nutrientName": "Energy", "value": 165},  # per 100g
                {"nutrientName": "Protein", "value": 31},
                {"nutrientName": "Carbohydrate, by difference", "value": 0},
                {"nutrientName": "Total lipid (fat)", "value": 3.6},
                {"nutrientName": "Fiber, total dietary", "value": 0},
                {"nutrientName": "Sodium, Na", "value": 74}
            ]
        }

        result = scale_nutrients(usda_food, 170, 'g')
        assert result is not None
        assert result["calories"] == pytest.approx(280.5, rel=0.1)  # 165 * 1.7
        assert result["protein"] == pytest.approx(52.7, rel=0.1)  # 31 * 1.7
        assert result["fat"] == pytest.approx(6.12, rel=0.1)  # 3.6 * 1.7
        assert result["sodium"] == pytest.approx(125.8, rel=0.1)  # 74 * 1.7

    def test_scale_to_ounces(self):
        """Should convert ounces to grams and scale"""
        usda_food = {
            "foodNutrients": [
                {"nutrientName": "Energy", "value": 165},  # per 100g
                {"nutrientName": "Protein", "value": 31}
            ]
        }

        # 4oz = 113.4g, scale factor = 1.134
        result = scale_nutrients(usda_food, 4, 'oz')
        assert result is not None
        assert result["calories"] == pytest.approx(187.11, rel=0.1)  # 165 * 1.134

    def test_missing_nutrients(self):
        """Should handle missing nutrients gracefully"""
        usda_food = {
            "foodNutrients": [
                {"nutrientName": "Energy", "value": 165},
                {"nutrientName": "Protein", "value": 31}
                # Missing carbs, fat, etc.
            ]
        }

        result = scale_nutrients(usda_food, 100, 'g')
        assert result is not None
        assert "calories" in result
        assert "protein" in result
        # Should not crash on missing nutrients

    def test_error_handling(self):
        """Should return None on error"""
        # Invalid structure
        result = scale_nutrients({}, 100, 'g')
        assert result is None


@pytest.mark.asyncio
class TestVerifyFoodItems:
    """Test end-to-end food verification"""

    async def test_verification_disabled(self):
        """Should return original items when verification disabled"""
        original_items = [
            FoodItem(
                name="Chicken Breast",
                quantity="170g",
                calories=200,
                macros=FoodMacros(protein=30, carbs=0, fat=5)
            )
        ]

        with patch('src.utils.nutrition_search.ENABLE_NUTRITION_VERIFICATION', False):
            result = await verify_food_items(original_items)
            assert result == original_items

    async def test_successful_verification(self):
        """Should verify and enhance food items with USDA data"""
        original_items = [
            FoodItem(
                name="Chicken Breast",
                quantity="170g",
                calories=200,
                macros=FoodMacros(protein=30, carbs=0, fat=5)
            )
        ]

        mock_usda_data = {
            "foods": [
                {
                    "fdcId": 123,
                    "description": "Chicken, broilers or fryers, breast, meat only, cooked, roasted",
                    "score": 800.0,
                    "foodNutrients": [
                        {"nutrientName": "Energy", "value": 165},
                        {"nutrientName": "Protein", "value": 31},
                        {"nutrientName": "Carbohydrate, by difference", "value": 0},
                        {"nutrientName": "Total lipid (fat)", "value": 3.6},
                        {"nutrientName": "Fiber, total dietary", "value": 0},
                        {"nutrientName": "Sodium, Na", "value": 74}
                    ]
                }
            ]
        }

        with patch('src.utils.nutrition_search.ENABLE_NUTRITION_VERIFICATION', True):
            with patch('src.utils.nutrition_search.search_usda', AsyncMock(return_value=mock_usda_data)):
                result = await verify_food_items(original_items)

                assert len(result) == 1
                assert result[0].verification_source == "usda"
                assert result[0].confidence_score is not None
                assert result[0].confidence_score > 0
                assert result[0].macros.micronutrients is not None
                assert result[0].macros.micronutrients.fiber is not None
                assert result[0].macros.micronutrients.sodium is not None

    async def test_no_usda_match_fallback(self):
        """Should fallback to AI estimate when no USDA match"""
        original_items = [
            FoodItem(
                name="Mystery Food",
                quantity="100g",
                calories=150,
                macros=FoodMacros(protein=10, carbs=20, fat=5)
            )
        ]

        # Mock empty USDA response
        mock_usda_data = {"foods": []}

        with patch('src.utils.nutrition_search.ENABLE_NUTRITION_VERIFICATION', True):
            with patch('src.utils.nutrition_search.search_usda', AsyncMock(return_value=mock_usda_data)):
                result = await verify_food_items(original_items)

                assert len(result) == 1
                assert result[0].verification_source == "ai_estimate"
                assert result[0].confidence_score == 0.5
                # Should keep original values
                assert result[0].calories == 150
                assert result[0].macros.protein == 10

    async def test_api_error_fallback(self):
        """Should fallback to AI estimate on API error"""
        original_items = [
            FoodItem(
                name="Chicken",
                quantity="100g",
                calories=150,
                macros=FoodMacros(protein=25, carbs=0, fat=5)
            )
        ]

        with patch('src.utils.nutrition_search.ENABLE_NUTRITION_VERIFICATION', True):
            with patch('src.utils.nutrition_search.search_usda', AsyncMock(return_value=None)):
                result = await verify_food_items(original_items)

                assert len(result) == 1
                assert result[0].verification_source == "ai_estimate"
                assert result[0].confidence_score == 0.5

    async def test_multiple_items(self):
        """Should verify multiple food items"""
        original_items = [
            FoodItem(
                name="Chicken Breast",
                quantity="170g",
                calories=200,
                macros=FoodMacros(protein=30, carbs=0, fat=5)
            ),
            FoodItem(
                name="Brown Rice",
                quantity="1 cup",
                calories=216,
                macros=FoodMacros(protein=5, carbs=45, fat=2)
            )
        ]

        mock_chicken_data = {
            "foods": [{
                "description": "Chicken breast",
                "score": 800,
                "foodNutrients": [
                    {"nutrientName": "Energy", "value": 165},
                    {"nutrientName": "Protein", "value": 31},
                    {"nutrientName": "Carbohydrate, by difference", "value": 0},
                    {"nutrientName": "Total lipid (fat)", "value": 3.6}
                ]
            }]
        }

        mock_rice_data = {
            "foods": [{
                "description": "Rice, brown, cooked",
                "score": 750,
                "foodNutrients": [
                    {"nutrientName": "Energy", "value": 112},
                    {"nutrientName": "Protein", "value": 2.3},
                    {"nutrientName": "Carbohydrate, by difference", "value": 24},
                    {"nutrientName": "Total lipid (fat)", "value": 0.9}
                ]
            }]
        }

        async def mock_search(name):
            if "chicken" in name:
                return mock_chicken_data
            elif "rice" in name:
                return mock_rice_data
            return None

        with patch('src.utils.nutrition_search.ENABLE_NUTRITION_VERIFICATION', True):
            with patch('src.utils.nutrition_search.search_usda', AsyncMock(side_effect=mock_search)):
                result = await verify_food_items(original_items)

                assert len(result) == 2
                assert all(item.verification_source == "usda" for item in result)

    async def test_scaling_error_fallback(self):
        """Should fallback to AI estimate if scaling fails"""
        original_items = [
            FoodItem(
                name="Chicken",
                quantity="100g",
                calories=150,
                macros=FoodMacros(protein=25, carbs=0, fat=5)
            )
        ]

        mock_usda_data = {
            "foods": [{
                "description": "Chicken",
                "score": 800,
                "foodNutrients": []  # Empty nutrients - will cause scaling to fail
            }]
        }

        with patch('src.utils.nutrition_search.ENABLE_NUTRITION_VERIFICATION', True):
            with patch('src.utils.nutrition_search.search_usda', AsyncMock(return_value=mock_usda_data)):
                result = await verify_food_items(original_items)

                assert len(result) == 1
                assert result[0].verification_source == "ai_estimate"
                assert result[0].confidence_score == 0.5
