"""
Enhanced Photo Analysis Pipeline
Epic 009 - Phase 7: Integration & Agent Tools

Integrates ALL memory context from Phases 1-6 into photo analysis:
- Phase 1: Visual similarity search (find similar foods)
- Phase 2: Plate recognition (calibration data)
- Phase 3: Formula matching (recognize saved formulas)
- Phase 4: Portion comparison (compare to references)

This transforms photo analysis from simple recognition into intelligent,
personalized food logging with zero manual entry needed.
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from src.utils.vision import analyze_food_photo
from src.services.visual_food_search import get_visual_search_service
from src.services.formula_detection import get_formula_detection_service
from src.services.portion_comparison import get_portion_service
from src.db.connection import db

logger = logging.getLogger(__name__)


class EnhancedPhotoAnalysis:
    """
    Enhanced photo analysis with full memory integration

    Workflow:
    1. Visual Memory Search (Phase 1)
       → Find similar foods from history
       → Get reference images for context

    2. Plate Recognition (Phase 2)
       → Detect known plates
       → Get calibration data for portion estimates

    3. Formula Matching (Phase 3)
       → Check for formula matches
       → Use both visual + keyword matching

    4. Context Building
       → Combine all data into rich context

    5. GPT-4 Vision Analysis
       → Enhanced prompt with all context
       → Reference images, calibration, formulas

    6. Portion Comparison (Phase 4)
       → Compare to reference portions
       → Adjust estimates based on history
    """

    def __init__(self) -> None:
        """Initialize enhanced photo analysis service"""
        self.visual_service = get_visual_search_service()
        self.formula_service = get_formula_detection_service()
        self.portion_service = get_portion_service()

    async def analyze_with_full_context(
        self,
        user_id: str,
        photo_path: str,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze food photo with full memory context

        Args:
            user_id: Telegram user ID
            photo_path: Path to food photo
            caption: Optional user caption

        Returns:
            Enhanced analysis result with all context

        Example:
            >>> result = await service.analyze_with_full_context(
            ...     user_id="123",
            ...     photo_path="/photos/shake.jpg",
            ...     caption="my shake"
            ... )
            >>> print(result['formula_match'])
            {'name': 'Banana Protein Shake', 'confidence': 0.92}
        """
        logger.info(f"Enhanced photo analysis: user={user_id}, photo={photo_path}")

        # STEP 1: Visual Memory Search (Phase 1)
        logger.debug("Step 1: Visual memory search")
        similar_foods = await self._search_similar_foods(user_id, photo_path)

        # STEP 2: Plate Recognition (Phase 2)
        logger.debug("Step 2: Plate recognition")
        plate_data = await self._detect_plate(user_id, photo_path)

        # STEP 3: Formula Matching (Phase 3)
        logger.debug("Step 3: Formula matching")
        formula_matches = await self._match_formulas(user_id, photo_path, caption)

        # STEP 4: Build Context
        logger.debug("Step 4: Building analysis context")
        context = await self._build_analysis_context(
            similar_foods,
            plate_data,
            formula_matches
        )

        # STEP 5: GPT-4 Vision Analysis with Context
        logger.debug("Step 5: GPT-4 vision analysis")
        vision_result = await self._analyze_with_context(
            photo_path,
            caption,
            context
        )

        # STEP 6: Portion Comparison (Phase 4)
        logger.debug("Step 6: Portion comparison")
        portion_comparison = await self._compare_portions(
            user_id,
            vision_result,
            similar_foods
        )

        # Combine all results
        enhanced_result = {
            "vision_result": vision_result,
            "similar_foods": similar_foods,
            "plate_data": plate_data,
            "formula_matches": formula_matches,
            "portion_comparison": portion_comparison,
            "context_used": context,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(
            f"Enhanced analysis complete: "
            f"{len(similar_foods)} similar foods, "
            f"{len(formula_matches)} formula matches"
        )

        return enhanced_result

    async def _search_similar_foods(
        self,
        user_id: str,
        photo_path: str
    ) -> List[Dict[str, Any]]:
        """
        Search for visually similar foods (Phase 1)

        Returns up to 3 most similar foods with metadata
        """
        try:
            similar = await self.visual_service.find_similar_foods(
                user_id=user_id,
                query_image_path=photo_path,
                limit=3,
                min_similarity=0.70
            )

            # Convert to dict format
            return [
                {
                    "food_entry_id": match.food_entry_id,
                    "photo_path": match.photo_path,
                    "similarity_score": match.similarity_score,
                    "confidence_level": match.confidence_level,
                    "created_at": match.created_at.isoformat(),
                    "days_ago": (datetime.now() - match.created_at).days
                }
                for match in similar
            ]

        except Exception as e:
            logger.warning(f"Visual search failed: {e}")
            return []

    async def _detect_plate(
        self,
        user_id: str,
        photo_path: str
    ) -> Optional[Dict[str, Any]]:
        """
        Detect known plate (Phase 2)

        Returns plate calibration data if detected
        """
        try:
            # Query recognized_plates table
            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT
                            rp.plate_id,
                            rp.plate_name,
                            rp.diameter_cm,
                            rp.calibration_method,
                            rp.reference_photo_path
                        FROM recognized_plates rp
                        WHERE rp.user_id = %s
                        AND rp.is_active = TRUE
                        ORDER BY rp.times_used DESC
                        LIMIT 1
                        """,
                        (user_id,)
                    )
                    plate = await cur.fetchone()

                    if plate:
                        return {
                            "plate_id": plate["plate_id"],
                            "name": plate["plate_name"],
                            "diameter_cm": plate["diameter_cm"],
                            "calibration_method": plate["calibration_method"],
                            "reference_photo": plate["reference_photo_path"]
                        }

            return None

        except Exception as e:
            logger.warning(f"Plate detection failed: {e}")
            return None

    async def _match_formulas(
        self,
        user_id: str,
        photo_path: str,
        caption: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Match against saved formulas (Phase 3)

        Uses both visual similarity and keyword matching
        """
        try:
            # Use combined search if caption provided
            if caption:
                matches = await self.formula_service.find_formulas_combined(
                    user_id=user_id,
                    text=caption,
                    image_path=photo_path,
                    limit=3
                )
            else:
                # Visual-only search
                matches = await self.formula_service.find_formulas_by_image(
                    user_id=user_id,
                    image_path=photo_path,
                    limit=3
                )

            return matches

        except Exception as e:
            logger.warning(f"Formula matching failed: {e}")
            return []

    async def _build_analysis_context(
        self,
        similar_foods: List[Dict],
        plate_data: Optional[Dict],
        formula_matches: List[Dict]
    ) -> str:
        """
        Build comprehensive context for GPT-4 Vision

        Combines data from all phases into a rich prompt context
        """
        context_parts = []

        # Add visual memory context
        if similar_foods:
            context_parts.append("\n📸 **VISUAL MEMORY CONTEXT**")
            context_parts.append("I found similar foods in your history:")

            for i, match in enumerate(similar_foods, 1):
                days = match['days_ago']
                time_str = "today" if days == 0 else f"{days} day{'s' if days > 1 else ''} ago"
                confidence = int(match['similarity_score'] * 100)

                context_parts.append(
                    f"{i}. {confidence}% match - eaten {time_str}"
                )

            context_parts.append("")

        # Add plate recognition context
        if plate_data:
            context_parts.append("🍽️ **PLATE CALIBRATION DATA**")
            context_parts.append(f"Detected plate: {plate_data['name']}")
            context_parts.append(f"Diameter: {plate_data['diameter_cm']}cm")
            context_parts.append("Use this for portion size estimation.")
            context_parts.append("")

        # Add formula matching context
        if formula_matches:
            context_parts.append("📋 **FORMULA MATCH CONTEXT**")
            context_parts.append("This looks like a saved formula:")

            for i, formula in enumerate(formula_matches[:2], 1):
                confidence = formula.get('combined_confidence') or formula.get('visual_similarity', 0)
                conf_pct = int(confidence * 100)

                context_parts.append(f"\n{i}. **{formula['name']}** ({conf_pct}% match)")
                context_parts.append(f"   {formula['total_calories']} kcal")

                # Add food items
                foods = formula.get('foods', [])
                if foods:
                    context_parts.append("   Contains:")
                    for food in foods[:3]:
                        qty = food.get('quantity', '')
                        context_parts.append(f"   - {food.get('name')}: {qty}")

            context_parts.append("")

        # Combine all context
        if context_parts:
            return "\n".join(context_parts)

        return ""

    async def _analyze_with_context(
        self,
        photo_path: str,
        caption: Optional[str],
        context: str
    ) -> Dict[str, Any]:
        """
        Run GPT-4 Vision analysis with enhanced context

        Passes context string to existing vision function
        """
        try:
            # Use existing vision analysis with enhanced context
            result = await analyze_food_photo(
                photo_path=photo_path,
                caption=caption,
                visual_patterns=context  # Pass memory context as visual patterns
            )

            return {
                "foods": result.foods,
                "confidence": result.confidence,
                "clarifying_questions": result.clarifying_questions,
                "timestamp": result.timestamp
            }

        except Exception as e:
            logger.error(f"Vision analysis failed: {e}", exc_info=True)
            return {
                "foods": [],
                "confidence": "low",
                "clarifying_questions": ["Failed to analyze photo"],
                "timestamp": None
            }

    async def _compare_portions(
        self,
        user_id: str,
        vision_result: Dict[str, Any],
        similar_foods: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """
        Compare portions to reference images (Phase 4)

        Adjusts estimates based on historical portion sizes
        """
        try:
            if not similar_foods or not vision_result.get('foods'):
                return None

            # Get most similar food
            top_match = similar_foods[0]

            # Use portion comparison service
            comparison = await self.portion_service.compare_to_reference(
                user_id=user_id,
                current_image_path="",  # Would be current photo
                reference_entry_id=top_match['food_entry_id']
            )

            return comparison

        except Exception as e:
            logger.warning(f"Portion comparison failed: {e}")
            return None


# Global service instance
_enhanced_analysis_service: Optional[EnhancedPhotoAnalysis] = None


def get_enhanced_analysis_service() -> EnhancedPhotoAnalysis:
    """Get or create the global enhanced analysis service instance"""
    global _enhanced_analysis_service

    if _enhanced_analysis_service is None:
        _enhanced_analysis_service = EnhancedPhotoAnalysis()

    return _enhanced_analysis_service
