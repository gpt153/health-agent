"""Vision AI integration for food photo analysis"""
import logging
import base64
import json
from typing import Optional
from pathlib import Path
from src.config import VISION_MODEL, OPENAI_API_KEY, ANTHROPIC_API_KEY
from src.models.food import VisionAnalysisResult, FoodItem, FoodMacros

logger = logging.getLogger(__name__)


async def analyze_food_photo(photo_path: str) -> VisionAnalysisResult:
    """
    Analyze food photo using vision AI

    Args:
        photo_path: Path to the food photo

    Returns:
        VisionAnalysisResult with identified foods
    """
    logger.info(f"Analyzing food photo: {photo_path} with model {VISION_MODEL}")

    # Read and encode image
    with open(photo_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')

    # Route to appropriate vision API
    if VISION_MODEL.startswith("openai:"):
        return await analyze_with_openai(image_data, photo_path)
    elif VISION_MODEL.startswith("anthropic:"):
        return await analyze_with_anthropic(image_data, photo_path)
    else:
        logger.error(f"Unknown vision model: {VISION_MODEL}")
        # Fallback to mock data
        return _get_mock_result()


async def analyze_with_openai(image_data: str, photo_path: str) -> VisionAnalysisResult:
    """Use OpenAI Vision API (GPT-4o-mini)"""
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)

        # Get model name from config (e.g., "openai:gpt-4o-mini" -> "gpt-4o-mini")
        model_name = VISION_MODEL.split(":", 1)[1] if ":" in VISION_MODEL else "gpt-4o-mini"

        # Determine image format from file extension
        file_ext = Path(photo_path).suffix.lower()
        media_type = "image/jpeg" if file_ext in [".jpg", ".jpeg"] else "image/png"

        # Prepare vision prompt
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Analyze this food photo and return a JSON response with:
1. foods: Array of food items with name, quantity (estimate), calories (estimate), and macros (protein, carbs, fat in grams)
2. confidence: "high", "medium", or "low"
3. clarifying_questions: Array of questions to improve accuracy

Be specific about portion sizes and provide nutritional estimates."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )

        # Parse response
        content = response.choices[0].message.content
        logger.info(f"OpenAI Vision response: {content}")

        # Extract JSON from response (may be wrapped in markdown code blocks)
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content.strip()

        data = json.loads(json_str)

        # Convert to our models
        foods = [
            FoodItem(
                name=item["name"],
                quantity=item["quantity"],
                calories=item["calories"],
                macros=FoodMacros(
                    protein=item["macros"]["protein"],
                    carbs=item["macros"]["carbs"],
                    fat=item["macros"]["fat"]
                )
            )
            for item in data.get("foods", [])
        ]

        return VisionAnalysisResult(
            foods=foods,
            confidence=data.get("confidence", "medium"),
            clarifying_questions=data.get("clarifying_questions", [])
        )

    except Exception as e:
        logger.error(f"OpenAI Vision error: {e}", exc_info=True)
        return _get_mock_result()


async def analyze_with_anthropic(image_data: str, photo_path: str) -> VisionAnalysisResult:
    """Use Anthropic Claude 3.5 Sonnet Vision"""
    try:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

        # Get model name from config (e.g., "anthropic:claude-3-5-sonnet-latest" -> "claude-3-5-sonnet-latest")
        model_name = VISION_MODEL.split(":", 1)[1] if ":" in VISION_MODEL else "claude-3-5-sonnet-latest"

        # Determine image format from file extension
        file_ext = Path(photo_path).suffix.lower()
        media_type = "image/jpeg" if file_ext in [".jpg", ".jpeg"] else "image/png"

        # Prepare vision prompt
        response = await client.messages.create(
            model=model_name,
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": """Analyze this food photo and return a JSON response with:
1. foods: Array of food items with name, quantity (estimate), calories (estimate), and macros (protein, carbs, fat in grams)
2. confidence: "high", "medium", or "low"
3. clarifying_questions: Array of questions to improve accuracy

Be specific about portion sizes and provide nutritional estimates."""
                        }
                    ]
                }
            ]
        )

        # Parse response
        content = response.content[0].text
        logger.info(f"Anthropic Vision response: {content}")

        # Extract JSON from response (may be wrapped in markdown code blocks)
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content.strip()

        data = json.loads(json_str)

        # Convert to our models
        foods = [
            FoodItem(
                name=item["name"],
                quantity=item["quantity"],
                calories=item["calories"],
                macros=FoodMacros(
                    protein=item["macros"]["protein"],
                    carbs=item["macros"]["carbs"],
                    fat=item["macros"]["fat"]
                )
            )
            for item in data.get("foods", [])
        ]

        return VisionAnalysisResult(
            foods=foods,
            confidence=data.get("confidence", "medium"),
            clarifying_questions=data.get("clarifying_questions", [])
        )

    except Exception as e:
        logger.error(f"Anthropic Vision error: {e}", exc_info=True)
        return _get_mock_result()


def _get_mock_result() -> VisionAnalysisResult:
    """Fallback mock result if API calls fail"""
    logger.warning("Using mock vision analysis as fallback")

    mock_foods = [
        FoodItem(
            name="Food Item",
            quantity="1 serving",
            calories=300,
            macros=FoodMacros(protein=20.0, carbs=30.0, fat=10.0)
        )
    ]

    return VisionAnalysisResult(
        foods=mock_foods,
        confidence="low",
        clarifying_questions=["Could you describe what's in the photo?"]
    )
