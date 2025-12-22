"""Nutrition estimate validation and reasonableness checking

This module provides validation for AI-generated nutrition estimates by comparing
them against typical ranges from USDA data and nutritional science.
"""

import logging
import re
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

# Typical calorie ranges per 100g (based on USDA FoodData Central)
# Format: {"food_key": {"min": cal, "max": cal, "typical": cal}}
FOOD_RANGES = {
    # Salads & Vegetables
    "salad": {"min": 15, "max": 150, "typical": 50},
    "green salad": {"min": 10, "max": 80, "typical": 30},
    "caesar salad": {"min": 80, "max": 200, "typical": 120},
    "garden salad": {"min": 15, "max": 100, "typical": 40},
    "mixed salad": {"min": 20, "max": 100, "typical": 45},

    # Proteins
    "chicken breast": {"min": 140, "max": 180, "typical": 165},
    "grilled chicken": {"min": 150, "max": 200, "typical": 175},
    "chicken": {"min": 140, "max": 250, "typical": 190},
    "salmon": {"min": 180, "max": 220, "typical": 206},
    "tuna": {"min": 100, "max": 150, "typical": 130},
    "beef": {"min": 200, "max": 300, "typical": 250},
    "pork": {"min": 180, "max": 280, "typical": 242},
    "tofu": {"min": 70, "max": 100, "typical": 76},
    "egg": {"min": 130, "max": 160, "typical": 143},  # per 100g

    # Carbohydrates
    "rice": {"min": 110, "max": 150, "typical": 130},
    "brown rice": {"min": 100, "max": 120, "typical": 112},
    "white rice": {"min": 120, "max": 140, "typical": 130},
    "pasta": {"min": 120, "max": 160, "typical": 140},
    "bread": {"min": 230, "max": 280, "typical": 265},
    "potato": {"min": 70, "max": 95, "typical": 77},
    "sweet potato": {"min": 80, "max": 100, "typical": 86},
    "oats": {"min": 350, "max": 390, "typical": 371},
    "quinoa": {"min": 110, "max": 130, "typical": 120},

    # Fruits
    "apple": {"min": 45, "max": 60, "typical": 52},
    "banana": {"min": 80, "max": 100, "typical": 89},
    "orange": {"min": 40, "max": 55, "typical": 47},
    "berries": {"min": 30, "max": 70, "typical": 50},
    "strawberry": {"min": 30, "max": 40, "typical": 32},
    "blueberry": {"min": 55, "max": 65, "typical": 57},
    "grapes": {"min": 65, "max": 75, "typical": 69},
    "watermelon": {"min": 25, "max": 35, "typical": 30},

    # Dairy
    "milk": {"min": 40, "max": 70, "typical": 61},
    "yogurt": {"min": 50, "max": 100, "typical": 61},
    "greek yogurt": {"min": 80, "max": 120, "typical": 97},
    "cheese": {"min": 300, "max": 450, "typical": 402},
    "cottage cheese": {"min": 80, "max": 120, "typical": 98},
    "quark": {"min": 60, "max": 80, "typical": 67},

    # Nuts & Seeds
    "almonds": {"min": 550, "max": 620, "typical": 579},
    "peanuts": {"min": 550, "max": 600, "typical": 567},
    "walnuts": {"min": 650, "max": 700, "typical": 654},
    "chia seeds": {"min": 450, "max": 500, "typical": 486},

    # Fats & Oils
    "olive oil": {"min": 880, "max": 900, "typical": 884},
    "butter": {"min": 710, "max": 750, "typical": 717},
    "avocado": {"min": 150, "max": 180, "typical": 160},
}


def extract_quantity_grams(quantity_str: str) -> Optional[float]:
    """
    Extract quantity in grams from string like '170g', '1 cup', '2 eggs'.

    Args:
        quantity_str: Quantity string from user or AI

    Returns:
        Float representing grams, or None if unparseable
    """
    quantity_str = quantity_str.lower().strip()

    # Direct gram specification
    if match := re.match(r'(\d+(?:\.\d+)?)\s*g(?:rams?)?', quantity_str, re.IGNORECASE):
        return float(match.group(1))

    # Common unit conversions (approximate)
    conversions = {
        'cup': 240,
        'cups': 240,
        'tbsp': 15,
        'tablespoon': 15,
        'tsp': 5,
        'teaspoon': 5,
        'oz': 28.35,
        'ounce': 28.35,
        'lb': 453.59,
        'pound': 453.59,
        'kg': 1000,
        'ml': 1,  # Approximate for liquids
        'liter': 1000,
    }

    for unit, grams in conversions.items():
        if match := re.match(rf'(\d+(?:\.\d+)?)\s*{unit}s?', quantity_str, re.IGNORECASE):
            amount = float(match.group(1))
            return amount * grams

    # Size descriptors (rough estimates)
    if 'small' in quantity_str:
        return 80
    elif 'medium' in quantity_str:
        return 150
    elif 'large' in quantity_str:
        return 250
    elif 'extra large' in quantity_str or 'xl' in quantity_str:
        return 350

    # Items (default to reasonable portion)
    if re.search(r'\d+\s*(item|piece|serving)', quantity_str):
        match = re.search(r'(\d+)', quantity_str)
        if match:
            count = int(match.group(1))
            return count * 100  # Assume 100g per item

    logger.debug(f"Could not parse quantity: {quantity_str}")
    return None


def normalize_food_name(food_name: str) -> str:
    """
    Normalize food name for range lookup.

    Args:
        food_name: Raw food name

    Returns:
        Normalized lowercase food name
    """
    normalized = food_name.lower().strip()

    # Remove common qualifiers
    qualifiers = [
        r'\b(organic|fresh|raw|cooked|grilled|baked|fried|steamed|boiled)\b',
        r'\b(homemade|store-bought|restaurant)\b',
        r'\b(large|medium|small|extra)\b',
        r'\b(sliced|diced|chopped|shredded)\b'
    ]

    for pattern in qualifiers:
        normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)

    # Clean up whitespace
    normalized = ' '.join(normalized.split())

    return normalized


def find_food_range(food_name: str) -> Optional[Dict[str, float]]:
    """
    Find matching calorie range for a food.

    Args:
        food_name: Normalized food name

    Returns:
        Dict with min, max, typical calories per 100g, or None
    """
    food_lower = normalize_food_name(food_name)

    # Try exact match first
    if food_lower in FOOD_RANGES:
        return FOOD_RANGES[food_lower]

    # Try partial matches (find most specific match)
    matches = []
    for key, value in FOOD_RANGES.items():
        if key in food_lower or food_lower in key:
            matches.append((key, value, len(key)))

    if matches:
        # Return longest match (most specific)
        matches.sort(key=lambda x: x[2], reverse=True)
        logger.debug(f"Matched '{food_name}' to '{matches[0][0]}'")
        return matches[0][1]

    return None


def validate_nutrition_estimate(
    food_name: str,
    quantity: str,
    calories: int,
    protein: float = 0,
    carbs: float = 0,
    fat: float = 0
) -> Dict:
    """
    Validate if nutrition estimate is reasonable.

    Args:
        food_name: Name of food item
        quantity: Quantity string (e.g., "170g", "1 cup", "small")
        calories: Estimated calories
        protein: Protein in grams
        carbs: Carbs in grams
        fat: Fat in grams

    Returns:
        {
            "is_valid": bool,
            "confidence": float (0.0-1.0),
            "issues": list[str],
            "suggested_calories": int or None,
            "reasoning": str,
            "expected_range": tuple (min, max) or None
        }
    """
    result = {
        "is_valid": True,
        "confidence": 1.0,
        "issues": [],
        "suggested_calories": None,
        "reasoning": "",
        "expected_range": None
    }

    # Find matching food range
    food_range = find_food_range(food_name)

    if not food_range:
        # Unknown food - can't validate
        result["confidence"] = 0.5
        result["reasoning"] = f"Unknown food '{food_name}' - no validation range available"
        logger.info(f"No range for '{food_name}', cannot validate")
        return result

    # Extract quantity in grams
    grams = extract_quantity_grams(quantity)

    if not grams:
        result["confidence"] = 0.6
        result["reasoning"] = f"Could not parse quantity '{quantity}' - validation limited"
        logger.warning(f"Could not parse quantity: {quantity}")
        return result

    # Calculate expected calorie range
    expected_min = (grams / 100) * food_range["min"]
    expected_max = (grams / 100) * food_range["max"]
    expected_typical = (grams / 100) * food_range["typical"]

    result["expected_range"] = (int(expected_min), int(expected_max))

    # Validate against range
    if calories < expected_min * 0.7:  # More than 30% below minimum
        result["is_valid"] = False
        result["confidence"] = 0.3
        result["issues"].append(
            f"Estimate {calories} kcal is too low "
            f"(expected {int(expected_min)}-{int(expected_max)} kcal for {grams}g)"
        )
        result["suggested_calories"] = int(expected_typical)
        result["reasoning"] = f"Significantly below typical range for {food_name}"
        logger.warning(f"LOW estimate for {food_name}: {calories} vs {expected_min}-{expected_max}")

    elif calories > expected_max * 1.5:  # More than 50% above maximum
        result["is_valid"] = False
        result["confidence"] = 0.3
        result["issues"].append(
            f"Estimate {calories} kcal is too high "
            f"(expected {int(expected_min)}-{int(expected_max)} kcal for {grams}g)"
        )
        result["suggested_calories"] = int(expected_typical)
        result["reasoning"] = f"Significantly above typical range for {food_name}"
        logger.warning(f"HIGH estimate for {food_name}: {calories} vs {expected_min}-{expected_max}")

    elif calories < expected_min or calories > expected_max:
        # Outside range but not drastically
        result["confidence"] = 0.7
        result["issues"].append(
            f"Estimate {calories} kcal is outside typical range "
            f"({int(expected_min)}-{int(expected_max)} kcal)"
        )
        result["reasoning"] = f"Somewhat unusual for {food_name}, but possible"
        logger.info(f"Outside range for {food_name}: {calories} vs {expected_min}-{expected_max}")

    else:
        # Within expected range
        result["confidence"] = 0.9
        result["reasoning"] = (
            f"Within typical range ({int(expected_min)}-{int(expected_max)} kcal) "
            f"for {grams}g of {food_name}"
        )
        logger.debug(f"Valid estimate for {food_name}: {calories} in [{expected_min}, {expected_max}]")

    # Validate macros sum (4-4-9 rule)
    if protein or carbs or fat:
        macro_calories = (protein * 4) + (carbs * 4) + (fat * 9)

        # Allow 20% variance (AI rounding, fiber adjustments, etc.)
        if calories > 0 and abs(macro_calories - calories) > calories * 0.2:
            result["issues"].append(
                f"Macros don't add up: {int(macro_calories)} kcal from macros "
                f"vs {calories} kcal total"
            )
            result["confidence"] *= 0.8
            logger.warning(
                f"Macro mismatch for {food_name}: "
                f"P{protein}g C{carbs}g F{fat}g = {macro_calories} kcal vs {calories} kcal"
            )

    return result


def batch_validate_food_items(food_items: list) -> list:
    """
    Validate a list of food items.

    Args:
        food_items: List of FoodItem objects

    Returns:
        List of validation results (same order as input)
    """
    results = []

    for item in food_items:
        validation = validate_nutrition_estimate(
            food_name=item.name,
            quantity=item.quantity,
            calories=item.calories,
            protein=item.macros.protein,
            carbs=item.macros.carbs,
            fat=item.macros.fat
        )
        results.append(validation)

    return results


# Example usage and tests
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)

    print("=" * 60)
    print("NUTRITION VALIDATION TESTS")
    print("=" * 60)

    # Test case 1: Small salad at 450 cal (user-reported issue)
    print("\n1. Small salad at 450 cal (SHOULD FAIL)")
    result1 = validate_nutrition_estimate(
        food_name="green salad",
        quantity="small",
        calories=450,
        protein=5,
        carbs=10,
        fat=35
    )
    print(f"   Valid: {result1['is_valid']}")
    print(f"   Confidence: {result1['confidence']}")
    print(f"   Issues: {result1['issues']}")
    print(f"   Suggested: {result1['suggested_calories']} kcal")
    print(f"   Range: {result1['expected_range']}")

    # Test case 2: Chicken breast 170g at 650 cal (user-reported issue)
    print("\n2. Chicken breast 170g at 650 cal (SHOULD FAIL)")
    result2 = validate_nutrition_estimate(
        food_name="chicken breast",
        quantity="170g",
        calories=650,
        protein=55,
        carbs=0,
        fat=45
    )
    print(f"   Valid: {result2['is_valid']}")
    print(f"   Confidence: {result2['confidence']}")
    print(f"   Issues: {result2['issues']}")
    print(f"   Suggested: {result2['suggested_calories']} kcal")
    print(f"   Range: {result2['expected_range']}")

    # Test case 3: Chicken breast 170g at 280 cal (reasonable)
    print("\n3. Chicken breast 170g at 280 cal (SHOULD PASS)")
    result3 = validate_nutrition_estimate(
        food_name="chicken breast",
        quantity="170g",
        calories=280,
        protein=53,
        carbs=0,
        fat=6
    )
    print(f"   Valid: {result3['is_valid']}")
    print(f"   Confidence: {result3['confidence']}")
    print(f"   Reasoning: {result3['reasoning']}")
    print(f"   Range: {result3['expected_range']}")

    # Test case 4: Medium banana (reasonable)
    print("\n4. Medium banana at 105 cal (SHOULD PASS)")
    result4 = validate_nutrition_estimate(
        food_name="banana",
        quantity="medium",
        calories=105,
        protein=1.3,
        carbs=27,
        fat=0.4
    )
    print(f"   Valid: {result4['is_valid']}")
    print(f"   Confidence: {result4['confidence']}")
    print(f"   Reasoning: {result4['reasoning']}")

    print("\n" + "=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)
