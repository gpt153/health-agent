"""Parse food descriptions from text into structured data"""
import logging
from typing import Optional
from openai import AsyncOpenAI
import json

from src.config import OPENAI_API_KEY
from src.models.food import FoodItem, FoodMacros
from src.utils.vision import VisionAnalysisResult
from datetime import datetime

logger = logging.getLogger(__name__)


async def parse_food_description(
    description: str,
    quantity: Optional[str] = None,
    user_id: Optional[str] = None
) -> VisionAnalysisResult:
    """
    Parse text description into structured food data.

    Uses LLM to extract foods, quantities, and initial calorie estimates.
    Returns same VisionAnalysisResult format as photo analysis for consistency.

    Args:
        description: User's food description (e.g., "150g chicken breast and salad")
        quantity: Optional quantity override
        user_id: User ID for context (optional)

    Returns:
        VisionAnalysisResult with foods array
    """
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""Extract food items from this description: "{description}"

IMPORTANT:
- Be CONSERVATIVE with calorie estimates (better to underestimate than overestimate)
- If quantity is unclear, use typical serving sizes
- For vague descriptions like "small salad", estimate on the LOWER end
- Break down combined foods (e.g., "chicken and rice" = 2 items)
- Use reasonable portion sizes (e.g., chicken breast = 150g not 300g)

Return valid JSON only:
{{
  "foods": [
    {{
      "name": "food name",
      "quantity": "amount with unit (e.g., 150g, 1 cup)",
      "calories": estimated_calories_number,
      "macros": {{
        "protein": grams,
        "carbs": grams,
        "fat": grams
      }},
      "confidence": "high/medium/low"
    }}
  ],
  "overall_confidence": "high/medium/low",
  "clarifying_questions": ["question if uncertain"]
}}

Examples of GOOD estimates:
- "I ate 170g chicken breast" → {{"name": "Chicken breast (grilled)", "quantity": "170g", "calories": 280, "macros": {{"protein": 52, "carbs": 0, "fat": 6}}}}
- "small salad" → {{"name": "Mixed green salad", "quantity": "1 cup (100g)", "calories": 50, "macros": {{"protein": 2, "carbs": 8, "fat": 1}}}}
- "Chipotle bowl" → Break down into rice, beans, chicken, etc. (ask for details)

Examples of BAD estimates to AVOID:
- "small salad" → 450 cal (TOO HIGH!)
- "chicken breast" → 650 cal (TOO HIGH! unless specified as 300g+)
"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,  # Low temperature for consistency
            max_tokens=800,
            response_format={"type": "json_object"}  # Force JSON output
        )

        content = response.choices[0].message.content.strip()

        # Parse JSON
        data = json.loads(content)

        # Convert to FoodItem objects
        foods = []
        for food_data in data.get("foods", []):
            macros_data = food_data.get("macros", {})

            food_item = FoodItem(
                name=food_data["name"],
                quantity=food_data.get("quantity", "1 serving"),
                calories=int(food_data.get("calories", 0)),
                macros=FoodMacros(
                    protein=float(macros_data.get("protein", 0)),
                    carbs=float(macros_data.get("carbs", 0)),
                    fat=float(macros_data.get("fat", 0))
                ),
                confidence=food_data.get("confidence", "medium"),
                verification_source="ai_text_parse",  # Distinguish from photo AI
                food_category=None  # Will be categorized later
            )
            foods.append(food_item)

        # Build result
        result = VisionAnalysisResult(
            foods=foods,
            confidence=data.get("overall_confidence", "medium"),
            clarifying_questions=data.get("clarifying_questions", []),
            timestamp=datetime.now()
        )

        logger.info(f"Parsed {len(foods)} foods from text: {description[:50]}")
        return result

    except Exception as e:
        logger.error(f"Error parsing food description: {e}", exc_info=True)

        # Return minimal fallback
        fallback_food = FoodItem(
            name=description,
            quantity="1 serving",
            calories=200,  # Conservative estimate
            macros=FoodMacros(protein=10, carbs=20, fat=8),
            confidence="low",
            verification_source="fallback"
        )

        return VisionAnalysisResult(
            foods=[fallback_food],
            confidence="low",
            clarifying_questions=["Could you provide more details about portions?"],
            timestamp=datetime.now()
        )
