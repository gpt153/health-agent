"""Vision AI integration for food photo analysis"""
import logging
import base64
import json
import time
from typing import Optional
from pathlib import Path
from src.config import VISION_MODEL, OPENAI_API_KEY, ANTHROPIC_API_KEY
from src.models.food import VisionAnalysisResult, FoodItem, FoodMacros
from src.resilience.circuit_breaker import (
    with_circuit_breaker,
    OPENAI_BREAKER,
    ANTHROPIC_BREAKER,
)
from src.resilience.retry import with_retry
from src.resilience.fallback import execute_with_fallbacks, FallbackStrategy
from src.resilience.metrics import record_api_call

logger = logging.getLogger(__name__)


async def analyze_food_photo(
    photo_path: str,
    caption: Optional[str] = None,
    user_id: Optional[str] = None,
    visual_patterns: Optional[str] = None,
    semantic_context: Optional[str] = None,
    food_history: Optional[str] = None,
    food_habits: Optional[str] = None
) -> VisionAnalysisResult:
    """
    Analyze food photo using vision AI with enhanced personalization and resilience.

    Uses circuit breaker pattern and fallback strategies to ensure reliable operation
    even when primary vision API is unavailable.

    Fallback chain:
    1. Primary vision model (from config)
    2. Alternative vision model (opposite of primary)
    3. Mock result (always succeeds)

    Args:
        photo_path: Path to the food photo
        caption: Optional caption provided by user
        user_id: User's ID for loading visual patterns
        visual_patterns: Pre-loaded visual patterns (optional, for performance)
        semantic_context: Relevant memories from Mem0 semantic search
        food_history: Recent food logging patterns
        food_habits: User's established food preparation habits

    Returns:
        VisionAnalysisResult with identified foods
    """
    logger.info(f"Analyzing food photo: {photo_path} with model {VISION_MODEL}")
    if caption:
        logger.info(f"User caption: {caption}")

    # Read and encode image
    with open(photo_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')

    # Prepare arguments for handlers
    handler_args = {
        "image_data": image_data,
        "photo_path": photo_path,
        "caption": caption,
        "visual_patterns": visual_patterns,
        "semantic_context": semantic_context,
        "food_history": food_history,
        "food_habits": food_habits,
    }

    # Define fallback strategies based on primary model
    if VISION_MODEL.startswith("openai:"):
        strategies = [
            FallbackStrategy(
                name="openai_vision",
                handler=lambda **kwargs: _analyze_openai_protected(**kwargs),
                priority=1
            ),
            FallbackStrategy(
                name="anthropic_vision",
                handler=lambda **kwargs: _analyze_anthropic_protected(**kwargs),
                priority=2
            ),
            FallbackStrategy(
                name="mock_fallback",
                handler=lambda **kwargs: _get_mock_result_async(),
                priority=3
            )
        ]
    elif VISION_MODEL.startswith("anthropic:"):
        strategies = [
            FallbackStrategy(
                name="anthropic_vision",
                handler=lambda **kwargs: _analyze_anthropic_protected(**kwargs),
                priority=1
            ),
            FallbackStrategy(
                name="openai_vision",
                handler=lambda **kwargs: _analyze_openai_protected(**kwargs),
                priority=2
            ),
            FallbackStrategy(
                name="mock_fallback",
                handler=lambda **kwargs: _get_mock_result_async(),
                priority=3
            )
        ]
    else:
        logger.error(f"Unknown vision model: {VISION_MODEL}, using mock fallback")
        return _get_mock_result()

    # Execute with fallback strategies
    return await execute_with_fallbacks(strategies, **handler_args)


@with_circuit_breaker(OPENAI_BREAKER)
@with_retry(max_retries=3)
async def _analyze_openai_protected(
    image_data: str,
    photo_path: str,
    caption: Optional[str] = None,
    visual_patterns: Optional[str] = None,
    semantic_context: Optional[str] = None,
    food_history: Optional[str] = None,
    food_habits: Optional[str] = None
) -> VisionAnalysisResult:
    """
    OpenAI vision call protected by circuit breaker and retry logic.

    Wraps analyze_with_openai with resilience patterns and metrics.
    """
    start_time = time.time()
    try:
        result = await analyze_with_openai(
            image_data, photo_path, caption, visual_patterns,
            semantic_context, food_history, food_habits
        )
        duration = time.time() - start_time
        record_api_call("openai", success=True, duration=duration)
        return result
    except Exception as e:
        duration = time.time() - start_time
        record_api_call("openai", success=False, duration=duration)
        raise


@with_circuit_breaker(ANTHROPIC_BREAKER)
@with_retry(max_retries=3)
async def _analyze_anthropic_protected(
    image_data: str,
    photo_path: str,
    caption: Optional[str] = None,
    visual_patterns: Optional[str] = None,
    semantic_context: Optional[str] = None,
    food_history: Optional[str] = None,
    food_habits: Optional[str] = None
) -> VisionAnalysisResult:
    """
    Anthropic vision call protected by circuit breaker and retry logic.

    Wraps analyze_with_anthropic with resilience patterns and metrics.
    """
    start_time = time.time()
    try:
        result = await analyze_with_anthropic(
            image_data, photo_path, caption, visual_patterns,
            semantic_context, food_history, food_habits
        )
        duration = time.time() - start_time
        record_api_call("anthropic", success=True, duration=duration)
        return result
    except Exception as e:
        duration = time.time() - start_time
        record_api_call("anthropic", success=False, duration=duration)
        raise


async def _get_mock_result_async() -> VisionAnalysisResult:
    """Async wrapper for mock result (always succeeds)"""
    return _get_mock_result()


async def analyze_with_openai(
    image_data: str,
    photo_path: str,
    caption: Optional[str] = None,
    visual_patterns: Optional[str] = None,
    semantic_context: Optional[str] = None,
    food_history: Optional[str] = None,
    food_habits: Optional[str] = None
) -> VisionAnalysisResult:
    """Use OpenAI Vision API (GPT-4o-mini)"""
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)

        # Get model name from config (e.g., "openai:gpt-4o-mini" -> "gpt-4o-mini")
        model_name = VISION_MODEL.split(":", 1)[1] if ":" in VISION_MODEL else "gpt-4o-mini"

        # Determine image format from file extension
        file_ext = Path(photo_path).suffix.lower()
        media_type = "image/jpeg" if file_ext in [".jpg", ".jpeg"] else "image/png"

        # Build prompt with caption and visual patterns
        if caption:
            prompt_text = f"""CRITICAL INSTRUCTIONS - READ CAREFULLY:

The user provided this description: "{caption}"

**This description is the ABSOLUTE TRUTH. Use it exactly as written.**

LANGUAGE HANDLING:
- The caption may be in ANY language (English, Swedish, Spanish, etc.)
- Translate food names to English for the response
- Common Swedish foods: "kvarg" = quark, "keso" = cottage cheese, "fil" = filmjölk/soured milk

QUANTITY RULES - EXTREMELY IMPORTANT:
- If the user specifies grams (e.g., "170g"), use EXACTLY that amount
- If they say "2 eggs", log EXACTLY 2 eggs
- If they list multiple items, log ALL of them separately
- NEVER estimate or guess quantities when the user provided exact amounts

Analyze this food photo and return a JSON response with:
1. foods: Array of food items with:
   - name: Food name in English
   - quantity: EXACT quantity from user's description (e.g., "170g", "2 eggs")
   - calories: Accurate estimate based on EXACT quantity
   - macros: protein, carbs, fat in grams (accurate for the EXACT quantity)

2. confidence: "high" (if caption is detailed), "medium", or "low"
3. clarifying_questions: Only if critical information is missing

TIME/DATE EXTRACTION:
- If the caption mentions WHEN the food was eaten (e.g., "yesterday", "igår", "at 11pm", "kl23"), extract this
- Common phrases: "yesterday"/"igår" = previous day, "kl" = time (Swedish), "at" = time marker
- Return as "timestamp" in ISO format if mentioned, or null if not

EXAMPLE 1:
Caption: "170g kvarg and 170g keso"
Response: {{"foods": [...], "confidence": "high", "timestamp": null}}

EXAMPLE 2:
Caption: "Igår kl23 åt jag 170g kvarg och 170g keso"
Response: {{"foods": [...], "confidence": "high", "timestamp": "2024-12-14T23:00:00"}}"""
        else:
            prompt_text = """Analyze this food photo and return a JSON response with:
1. foods: Array of food items with name, quantity (estimate), calories (estimate), and macros (protein, carbs, fat in grams)
2. confidence: "high", "medium", or "low"
3. clarifying_questions: Array of questions to improve accuracy

Be specific about portion sizes and provide nutritional estimates."""

        if visual_patterns:
            prompt_text += f"\n\nUser's known food patterns:\n{visual_patterns}\nCheck if this matches any known items."

        # Add enhanced context for personalization
        if semantic_context:
            prompt_text += f"\n{semantic_context}"

        if food_history:
            prompt_text += f"\n{food_history}"

        if food_habits:
            prompt_text += f"\n{food_habits}\nAuto-apply these habits when recognizing matching foods."

        # Prepare vision prompt
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt_text
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

        # Parse timestamp if provided
        from datetime import datetime
        timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except (ValueError, TypeError):
                logger.warning(f"Failed to parse timestamp: {data.get('timestamp')}")

        return VisionAnalysisResult(
            foods=foods,
            confidence=data.get("confidence", "medium"),
            clarifying_questions=data.get("clarifying_questions", []),
            timestamp=timestamp
        )

    except Exception as e:
        logger.error(f"OpenAI Vision error: {e}", exc_info=True)
        return _get_mock_result()


async def analyze_with_anthropic(
    image_data: str,
    photo_path: str,
    caption: Optional[str] = None,
    visual_patterns: Optional[str] = None,
    semantic_context: Optional[str] = None,
    food_history: Optional[str] = None,
    food_habits: Optional[str] = None
) -> VisionAnalysisResult:
    """Use Anthropic Claude 3.5 Sonnet Vision"""
    try:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

        # Get model name from config (e.g., "anthropic:claude-3-5-sonnet-latest" -> "claude-3-5-sonnet-latest")
        model_name = VISION_MODEL.split(":", 1)[1] if ":" in VISION_MODEL else "claude-3-5-sonnet-latest"

        # Determine image format from file extension
        file_ext = Path(photo_path).suffix.lower()
        media_type = "image/jpeg" if file_ext in [".jpg", ".jpeg"] else "image/png"

        # Build prompt with caption and visual patterns
        if caption:
            prompt_text = f"""CRITICAL INSTRUCTIONS - READ CAREFULLY:

The user provided this description: "{caption}"

**This description is the ABSOLUTE TRUTH. Use it exactly as written.**

LANGUAGE HANDLING:
- The caption may be in ANY language (English, Swedish, Spanish, etc.)
- Translate food names to English for the response
- Common Swedish foods: "kvarg" = quark, "keso" = cottage cheese, "fil" = filmjölk/soured milk

QUANTITY RULES - EXTREMELY IMPORTANT:
- If the user specifies grams (e.g., "170g"), use EXACTLY that amount
- If they say "2 eggs", log EXACTLY 2 eggs
- If they list multiple items, log ALL of them separately
- NEVER estimate or guess quantities when the user provided exact amounts

Analyze this food photo and return a JSON response with:
1. foods: Array of food items with:
   - name: Food name in English
   - quantity: EXACT quantity from user's description (e.g., "170g", "2 eggs")
   - calories: Accurate estimate based on EXACT quantity
   - macros: protein, carbs, fat in grams (accurate for the EXACT quantity)

2. confidence: "high" (if caption is detailed), "medium", or "low"
3. clarifying_questions: Only if critical information is missing

TIME/DATE EXTRACTION:
- If the caption mentions WHEN the food was eaten (e.g., "yesterday", "igår", "at 11pm", "kl23"), extract this
- Common phrases: "yesterday"/"igår" = previous day, "kl" = time (Swedish), "at" = time marker
- Return as "timestamp" in ISO format if mentioned, or null if not

EXAMPLE 1:
Caption: "170g kvarg and 170g keso"
Response: {{"foods": [...], "confidence": "high", "timestamp": null}}

EXAMPLE 2:
Caption: "Igår kl23 åt jag 170g kvarg och 170g keso"
Response: {{"foods": [...], "confidence": "high", "timestamp": "2024-12-14T23:00:00"}}"""
        else:
            prompt_text = """Analyze this food photo and return a JSON response with:
1. foods: Array of food items with name, quantity (estimate), calories (estimate), and macros (protein, carbs, fat in grams)
2. confidence: "high", "medium", or "low"
3. clarifying_questions: Array of questions to improve accuracy

Be specific about portion sizes and provide nutritional estimates."""

        if visual_patterns:
            prompt_text += f"\n\nUser's known food patterns:\n{visual_patterns}\nCheck if this matches any known items."

        # Add enhanced context for personalization
        if semantic_context:
            prompt_text += f"\n{semantic_context}"

        if food_history:
            prompt_text += f"\n{food_history}"

        if food_habits:
            prompt_text += f"\n{food_habits}\nAuto-apply these habits when recognizing matching foods."

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
                            "text": prompt_text
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

        # Parse timestamp if provided
        from datetime import datetime
        timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except (ValueError, TypeError):
                logger.warning(f"Failed to parse timestamp: {data.get('timestamp')}")

        return VisionAnalysisResult(
            foods=foods,
            confidence=data.get("confidence", "medium"),
            clarifying_questions=data.get("clarifying_questions", []),
            timestamp=timestamp
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
