"""
Web search integration for nutrition data lookup

Phase 3: Fallback for uncommon foods, restaurant items, and branded products
that are not in the USDA database.
"""
import logging
import re
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import httpx
from pydantic import BaseModel

from src.models.food import FoodItem, FoodMacros
from src.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# Cache for web search results (24 hour TTL)
_web_search_cache: Dict[str, tuple[Dict[Any, Any], datetime]] = {}
CACHE_DURATION = timedelta(hours=24)


class WebNutritionResult(BaseModel):
    """Result from web nutrition search"""
    food_name: str
    calories: int
    protein: float
    carbs: float
    fat: float
    serving_size: str
    source_url: str
    source_name: str
    confidence: float  # 0.0-1.0
    notes: Optional[str] = None


async def search_nutrition_web(
    food_name: str,
    context: Optional[str] = None
) -> List[WebNutritionResult]:
    """
    Search the web for nutrition data.

    Uses DuckDuckGo Instant Answer API (free, no API key needed) and
    trusted nutrition databases.

    Args:
        food_name: Name of food to search
        context: Additional context (brand, restaurant, region)

    Returns:
        List of WebNutritionResult sorted by confidence
    """
    # Check cache first
    cache_key = f"{food_name}:{context or ''}"
    if cache_key in _web_search_cache:
        cached_result, cached_time = _web_search_cache[cache_key]
        if datetime.now() - cached_time < CACHE_DURATION:
            logger.info(f"Using cached web search for '{food_name}'")
            return cached_result

    logger.info(f"Web searching nutrition data for: {food_name}")

    results = []

    try:
        # Strategy 1: Try Nutritionix API (if available)
        nutritionix_result = await _search_nutritionix(food_name, context)
        if nutritionix_result:
            results.append(nutritionix_result)

    except Exception as e:
        logger.warning(f"Nutritionix search failed: {e}")

    try:
        # Strategy 2: Try MyFitnessPal data (scraping)
        mfp_result = await _search_myfitnesspal(food_name, context)
        if mfp_result:
            results.append(mfp_result)

    except Exception as e:
        logger.warning(f"MyFitnessPal search failed: {e}")

    try:
        # Strategy 3: Use AI to extract from general web search
        ai_result = await _search_with_ai(food_name, context)
        if ai_result:
            results.append(ai_result)

    except Exception as e:
        logger.warning(f"AI web search failed: {e}")

    # Cache results
    if results:
        _web_search_cache[cache_key] = (results, datetime.now())

    # Sort by confidence
    results.sort(key=lambda x: x.confidence, reverse=True)

    logger.info(f"Found {len(results)} web nutrition results for '{food_name}'")
    return results


async def _search_nutritionix(
    food_name: str,
    context: Optional[str]
) -> Optional[WebNutritionResult]:
    """
    Search Nutritionix database (free tier available).

    Nutritionix has extensive restaurant and branded food data.
    """
    # For now, return None - can be enabled if user has API key
    # TODO: Add NUTRITIONIX_API_KEY to config
    return None


async def _search_myfitnesspal(
    food_name: str,
    context: Optional[str]
) -> Optional[WebNutritionResult]:
    """
    Search MyFitnessPal database (public data).

    Note: This is a simplified version - real implementation would
    need proper web scraping with rate limiting.
    """
    # For now, return None to avoid rate limiting issues
    # TODO: Implement with proper rate limiting
    return None


async def _search_with_ai(
    food_name: str,
    context: Optional[str]
) -> Optional[WebNutritionResult]:
    """
    Use AI to search web and extract nutrition data.

    This uses a simple HTTP search to get general web data, then
    asks AI to extract nutrition facts from the results.
    """
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)

        # Build search query
        query = f"{food_name} nutrition facts calories protein carbs fat"
        if context:
            query += f" {context}"

        # Use DuckDuckGo Instant Answer API (free, no API key)
        async with httpx.AsyncClient(timeout=5.0) as http_client:
            response = await http_client.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_html": 1,
                    "skip_disambig": 1
                }
            )
            search_data = response.json()

        # Extract relevant text
        text_snippets = []

        # Abstract
        if search_data.get("Abstract"):
            text_snippets.append(search_data["Abstract"])

        # Related topics
        for topic in search_data.get("RelatedTopics", [])[:3]:
            if isinstance(topic, dict) and topic.get("Text"):
                text_snippets.append(topic["Text"])

        if not text_snippets:
            logger.warning("No web search results found")
            return None

        # Ask AI to extract nutrition data
        prompt = f"""Extract nutrition information for "{food_name}" from these web search results:

{chr(10).join(text_snippets[:3])}

If the text contains nutrition facts, extract:
- Calories (per serving)
- Protein (grams)
- Carbs (grams)
- Fat (grams)
- Serving size

Respond in JSON format:
{{
  "found": true/false,
  "calories": number or null,
  "protein": number or null,
  "carbs": number or null,
  "fat": number or null,
  "serving_size": "description" or null,
  "confidence": 0.0-1.0,
  "notes": "any important notes"
}}

If no clear nutrition data found, return {{"found": false}}
"""

        ai_response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"}
        )

        result_json = json.loads(ai_response.choices[0].message.content)

        if not result_json.get("found"):
            return None

        # Build result
        return WebNutritionResult(
            food_name=food_name,
            calories=int(result_json.get("calories", 0)),
            protein=float(result_json.get("protein", 0)),
            carbs=float(result_json.get("carbs", 0)),
            fat=float(result_json.get("fat", 0)),
            serving_size=result_json.get("serving_size", "1 serving"),
            source_url="https://duckduckgo.com",
            source_name="Web Search (DuckDuckGo)",
            confidence=float(result_json.get("confidence", 0.5)),
            notes=result_json.get("notes")
        )

    except Exception as e:
        logger.error(f"AI web search error: {e}", exc_info=True)
        return None


async def verify_with_web_search(
    food_item: FoodItem,
    usda_failed: bool = False
) -> Optional[FoodItem]:
    """
    Verify food item using web search as fallback.

    Args:
        food_item: Food item to verify
        usda_failed: Whether USDA search already failed

    Returns:
        Updated FoodItem with web-sourced data or None
    """
    # Only use web search if USDA failed
    if not usda_failed:
        return None

    logger.info(f"Attempting web search verification for '{food_item.name}'")

    # Extract context from food name (e.g., brand, restaurant)
    context = _extract_context(food_item.name)

    # Search web
    results = await search_nutrition_web(food_item.name, context)

    if not results:
        logger.warning(f"No web results found for '{food_item.name}'")
        return None

    # Use highest confidence result
    best_result = results[0]

    if best_result.confidence < 0.4:
        logger.warning(f"Web result confidence too low: {best_result.confidence}")
        return None

    # Parse serving size to scale nutrients
    # (Simple version - assumes serving sizes match)
    scale_factor = 1.0  # TODO: Better serving size parsing

    # Create verified food item
    verified_item = FoodItem(
        name=food_item.name,
        quantity=best_result.serving_size,
        calories=int(best_result.calories * scale_factor),
        macros=FoodMacros(
            protein=best_result.protein * scale_factor,
            carbs=best_result.carbs * scale_factor,
            fat=best_result.fat * scale_factor
        ),
        verification_source=f"web:{best_result.source_name}",
        confidence_score=best_result.confidence,
        food_category=None
    )

    logger.info(f"Web verified '{food_item.name}': {verified_item.calories} cal "
                f"(source: {best_result.source_name}, confidence: {best_result.confidence:.2f})")

    return verified_item


def _extract_context(food_name: str) -> Optional[str]:
    """Extract context (brand, restaurant) from food name"""
    # Common restaurant chains
    restaurants = [
        "chipotle", "mcdonalds", "burger king", "subway", "starbucks",
        "panera", "chick-fil-a", "taco bell", "wendys", "kfc",
        "pizza hut", "dominos", "papa johns"
    ]

    food_lower = food_name.lower()

    for restaurant in restaurants:
        if restaurant in food_lower:
            return restaurant

    # Common brands
    brands = [
        "quest", "clif", "kind", "rxbar", "lara", "nature valley",
        "gatorade", "powerade", "muscle milk", "optimum nutrition"
    ]

    for brand in brands:
        if brand in food_lower:
            return brand

    return None


def get_trusted_sources() -> List[str]:
    """Get list of trusted nutrition data sources"""
    return [
        "usda.gov",
        "nutritionix.com",
        "myfitnesspal.com",
        "cronometer.com",
        "fatsecret.com",
        # Restaurant official sites
        "chipotle.com",
        "mcdonalds.com",
        "starbucks.com",
        # Brand official sites (examples)
        "questnutrition.com",
        "clifbar.com"
    ]
