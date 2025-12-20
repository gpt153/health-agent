"""USDA FoodData Central API integration for nutritional data verification"""
import logging
import re
import httpx
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from src.config import USDA_API_KEY, ENABLE_NUTRITION_VERIFICATION
from src.models.food import FoodItem, FoodMacros, Micronutrients

logger = logging.getLogger(__name__)

# Simple in-memory cache with expiration
_cache: Dict[str, Tuple[Dict[Any, Any], datetime]] = {}
CACHE_DURATION = timedelta(hours=24)  # Cache for 24 hours
API_TIMEOUT = 5.0  # 5 second timeout for API calls


def normalize_food_name(name: str) -> str:
    """
    Normalize food name for better USDA matching.

    Args:
        name: Raw food name from vision AI

    Returns:
        Normalized food name for search
    """
    # Convert to lowercase
    normalized = name.lower().strip()

    # Remove common qualifiers that don't affect nutrition
    qualifiers = [
        r'\b(organic|fresh|raw|cooked|grilled|baked|fried|steamed)\b',
        r'\b(homemade|store-bought|restaurant)\b',
        r'\b(large|medium|small|extra)\b'
    ]
    for pattern in qualifiers:
        normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)

    # Clean up whitespace
    normalized = ' '.join(normalized.split())

    logger.debug(f"Normalized '{name}' -> '{normalized}'")
    return normalized


def parse_quantity(quantity_str: str) -> Tuple[float, str]:
    """
    Parse quantity string to extract amount and unit.

    Args:
        quantity_str: Quantity string like "100g", "1 cup", "2 eggs"

    Returns:
        Tuple of (amount, unit)
    """
    # Remove leading/trailing whitespace
    quantity_str = quantity_str.strip().lower()

    # Common patterns
    patterns = [
        (r'^(\d+(?:\.\d+)?)\s*g(?:rams?)?$', 'g'),  # "100g", "100 grams"
        (r'^(\d+(?:\.\d+)?)\s*oz$', 'oz'),  # "4oz"
        (r'^(\d+(?:\.\d+)?)\s*lb$', 'lb'),  # "1lb"
        (r'^(\d+(?:\.\d+)?)\s*kg$', 'kg'),  # "0.5kg"
        (r'^(\d+(?:\.\d+)?)\s*cup(?:s)?$', 'cup'),  # "1 cup"
        (r'^(\d+(?:\.\d+)?)\s*tbsp$', 'tbsp'),  # "2 tbsp"
        (r'^(\d+(?:\.\d+)?)\s*tsp$', 'tsp'),  # "1 tsp"
        (r'^(\d+(?:\.\d+)?)\s*ml$', 'ml'),  # "250ml"
        (r'^(\d+(?:\.\d+)?)\s*(?:piece|pieces|item|items|egg|eggs|apple|apples)$', 'item'),  # "2 eggs"
    ]

    for pattern, unit in patterns:
        match = re.match(pattern, quantity_str)
        if match:
            amount = float(match.group(1))
            logger.debug(f"Parsed '{quantity_str}' -> {amount} {unit}")
            return amount, unit

    # Default fallback
    logger.debug(f"Could not parse '{quantity_str}', using default 100g")
    return 100.0, 'g'


async def search_usda(
    food_name: str,
    max_results: int = 3
) -> Optional[Dict[str, Any]]:
    """
    Search USDA FoodData Central for food items.

    Args:
        food_name: Normalized food name
        max_results: Maximum number of results to return

    Returns:
        USDA API response dict or None if failed
    """
    if not ENABLE_NUTRITION_VERIFICATION:
        logger.info("Nutrition verification disabled, skipping USDA search")
        return None

    # Check cache
    cache_key = f"{food_name}:{max_results}"
    if cache_key in _cache:
        cached_data, cached_time = _cache[cache_key]
        if datetime.now() - cached_time < CACHE_DURATION:
            logger.info(f"Cache hit for '{food_name}'")
            return cached_data
        else:
            # Remove expired cache entry
            del _cache[cache_key]

    try:
        url = "https://api.nal.usda.gov/fdc/v1/foods/search"
        params = {
            "api_key": USDA_API_KEY,
            "query": food_name,
            "pageSize": max_results,
            "dataType": ["Survey (FNDDS)", "Foundation", "SR Legacy"]  # Prioritize these
        }

        logger.info(f"Searching USDA for '{food_name}'")

        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            # Cache the result
            _cache[cache_key] = (data, datetime.now())

            logger.info(f"USDA search returned {data.get('totalHits', 0)} results")
            return data

    except httpx.TimeoutException:
        logger.warning(f"USDA API timeout for '{food_name}'")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"USDA API HTTP error: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"USDA search error: {e}", exc_info=True)
        return None


def scale_nutrients(
    usda_food: Dict[str, Any],
    target_amount: float,
    target_unit: str
) -> Optional[Dict[str, float]]:
    """
    Scale USDA nutrients to target quantity.

    Args:
        usda_food: USDA food item from search results
        target_amount: Target amount (e.g., 170 for 170g)
        target_unit: Target unit (e.g., 'g', 'cup', 'item')

    Returns:
        Dict with scaled nutrients or None if scaling fails
    """
    try:
        nutrients = usda_food.get('foodNutrients', [])

        # Get serving size (USDA uses 100g as base for most items)
        serving_size = 100.0  # Default to 100g
        serving_unit = 'g'

        # Check if food has portion information
        portions = usda_food.get('foodPortions', [])
        if portions and target_unit != 'g':
            # Try to find matching portion unit
            for portion in portions:
                portion_desc = portion.get('modifier', '').lower()
                if target_unit in portion_desc or target_unit == 'item':
                    serving_size = portion.get('gramWeight', 100.0)
                    break

        # Calculate scaling factor
        if target_unit == 'g':
            scale_factor = target_amount / serving_size
        elif target_unit == 'kg':
            scale_factor = (target_amount * 1000) / serving_size
        elif target_unit == 'oz':
            scale_factor = (target_amount * 28.35) / serving_size
        elif target_unit == 'lb':
            scale_factor = (target_amount * 453.59) / serving_size
        else:
            # For items, cups, etc., assume USDA portion is correct
            scale_factor = target_amount

        # Extract key nutrients
        nutrient_map = {
            'Energy': 'calories',
            'Protein': 'protein',
            'Carbohydrate, by difference': 'carbs',
            'Total lipid (fat)': 'fat',
            'Fiber, total dietary': 'fiber',
            'Sodium, Na': 'sodium',
            'Sugars, total including NLEA': 'sugar',
            'Vitamin C, total ascorbic acid': 'vitamin_c',
            'Calcium, Ca': 'calcium',
            'Iron, Fe': 'iron'
        }

        result = {}
        for nutrient in nutrients:
            nutrient_name = nutrient.get('nutrientName', '')
            nutrient_value = nutrient.get('value', 0)

            for usda_name, our_name in nutrient_map.items():
                if usda_name in nutrient_name:
                    result[our_name] = round(nutrient_value * scale_factor, 2)
                    break

        logger.debug(f"Scaled nutrients (factor={scale_factor:.2f}): {result}")
        return result

    except Exception as e:
        logger.error(f"Error scaling nutrients: {e}", exc_info=True)
        return None


async def verify_food_items(food_items: List[FoodItem]) -> List[FoodItem]:
    """
    Verify food items against USDA database.
    Main entry point for verification.

    Args:
        food_items: List of FoodItem from vision AI

    Returns:
        List of FoodItem with verified/enhanced nutritional data
    """
    if not ENABLE_NUTRITION_VERIFICATION:
        logger.info("Nutrition verification disabled, returning original items")
        return food_items

    verified_items = []

    for item in food_items:
        try:
            # Normalize food name
            normalized_name = normalize_food_name(item.name)

            # Parse quantity
            amount, unit = parse_quantity(item.quantity)

            # Search USDA
            usda_results = await search_usda(normalized_name)

            if not usda_results or not usda_results.get('foods'):
                logger.info(f"No USDA match for '{item.name}', using AI estimate")
                # Mark as AI estimate
                item.verification_source = "ai_estimate"
                item.confidence_score = 0.5
                verified_items.append(item)
                continue

            # Get best match (first result is usually best)
            best_match = usda_results['foods'][0]
            logger.info(f"USDA match: '{best_match.get('description')}' (score: {best_match.get('score', 0)})")

            # Scale nutrients to target quantity
            scaled_nutrients = scale_nutrients(best_match, amount, unit)

            if not scaled_nutrients:
                logger.warning(f"Failed to scale nutrients for '{item.name}', using AI estimate")
                item.verification_source = "ai_estimate"
                item.confidence_score = 0.5
                verified_items.append(item)
                continue

            # Create verified food item with USDA data
            verified_macros = FoodMacros(
                protein=scaled_nutrients.get('protein', item.macros.protein),
                carbs=scaled_nutrients.get('carbs', item.macros.carbs),
                fat=scaled_nutrients.get('fat', item.macros.fat),
                micronutrients=Micronutrients(
                    fiber=scaled_nutrients.get('fiber'),
                    sodium=scaled_nutrients.get('sodium'),
                    sugar=scaled_nutrients.get('sugar'),
                    vitamin_c=scaled_nutrients.get('vitamin_c'),
                    calcium=scaled_nutrients.get('calcium'),
                    iron=scaled_nutrients.get('iron')
                )
            )

            verified_item = FoodItem(
                name=item.name,
                quantity=item.quantity,
                calories=int(scaled_nutrients.get('calories', item.calories)),
                macros=verified_macros,
                verification_source="usda",
                confidence_score=min(best_match.get('score', 100) / 100, 1.0)
            )

            logger.info(f"Verified '{item.name}': {verified_item.calories} cal (USDA)")
            verified_items.append(verified_item)

        except Exception as e:
            logger.error(f"Error verifying '{item.name}': {e}", exc_info=True)
            # Fallback to AI estimate
            item.verification_source = "ai_estimate"
            item.confidence_score = 0.5
            verified_items.append(item)

    return verified_items
