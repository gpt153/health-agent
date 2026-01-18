"""
Formula Auto-Suggestion System
Suggests formulas during food logging based on context.

Epic 009 - Phase 3: Food Formulas & Auto-Suggestion
"""
from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, time
from dataclasses import dataclass

from src.db.connection import db
from src.services.formula_detection import get_formula_detection_service
from src.exceptions import ServiceError

logger = logging.getLogger(__name__)


class SuggestionError(ServiceError):
    """Raised when suggestion system fails"""
    pass


@dataclass
class FormulaSuggestion:
    """A formula suggestion with context"""
    formula_id: str
    name: str
    foods: List[Dict]
    total_calories: int
    total_macros: Dict
    confidence: float  # 0.0 to 1.0
    reason: str  # Why this was suggested
    match_method: str  # "keyword", "visual", "combined", "contextual"


class FormulaSuggestionService:
    """
    Intelligent formula suggestion system

    Suggests formulas based on:
    - User's text input
    - Uploaded photo (if available)
    - Time of day (breakfast/lunch/dinner patterns)
    - Recent usage patterns

    Epic 009 - Phase 3: Food Formulas & Auto-Suggestion
    """

    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.80
    AUTO_APPLY_THRESHOLD = 0.95  # Auto-apply if confidence this high

    def __init__(self) -> None:
        """Initialize suggestion service"""
        self.detection_service = get_formula_detection_service()

    async def suggest_formulas(
        self,
        user_id: str,
        text: Optional[str] = None,
        image_path: Optional[str] = None,
        current_time: Optional[datetime] = None,
        max_suggestions: int = 3
    ) -> List[FormulaSuggestion]:
        """
        Get formula suggestions based on available context

        Args:
            user_id: Telegram user ID
            text: User's text input (optional)
            image_path: Food photo path (optional)
            current_time: Timestamp for contextual suggestions
            max_suggestions: Max number of suggestions to return

        Returns:
            List of formula suggestions ranked by confidence

        Raises:
            SuggestionError: If suggestion generation fails
        """
        if current_time is None:
            current_time = datetime.now()

        try:
            suggestions = []

            # Method 1: Combined text + visual matching (highest priority)
            if text or image_path:
                combined_matches = await self.detection_service.find_formulas_combined(
                    user_id=user_id,
                    text=text,
                    image_path=image_path,
                    limit=max_suggestions
                )

                for match in combined_matches:
                    reason = self._generate_reason(match, text, image_path)
                    suggestions.append(FormulaSuggestion(
                        formula_id=match["id"],
                        name=match["name"],
                        foods=match["foods"],
                        total_calories=match["total_calories"],
                        total_macros=match["total_macros"],
                        confidence=match["combined_confidence"],
                        reason=reason,
                        match_method="combined" if (text and image_path) else (
                            "keyword" if text else "visual"
                        )
                    ))

            # Method 2: Contextual suggestions (time-based patterns)
            if len(suggestions) < max_suggestions:
                contextual = await self._get_contextual_suggestions(
                    user_id, current_time, max_suggestions - len(suggestions)
                )
                suggestions.extend(contextual)

            # Sort by confidence
            suggestions.sort(key=lambda s: s.confidence, reverse=True)

            # Limit to max_suggestions
            suggestions = suggestions[:max_suggestions]

            logger.info(
                f"Generated {len(suggestions)} suggestions for user {user_id}"
            )

            return suggestions

        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}", exc_info=True)
            raise SuggestionError(f"Suggestion failed: {e}")

    async def _get_contextual_suggestions(
        self,
        user_id: str,
        current_time: datetime,
        limit: int
    ) -> List[FormulaSuggestion]:
        """
        Get contextual suggestions based on time of day and patterns

        Example: If it's morning and user often has the same breakfast,
        suggest that breakfast formula.
        """
        try:
            # Determine meal time category
            meal_time = self._get_meal_time_category(current_time.time())

            # Find formulas commonly used at this time
            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT
                            ff.id,
                            ff.name,
                            ff.foods,
                            ff.total_calories,
                            ff.total_macros,
                            COUNT(ful.id) as usage_count,
                            MAX(ful.used_at) as last_used
                        FROM food_formulas ff
                        JOIN formula_usage_log ful ON ff.id = ful.formula_id
                        WHERE ff.user_id = %s
                        AND EXTRACT(HOUR FROM ful.used_at) BETWEEN %s AND %s
                        GROUP BY ff.id, ff.name, ff.foods, ff.total_calories, ff.total_macros
                        ORDER BY usage_count DESC, last_used DESC
                        LIMIT %s
                        """,
                        (
                            user_id,
                            meal_time["start_hour"],
                            meal_time["end_hour"],
                            limit
                        )
                    )
                    results = await cur.fetchall()

            suggestions = []
            for row in results:
                # Calculate confidence based on usage frequency at this time
                usage_count = row["usage_count"]
                confidence = min(0.75, 0.5 + (usage_count * 0.05))  # Cap at 0.75

                # Handle JSONB columns
                import json
                foods = row["foods"]
                if isinstance(foods, str):
                    foods = json.loads(foods)

                total_macros = row["total_macros"]
                if isinstance(total_macros, str):
                    total_macros = json.loads(total_macros)

                suggestions.append(FormulaSuggestion(
                    formula_id=str(row["id"]),
                    name=row["name"],
                    foods=foods,
                    total_calories=row["total_calories"],
                    total_macros=total_macros,
                    confidence=confidence,
                    reason=f"You often have this during {meal_time['name']}",
                    match_method="contextual"
                ))

            return suggestions

        except Exception as e:
            logger.warning(f"Contextual suggestions failed: {e}", exc_info=True)
            return []

    def _get_meal_time_category(self, current_time: time) -> Dict[str, Any]:
        """Categorize time into meal periods"""
        hour = current_time.hour

        if 5 <= hour < 11:
            return {"name": "breakfast", "start_hour": 5, "end_hour": 11}
        elif 11 <= hour < 15:
            return {"name": "lunch", "start_hour": 11, "end_hour": 15}
        elif 15 <= hour < 18:
            return {"name": "snack time", "start_hour": 15, "end_hour": 18}
        elif 18 <= hour < 22:
            return {"name": "dinner", "start_hour": 18, "end_hour": 22}
        else:
            return {"name": "late night", "start_hour": 22, "end_hour": 5}

    def _generate_reason(
        self,
        match: Dict[str, Any],
        text: Optional[str],
        image_path: Optional[str]
    ) -> str:
        """Generate human-readable reason for suggestion"""
        reasons = []

        if text and match.get("text_match_score", 0) > 0.7:
            reasons.append("matches your description")

        if image_path and match.get("visual_similarity", 0) > 0.7:
            reasons.append("looks similar to your photo")

        if match.get("times_used", 0) >= 5:
            reasons.append("you've logged this before")

        if not reasons:
            return "similar to your previous meals"

        return " and ".join(reasons).capitalize()

    def should_auto_apply(self, suggestion: FormulaSuggestion) -> bool:
        """Determine if suggestion should be auto-applied"""
        return suggestion.confidence >= self.AUTO_APPLY_THRESHOLD


# Global service instance
_suggestion_service: Optional[FormulaSuggestionService] = None


def get_suggestion_service() -> FormulaSuggestionService:
    """Get or create global suggestion service instance"""
    global _suggestion_service

    if _suggestion_service is None:
        _suggestion_service = FormulaSuggestionService()

    return _suggestion_service
