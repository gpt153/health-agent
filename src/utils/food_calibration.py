"""
Food Calibration System - Learning from User Corrections

Phase 4: Tracks user corrections and applies learned calibration factors
to future estimates, reducing repeat errors.
"""
import logging
import re
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.models.food import FoodItem, FoodMacros

logger = logging.getLogger(__name__)


@dataclass
class CorrectionPattern:
    """Pattern learned from user corrections"""
    food_category: str
    avg_correction_factor: float  # corrected / original (e.g., 0.8 means AI over-estimates by 20%)
    correction_count: int
    last_updated: datetime
    confidence: float  # 0.0-1.0 based on correction_count


# In-memory correction patterns (will be persisted to database in full implementation)
_correction_patterns: Dict[str, CorrectionPattern] = {}

# User-specific corrections
_user_corrections: Dict[str, List[Dict[str, Any]]] = {}


def detect_correction_intent(message: str) -> bool:
    """
    Detect if user message is attempting to correct a food entry.

    Args:
        message: User's message text

    Returns:
        True if message appears to be a correction
    """
    correction_patterns = [
        r"\b(wrong|incorrect|that'?s not right)\b",
        r"\b(should be|actually|really)\s+\d+",
        r"\b(too high|too low|way off|way too)\b",
        r"\b(update|change|fix|correct)\b.*\b(calories|cal)\b",
        r"\b(not|isn't|wasnt)\s+\d+\s+(cal|calories)",
        r"\b(more like|closer to)\s+\d+"
    ]

    message_lower = message.lower()

    for pattern in correction_patterns:
        if re.search(pattern, message_lower):
            return True

    return False


def extract_corrected_calories(message: str) -> Optional[int]:
    """
    Extract corrected calorie value from user message.

    Args:
        message: User's correction message

    Returns:
        Corrected calorie value or None if not found

    Examples:
        "should be 220 cal" → 220
        "actually 180 calories" → 180
        "more like 250" → 250
    """
    # Pattern: number followed by "cal" or "calories"
    match = re.search(r"(\d+)\s*(?:cal(?:ories)?)?", message)

    if match:
        return int(match.group(1))

    return None


def categorize_food(food_name: str) -> str:
    """
    Categorize food into broad category for pattern matching.

    Args:
        food_name: Name of the food

    Returns:
        Category name (e.g., "protein", "salad", "rice", etc.)
    """
    food_lower = food_name.lower()

    # Protein sources
    if any(keyword in food_lower for keyword in ["chicken", "beef", "pork", "fish", "salmon", "tuna", "turkey", "steak"]):
        return "protein_meat"

    if any(keyword in food_lower for keyword in ["egg", "tofu", "tempeh"]):
        return "protein_other"

    # Vegetables
    if any(keyword in food_lower for keyword in ["salad", "lettuce", "greens", "spinach", "kale"]):
        return "salad_greens"

    if any(keyword in food_lower for keyword in ["vegetable", "veggie", "carrot", "broccoli", "pepper"]):
        return "vegetables"

    # Grains
    if any(keyword in food_lower for keyword in ["rice", "pasta", "noodle", "quinoa"]):
        return "grains"

    if any(keyword in food_lower for keyword in ["bread", "toast", "bagel", "tortilla"]):
        return "bread"

    # Fruits
    if any(keyword in food_lower for keyword in ["apple", "banana", "orange", "berry", "fruit"]):
        return "fruit"

    # Restaurant items
    if any(keyword in food_lower for keyword in ["chipotle", "mcdonalds", "burger king", "subway"]):
        return "restaurant_fast_food"

    if any(keyword in food_lower for keyword in ["pizza", "burger", "sandwich", "taco", "burrito"]):
        return "prepared_meal"

    # Default
    return "other"


async def save_correction(
    user_id: str,
    food_name: str,
    original_calories: int,
    corrected_calories: int,
    entry_id: Optional[str] = None
) -> None:
    """
    Save a user correction to the knowledge base.

    Args:
        user_id: User who made the correction
        food_name: Name of the food
        original_calories: Original AI estimate
        corrected_calories: User's corrected value
        entry_id: ID of the food entry that was corrected
    """
    correction_factor = corrected_calories / original_calories if original_calories > 0 else 1.0

    # Save user-specific correction
    if user_id not in _user_corrections:
        _user_corrections[user_id] = []

    _user_corrections[user_id].append({
        "food_name": food_name,
        "original_calories": original_calories,
        "corrected_calories": corrected_calories,
        "correction_factor": correction_factor,
        "timestamp": datetime.now(),
        "entry_id": entry_id
    })

    # Update global correction patterns
    category = categorize_food(food_name)

    if category in _correction_patterns:
        pattern = _correction_patterns[category]

        # Update running average
        total_factor = pattern.avg_correction_factor * pattern.correction_count
        new_total = total_factor + correction_factor
        pattern.correction_count += 1
        pattern.avg_correction_factor = new_total / pattern.correction_count
        pattern.last_updated = datetime.now()
        pattern.confidence = min(pattern.correction_count / 10, 1.0)  # Max confidence at 10 corrections

    else:
        # Create new pattern
        _correction_patterns[category] = CorrectionPattern(
            food_category=category,
            avg_correction_factor=correction_factor,
            correction_count=1,
            last_updated=datetime.now(),
            confidence=0.1  # Low confidence with single correction
        )

    logger.info(f"Saved correction for '{food_name}' (category: {category}): "
                f"{original_calories} → {corrected_calories} (factor: {correction_factor:.2f})")


async def get_user_corrections(user_id: str, food_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get correction history for a user.

    Args:
        user_id: User ID
        food_name: Optional filter by food name

    Returns:
        List of correction records
    """
    if user_id not in _user_corrections:
        return []

    corrections = _user_corrections[user_id]

    if food_name:
        # Filter by food name (fuzzy match)
        food_lower = food_name.lower()
        corrections = [c for c in corrections if food_lower in c["food_name"].lower()]

    return corrections


async def apply_calibration(
    food_item: FoodItem,
    user_id: Optional[str] = None
) -> FoodItem:
    """
    Apply learned calibration factors to food estimate.

    Args:
        food_item: Food item with initial estimate
        user_id: User ID for user-specific calibrations

    Returns:
        Calibrated FoodItem
    """
    category = categorize_food(food_item.name)

    # Check global correction patterns
    if category in _correction_patterns:
        pattern = _correction_patterns[category]

        # Only apply if we have enough data (3+ corrections) and reasonable confidence
        if pattern.correction_count >= 3 and pattern.confidence >= 0.3:
            logger.info(f"Applying global calibration for {category}: "
                       f"factor {pattern.avg_correction_factor:.2f} "
                       f"(based on {pattern.correction_count} corrections)")

            calibrated_calories = int(food_item.calories * pattern.avg_correction_factor)
            calibrated_protein = food_item.macros.protein * pattern.avg_correction_factor
            calibrated_carbs = food_item.macros.carbs * pattern.avg_correction_factor
            calibrated_fat = food_item.macros.fat * pattern.avg_correction_factor

            calibrated_item = FoodItem(
                name=food_item.name,
                quantity=food_item.quantity,
                calories=calibrated_calories,
                macros=FoodMacros(
                    protein=calibrated_protein,
                    carbs=calibrated_carbs,
                    fat=calibrated_fat
                ),
                verification_source=f"{food_item.verification_source}+calibrated",
                confidence_score=food_item.confidence_score,
                food_category=category
            )

            return calibrated_item

    # Check user-specific corrections
    if user_id:
        user_corrections = await get_user_corrections(user_id, food_item.name)

        if len(user_corrections) >= 2:
            # Calculate average user-specific correction factor
            avg_factor = sum(c["correction_factor"] for c in user_corrections) / len(user_corrections)

            logger.info(f"Applying user-specific calibration for '{food_item.name}': "
                       f"factor {avg_factor:.2f} "
                       f"(based on {len(user_corrections)} user corrections)")

            calibrated_calories = int(food_item.calories * avg_factor)
            calibrated_protein = food_item.macros.protein * avg_factor
            calibrated_carbs = food_item.macros.carbs * avg_factor
            calibrated_fat = food_item.macros.fat * avg_factor

            return FoodItem(
                name=food_item.name,
                quantity=food_item.quantity,
                calories=calibrated_calories,
                macros=FoodMacros(
                    protein=calibrated_protein,
                    carbs=calibrated_carbs,
                    fat=calibrated_fat
                ),
                verification_source=f"{food_item.verification_source}+user_calibrated",
                confidence_score=food_item.confidence_score,
                food_category=category
            )

    # No calibration available
    return food_item


async def calibrate_foods(foods: List[FoodItem], user_id: Optional[str] = None) -> List[FoodItem]:
    """
    Apply calibration to a list of foods.

    Args:
        foods: List of food items
        user_id: User ID for user-specific calibrations

    Returns:
        List of calibrated food items
    """
    calibrated = []

    for food in foods:
        calibrated_food = await apply_calibration(food, user_id)
        calibrated.append(calibrated_food)

    return calibrated


def get_correction_summary(user_id: str) -> Dict[str, Any]:
    """
    Get summary of user's correction patterns.

    Args:
        user_id: User ID

    Returns:
        Summary statistics
    """
    corrections = _user_corrections.get(user_id, [])

    if not corrections:
        return {
            "total_corrections": 0,
            "categories": {},
            "avg_correction_factor": 1.0
        }

    # Group by category
    categories = {}
    for c in corrections:
        food_name = c["food_name"]
        category = categorize_food(food_name)

        if category not in categories:
            categories[category] = {
                "count": 0,
                "avg_factor": 0.0,
                "corrections": []
            }

        categories[category]["count"] += 1
        categories[category]["corrections"].append(c["correction_factor"])

    # Calculate averages
    for category in categories:
        factors = categories[category]["corrections"]
        categories[category]["avg_factor"] = sum(factors) / len(factors)

    # Overall average
    all_factors = [c["correction_factor"] for c in corrections]
    avg_correction_factor = sum(all_factors) / len(all_factors)

    return {
        "total_corrections": len(corrections),
        "categories": categories,
        "avg_correction_factor": avg_correction_factor
    }


# Pre-seed with some general knowledge (from nutrition research)
def _initialize_defaults():
    """Initialize with some general correction patterns"""
    # These are based on common AI over-estimation tendencies

    # Salads often over-estimated (people forget it's mostly water)
    _correction_patterns["salad_greens"] = CorrectionPattern(
        food_category="salad_greens",
        avg_correction_factor=0.6,  # AI tends to over-estimate by ~40%
        correction_count=5,  # Enough to be trusted
        last_updated=datetime.now(),
        confidence=0.5
    )

    # Restaurant items often under-estimated (portions are large)
    _correction_patterns["restaurant_fast_food"] = CorrectionPattern(
        food_category="restaurant_fast_food",
        avg_correction_factor=1.15,  # AI under-estimates by ~15%
        correction_count=5,
        last_updated=datetime.now(),
        confidence=0.5
    )


# Initialize defaults on import
_initialize_defaults()
