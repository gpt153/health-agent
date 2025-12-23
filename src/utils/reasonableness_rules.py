"""
Reasonableness Rules for Nutrition Validation

Defines acceptable calorie and macro ranges for different food categories
to detect unrealistic AI estimates.
"""
import logging
from typing import Dict, List, Optional, Tuple
from src.models.food import FoodItem

logger = logging.getLogger(__name__)

# Calorie ranges per 100g for different food categories
# Format: (min_cal, max_cal) per 100g
CALORIE_RANGES = {
    # Vegetables (non-starchy)
    "vegetables": (10, 100),
    "salad": (10, 50),
    "leafy_greens": (10, 35),

    # Proteins
    "chicken_breast": (110, 200),
    "chicken": (110, 250),
    "beef": (150, 300),
    "fish": (80, 250),
    "eggs": (130, 160),
    "tofu": (70, 150),

    # Carbohydrates
    "rice": (100, 160),
    "pasta": (120, 180),
    "bread": (200, 300),
    "potato": (70, 130),
    "sweet_potato": (80, 100),

    # Fruits
    "fruit": (30, 100),
    "berries": (30, 70),
    "banana": (80, 110),

    # Dairy
    "milk": (40, 70),
    "yogurt": (50, 150),
    "cheese": (250, 400),
    "cottage_cheese": (70, 120),
    "quark": (60, 100),

    # Fats/Oils
    "oil": (800, 900),
    "butter": (700, 750),
    "nuts": (500, 700),
    "avocado": (140, 180),

    # Mixed dishes (wider ranges due to variation)
    "mixed_meal": (100, 400),
    "soup": (30, 150),
    "stew": (80, 200),
}

# Protein ranges per 100g (in grams)
PROTEIN_RANGES = {
    "chicken_breast": (20, 32),
    "chicken": (18, 32),
    "beef": (20, 30),
    "fish": (15, 30),
    "eggs": (12, 14),
    "tofu": (8, 20),
    "cottage_cheese": (10, 14),
    "quark": (10, 14),
    "yogurt": (3, 10),
    "milk": (3, 4),
    "nuts": (15, 25),
}

# Keywords to category mapping
CATEGORY_KEYWORDS = {
    "salad": ["salad", "lettuce", "greens", "arugula", "spinach", "kale"],
    "leafy_greens": ["lettuce", "spinach", "kale", "arugula", "chard"],
    "vegetables": ["vegetable", "broccoli", "carrot", "tomato", "cucumber", "pepper", "zucchini", "cauliflower"],
    "chicken_breast": ["chicken breast"],
    "chicken": ["chicken"],
    "beef": ["beef", "steak", "ground beef"],
    "fish": ["fish", "salmon", "tuna", "cod", "tilapia"],
    "eggs": ["egg"],
    "tofu": ["tofu"],
    "rice": ["rice"],
    "pasta": ["pasta", "noodle", "spaghetti"],
    "bread": ["bread", "toast"],
    "potato": ["potato"],
    "sweet_potato": ["sweet potato", "yam"],
    "fruit": ["apple", "orange", "pear", "peach", "plum", "grape"],
    "berries": ["berry", "strawberry", "blueberry", "raspberry", "blackberry"],
    "banana": ["banana"],
    "milk": ["milk"],
    "yogurt": ["yogurt", "yoghurt"],
    "cheese": ["cheese", "cheddar", "mozzarella", "parmesan"],
    "cottage_cheese": ["cottage cheese", "keso"],
    "quark": ["quark", "kvarg"],
    "oil": ["oil", "olive oil", "vegetable oil"],
    "butter": ["butter"],
    "nuts": ["nuts", "almond", "cashew", "peanut", "walnut"],
    "avocado": ["avocado"],
    "soup": ["soup"],
    "stew": ["stew"],
}


def categorize_food(food_name: str) -> Optional[str]:
    """
    Categorize a food item based on its name.

    Args:
        food_name: Name of the food item

    Returns:
        Category name or None if not categorized
    """
    food_lower = food_name.lower()

    # Check specific categories first (more specific matches)
    priority_categories = [
        "chicken_breast", "cottage_cheese", "quark", "sweet_potato",
        "leafy_greens", "salad"
    ]

    for category in priority_categories:
        keywords = CATEGORY_KEYWORDS.get(category, [])
        if any(keyword in food_lower for keyword in keywords):
            return category

    # Check general categories
    for category, keywords in CATEGORY_KEYWORDS.items():
        if category in priority_categories:
            continue
        if any(keyword in food_lower for keyword in keywords):
            return category

    return None


def parse_quantity_to_grams(quantity: str) -> Optional[float]:
    """
    Parse quantity string to grams for comparison.

    Args:
        quantity: Quantity string (e.g., "100g", "1 cup", "2 eggs")

    Returns:
        Weight in grams or None if cannot parse
    """
    import re

    quantity_lower = quantity.lower().strip()

    # Direct gram measurements
    gram_match = re.match(r'^(\d+(?:\.\d+)?)\s*g(?:rams?)?$', quantity_lower)
    if gram_match:
        return float(gram_match.group(1))

    # Kilogram to grams
    kg_match = re.match(r'^(\d+(?:\.\d+)?)\s*kg$', quantity_lower)
    if kg_match:
        return float(kg_match.group(1)) * 1000

    # Ounces to grams
    oz_match = re.match(r'^(\d+(?:\.\d+)?)\s*oz$', quantity_lower)
    if oz_match:
        return float(oz_match.group(1)) * 28.35

    # Common item conversions (approximate)
    item_conversions = {
        "egg": 50,  # medium egg
        "chicken breast": 150,  # typical serving
        "apple": 180,
        "banana": 120,
        "potato": 150,
    }

    for item, grams in item_conversions.items():
        pattern = rf'^(\d+(?:\.\d+)?)\s*(?:piece|pieces|item|items|{item}s?)$'
        match = re.match(pattern, quantity_lower)
        if match:
            count = float(match.group(1))
            return count * grams

    # Cup measurements (approximate, varies by food)
    cup_match = re.match(r'^(\d+(?:\.\d+)?)\s*cups?$', quantity_lower)
    if cup_match:
        return float(cup_match.group(1)) * 150  # Rough average

    return None


def check_reasonableness(food_item: FoodItem) -> Tuple[bool, List[str]]:
    """
    Check if a food item's nutritional values are reasonable.

    Args:
        food_item: FoodItem to validate

    Returns:
        Tuple of (is_reasonable, list_of_warnings)
    """
    warnings = []

    # Categorize the food
    category = categorize_food(food_item.name)

    if not category:
        # Unknown category - can't validate
        logger.debug(f"Unknown category for '{food_item.name}', skipping validation")
        return True, []

    # Parse quantity to grams
    grams = parse_quantity_to_grams(food_item.quantity)

    if not grams or grams <= 0:
        logger.debug(f"Could not parse quantity '{food_item.quantity}' for '{food_item.name}'")
        return True, []

    # Calculate calories per 100g
    calories_per_100g = (food_item.calories / grams) * 100

    # Check against calorie range
    if category in CALORIE_RANGES:
        min_cal, max_cal = CALORIE_RANGES[category]

        if calories_per_100g < min_cal:
            warnings.append(
                f"⚠️ {food_item.name}: {food_item.calories} cal seems LOW "
                f"({calories_per_100g:.0f} cal/100g). Expected {min_cal}-{max_cal} cal/100g."
            )
        elif calories_per_100g > max_cal:
            warnings.append(
                f"⚠️ {food_item.name}: {food_item.calories} cal seems HIGH "
                f"({calories_per_100g:.0f} cal/100g). Expected {min_cal}-{max_cal} cal/100g."
            )

    # Check protein if category has protein ranges
    if category in PROTEIN_RANGES:
        protein_per_100g = (food_item.macros.protein / grams) * 100
        min_protein, max_protein = PROTEIN_RANGES[category]

        if protein_per_100g < min_protein * 0.7:  # Allow 30% margin
            warnings.append(
                f"⚠️ {food_item.name}: {food_item.macros.protein}g protein seems LOW "
                f"({protein_per_100g:.1f}g/100g). Expected {min_protein}-{max_protein}g/100g."
            )
        elif protein_per_100g > max_protein * 1.3:  # Allow 30% margin
            warnings.append(
                f"⚠️ {food_item.name}: {food_item.macros.protein}g protein seems HIGH "
                f"({protein_per_100g:.1f}g/100g). Expected {min_protein}-{max_protein}g/100g."
            )

    # Macro sanity check: protein + carbs + fat calories should roughly equal total
    macro_calories = (
        food_item.macros.protein * 4 +
        food_item.macros.carbs * 4 +
        food_item.macros.fat * 9
    )

    calorie_diff_percent = abs(macro_calories - food_item.calories) / max(food_item.calories, 1) * 100

    if calorie_diff_percent > 25:  # Allow 25% discrepancy
        warnings.append(
            f"⚠️ {food_item.name}: Macro calories ({macro_calories:.0f}) don't match "
            f"total calories ({food_item.calories}). Difference: {calorie_diff_percent:.0f}%."
        )

    is_reasonable = len(warnings) == 0

    if warnings:
        logger.warning(f"Reasonableness check failed for '{food_item.name}': {warnings}")

    return is_reasonable, warnings


def validate_food_items(food_items: List[FoodItem]) -> Tuple[List[FoodItem], List[str]]:
    """
    Validate a list of food items for reasonableness.

    Args:
        food_items: List of FoodItem to validate

    Returns:
        Tuple of (validated_items, all_warnings)
    """
    all_warnings = []

    for item in food_items:
        is_reasonable, warnings = check_reasonableness(item)
        all_warnings.extend(warnings)

    return food_items, all_warnings
