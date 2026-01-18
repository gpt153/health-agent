"""
PydanticAI tools for memory system integration.
Epic 009 - Phase 7: Integration & Agent Tools

This module provides agent tools for accessing the visual memory system,
food formulas, and health pattern insights built in Phases 1-6.
"""
from __future__ import annotations

from pydantic_ai import RunContext
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime, timedelta
import logging

if TYPE_CHECKING:
    from src.agent import AgentDeps

from src.services.visual_food_search import get_visual_search_service
from src.services.formula_detection import get_formula_detection_service
from src.services.pattern_detection import get_user_patterns

logger = logging.getLogger(__name__)


class MemoryResult(BaseModel):
    """Result of memory tool operations"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    matches: Optional[List[Dict]] = None
    confidence: Optional[float] = None


async def search_food_images(
    ctx: RunContext[AgentDeps],
    image_path: Optional[str] = None,
    text_description: Optional[str] = None,
    limit: int = 3
) -> MemoryResult:
    """
    Search user's food history for visually similar items

    This tool leverages Phase 1's visual reference system to find meals
    that look similar to a query image. Perfect for:
    - "What did I eat?" questions
    - "When did I last have this?" queries
    - Auto-suggestion during food logging

    Args:
        image_path: Path to query image (from photo upload)
        text_description: Optional text context for hybrid search
        limit: Max results to return (default: 3)

    Returns:
        MemoryResult with matching food entries + metadata

    Example:
        User sends photo of protein shake
        → Finds 3 similar shakes from history
        → Returns with dates, nutrition, confidence scores
    """
    try:
        # Require at least image_path
        if not image_path:
            return MemoryResult(
                success=False,
                message="Please provide an image to search for similar meals."
            )

        # Get visual search service
        visual_service = get_visual_search_service()

        # Search for visually similar foods
        logger.info(f"Searching for similar foods: {image_path}")
        similar_foods = await visual_service.find_similar_foods(
            user_id=ctx.deps.telegram_id,
            query_image_path=image_path,
            limit=limit,
            min_similarity=0.70  # 70% minimum similarity
        )

        if not similar_foods:
            return MemoryResult(
                success=True,
                message="I couldn't find any similar meals in your history yet. "
                        "As you log more meals with photos, I'll be able to recognize them!",
                matches=[]
            )

        # Format results for user
        message = f"Found {len(similar_foods)} similar meal(s) in your history:\n\n"

        matches = []
        for i, match in enumerate(similar_foods, 1):
            # Calculate days ago
            days_ago = (datetime.now() - match.created_at).days
            time_str = "today" if days_ago == 0 else f"{days_ago} day{'s' if days_ago > 1 else ''} ago"

            # Format confidence
            confidence_pct = int(match.similarity_score * 100)
            confidence_emoji = "🎯" if match.confidence_level == "high" else "✓"

            message += f"{i}. {confidence_emoji} **{confidence_pct}% match** - {time_str}\n"

            # Store match data
            matches.append({
                "food_entry_id": match.food_entry_id,
                "photo_path": match.photo_path,
                "similarity_score": match.similarity_score,
                "confidence_level": match.confidence_level,
                "created_at": match.created_at.isoformat(),
                "days_ago": days_ago
            })

        # Add helpful context
        if similar_foods[0].confidence_level == "high":
            message += "\n💡 The top match has high confidence. This might be a recurring meal!"

        return MemoryResult(
            success=True,
            message=message,
            matches=matches,
            confidence=similar_foods[0].similarity_score
        )

    except Exception as e:
        logger.error(f"Visual search failed: {e}", exc_info=True)
        return MemoryResult(
            success=False,
            message=f"Failed to search similar images: {str(e)}"
        )


async def get_food_formula(
    ctx: RunContext[AgentDeps],
    keyword: Optional[str] = None,
    image_path: Optional[str] = None,
    auto_suggest: bool = True
) -> MemoryResult:
    """
    Retrieve user's formulas by keyword or image

    This tool leverages Phase 3's formula system to find saved meal templates.
    Perfect for:
    - "I had my shake" → auto-match to saved formula
    - Photo-based formula matching
    - Auto-suggestion during meal logging

    Args:
        keyword: Search keyword (fuzzy matching enabled)
        image_path: Photo for visual formula matching
        auto_suggest: Enable context-based auto-suggestion (time of day, usage patterns)

    Returns:
        MemoryResult with matched formulas + confidence

    Example:
        User: "I had my shake"
        → Searches formulas for "shake"
        → Finds "Banana Protein Shake" (used 15 times)
        → Returns with full nutrition data
    """
    try:
        # Require at least keyword or image
        if not keyword and not image_path:
            return MemoryResult(
                success=False,
                message="Please provide a keyword or image to search for formulas."
            )

        formula_service = get_formula_detection_service()

        # Use combined search if both provided, otherwise single-mode
        if keyword and image_path:
            logger.info(f"Combined formula search: keyword='{keyword}', image={image_path}")
            formulas = await formula_service.find_formulas_combined(
                user_id=ctx.deps.telegram_id,
                text=keyword,
                image_path=image_path,
                limit=5
            )
        elif keyword:
            logger.info(f"Keyword formula search: '{keyword}'")
            formulas = await formula_service.find_formulas_by_keyword(
                user_id=ctx.deps.telegram_id,
                keyword=keyword,
                limit=5
            )
        else:  # image_path only
            logger.info(f"Visual formula search: {image_path}")
            formulas = await formula_service.find_formulas_by_image(
                user_id=ctx.deps.telegram_id,
                image_path=image_path,
                limit=5
            )

        if not formulas:
            return MemoryResult(
                success=False,
                message=f"No formulas found matching '{keyword or 'this image'}'. "
                        "Would you like to create a formula for this meal?"
            )

        # Apply auto-suggestion logic if enabled
        if auto_suggest and formulas:
            formulas = _apply_auto_suggestion_boost(formulas)

        # Format top match
        top_match = formulas[0]
        confidence = top_match.get("combined_confidence") or top_match.get("match_score", 0)

        # Build response message
        if confidence >= 0.85:
            # High confidence - suggest auto-logging
            message = f"🎯 This looks like your **{top_match['name']}**!\n\n"
            message += f"📊 {top_match['total_calories']} kcal\n"

            # Show macros if available
            if top_match.get('total_macros'):
                macros = top_match['total_macros']
                message += f"🔸 Protein: {macros.get('protein', 0)}g | "
                message += f"Carbs: {macros.get('carbs', 0)}g | "
                message += f"Fat: {macros.get('fat', 0)}g\n"

            message += f"✨ Used {top_match['times_used']} times before\n"
            message += f"\nShould I log this formula for you?"

        else:
            # Multiple suggestions
            message = f"💡 Found {len(formulas)} matching formula(s):\n\n"
            for i, formula in enumerate(formulas[:3], 1):
                conf_pct = int((formula.get('combined_confidence') or formula.get('match_score', 0)) * 100)
                message += f"{i}. **{formula['name']}** ({conf_pct}% match)\n"
                message += f"   {formula['total_calories']} kcal | Used {formula['times_used']} times\n\n"

            message += "Would you like to use one of these?"

        return MemoryResult(
            success=True,
            message=message,
            matches=formulas,
            confidence=confidence,
            data={
                "top_match": top_match,
                "total_matches": len(formulas)
            }
        )

    except Exception as e:
        logger.error(f"Formula search failed: {e}", exc_info=True)
        return MemoryResult(
            success=False,
            message=f"Failed to search formulas: {str(e)}"
        )


async def get_health_patterns(
    ctx: RunContext[AgentDeps],
    query: Optional[str] = None,
    pattern_types: Optional[List[str]] = None,
    min_confidence: float = 0.70,
    min_impact: float = 50.0,
    limit: int = 5
) -> MemoryResult:
    """
    Retrieve discovered health patterns

    This tool leverages Phase 6's pattern detection system to surface
    AI-discovered insights. Perfect for:
    - "Why am I tired today?" → surface relevant patterns
    - Proactive coaching: "I've noticed a pattern..."
    - Pattern browsing: "What patterns have you found?"

    Args:
        query: Natural language query (for semantic matching)
        pattern_types: Filter by type (temporal_correlation, multifactor, etc.)
        min_confidence: Minimum pattern confidence (0.0-1.0, default: 0.70)
        min_impact: Minimum impact score (0-100, default: 50)
        limit: Max patterns to return (default: 5)

    Returns:
        MemoryResult with patterns + actionable insights

    Example:
        User: "Why am I tired?"
        → Retrieves patterns related to energy/tiredness
        → Finds: "Low energy after pasta + poor sleep" (85% confidence)
        → Returns actionable insight
    """
    try:
        logger.info(
            f"Searching patterns: query='{query}', types={pattern_types}, "
            f"min_confidence={min_confidence}, min_impact={min_impact}"
        )

        # Get patterns from database
        patterns = await get_user_patterns(
            user_id=ctx.deps.telegram_id,
            min_confidence=min_confidence,
            min_impact=min_impact,
            include_archived=False
        )

        if not patterns:
            return MemoryResult(
                success=True,
                message="I haven't discovered any significant patterns in your data yet. "
                        "As you log more meals, sleep, and symptoms, I'll start detecting patterns!",
                matches=[]
            )

        # Filter by pattern type if specified
        if pattern_types:
            patterns = [p for p in patterns if p['pattern_type'] in pattern_types]

        # Apply relevance scoring if query provided
        if query:
            patterns = _score_pattern_relevance(patterns, query, ctx)

        # Sort by relevance/impact
        patterns.sort(key=lambda p: (
            p.get('relevance_score', 0),
            p['impact_score'] or 0,
            p['confidence']
        ), reverse=True)

        # Limit results
        patterns = patterns[:limit]

        if not patterns:
            return MemoryResult(
                success=True,
                message=f"No patterns found matching your criteria.",
                matches=[]
            )

        # Format response
        if len(patterns) == 1:
            # Single high-relevance pattern
            pattern = patterns[0]
            message = "🔍 **I've noticed a pattern in your data:**\n\n"
            message += pattern['actionable_insight'] + "\n\n"
            message += f"📊 Confidence: {int(pattern['confidence'] * 100)}%\n"
            message += f"📈 Impact: {'High' if pattern['impact_score'] >= 70 else 'Medium'} "
            message += f"({pattern['impact_score']:.0f}/100)\n"
            message += f"📅 Observed: {pattern['occurrences']} times\n\n"
            message += "💬 Was this insight helpful?\n[Helpful] [Not Helpful]"

        else:
            # Multiple patterns
            message = f"📊 Found {len(patterns)} relevant pattern(s):\n\n"
            for i, pattern in enumerate(patterns[:3], 1):
                message += f"{i}. **{_get_pattern_title(pattern)}**\n"
                message += f"   {pattern['actionable_insight'][:100]}...\n"
                message += f"   Confidence: {int(pattern['confidence'] * 100)}% | "
                message += f"Impact: {pattern['impact_score']:.0f}/100\n\n"

            message += "Want to know more about any of these patterns?"

        return MemoryResult(
            success=True,
            message=message,
            matches=patterns,
            confidence=patterns[0]['confidence'] if patterns else 0,
            data={
                "total_patterns": len(patterns),
                "high_impact_count": sum(1 for p in patterns if p['impact_score'] >= 70)
            }
        )

    except Exception as e:
        logger.error(f"Pattern retrieval failed: {e}", exc_info=True)
        return MemoryResult(
            success=False,
            message=f"Failed to retrieve patterns: {str(e)}"
        )


# ================================================================
# Helper Functions
# ================================================================

def _apply_auto_suggestion_boost(formulas: List[Dict]) -> List[Dict]:
    """
    Apply context-based boosting to formula matches

    Boosts scores based on:
    - Time of day (breakfast/lunch/dinner patterns)
    - Usage frequency
    - Recency
    """
    current_hour = datetime.now().hour

    for formula in formulas:
        boost_multiplier = 1.0

        # Time-based boosting
        # Breakfast (6-10 AM)
        if 6 <= current_hour < 10:
            if any(kw in formula.get('keywords', []) for kw in ['breakfast', 'morning', 'coffee']):
                boost_multiplier *= 1.2

        # Lunch (11 AM - 2 PM)
        elif 11 <= current_hour <= 14:
            if any(kw in formula.get('keywords', []) for kw in ['lunch', 'sandwich', 'salad']):
                boost_multiplier *= 1.2

        # Dinner (5 PM - 9 PM)
        elif 17 <= current_hour <= 21:
            if any(kw in formula.get('keywords', []) for kw in ['dinner', 'evening']):
                boost_multiplier *= 1.2

        # Frequency boosting (formulas used often)
        times_used = formula.get('times_used', 0)
        if times_used > 10:
            boost_multiplier *= 1.1
        elif times_used > 20:
            boost_multiplier *= 1.15

        # Apply boost to confidence
        original_confidence = formula.get('combined_confidence') or formula.get('match_score', 0)
        boosted_confidence = min(original_confidence * boost_multiplier, 1.0)

        formula['combined_confidence'] = boosted_confidence
        formula['boost_applied'] = boost_multiplier > 1.0

    # Re-sort by boosted confidence
    formulas.sort(key=lambda f: f.get('combined_confidence', 0), reverse=True)

    return formulas


def _score_pattern_relevance(
    patterns: List[Dict],
    query: str,
    ctx: RunContext[AgentDeps]
) -> List[Dict]:
    """
    Score pattern relevance to current context

    Factors:
    - Semantic match to query
    - Temporal match (pattern applicable now?)
    - Contextual match (recent events match pattern triggers?)
    - Recency (pattern observed recently?)
    """
    query_lower = query.lower()

    for pattern in patterns:
        relevance = 0.0

        # Semantic match (simple keyword matching for now)
        insight = pattern.get('actionable_insight', '').lower()
        pattern_rule = pattern.get('pattern_rule', {})

        # Check if query keywords appear in insight
        query_words = set(query_lower.split())
        insight_words = set(insight.split())
        overlap = len(query_words & insight_words)
        if overlap > 0:
            relevance += 30 * (overlap / len(query_words))

        # Check for symptom/outcome matching
        if pattern['pattern_type'] == 'temporal_correlation':
            outcome = pattern_rule.get('outcome', {}).get('characteristic', '')
            if any(word in outcome.lower() for word in query_words):
                relevance += 40

        # Recency bonus
        updated_at = pattern.get('updated_at')
        if updated_at:
            days_since = (datetime.now() - updated_at).days
            if days_since <= 7:
                relevance += 20
            elif days_since <= 30:
                relevance += 10

        # Impact bonus
        if pattern.get('impact_score', 0) >= 70:
            relevance += 10

        pattern['relevance_score'] = min(relevance, 100.0)

    return patterns


def _get_pattern_title(pattern: Dict) -> str:
    """Generate a concise title for a pattern"""
    pattern_type = pattern['pattern_type']

    if pattern_type == 'temporal_correlation':
        rule = pattern['pattern_rule']
        trigger = rule.get('trigger', {}).get('characteristic', 'event')
        outcome = rule.get('outcome', {}).get('characteristic', 'outcome')
        return f"{trigger.replace('_', ' ').title()} → {outcome.replace('_', ' ').title()}"

    elif pattern_type == 'multifactor_pattern':
        factors = pattern['pattern_rule'].get('factors', [])
        if len(factors) >= 2:
            return f"{len(factors)}-Factor Pattern"

    elif pattern_type == 'behavioral_sequence':
        return "Behavioral Sequence"

    elif pattern_type == 'cyclical_pattern':
        cycle = pattern['pattern_rule'].get('cycle', 'temporal')
        return f"{cycle.title()} Pattern"

    return pattern_type.replace('_', ' ').title()
