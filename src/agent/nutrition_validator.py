"""
Multi-Agent Nutrition Validator

Implements cross-model validation and reasonableness checking to prevent
unrealistic calorie/macro estimates from vision AI.
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from src.models.food import FoodItem, VisionAnalysisResult, FoodMacros
from src.utils.reasonableness_rules import validate_food_items, check_reasonableness
from src.config import VISION_MODEL, OPENAI_API_KEY, ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)


class NutritionValidator:
    """
    Multi-agent validator for nutrition estimates.

    Performs:
    1. Cross-model validation (compare OpenAI vs Anthropic)
    2. Reasonableness checks against known ranges
    3. USDA comparison (if available)
    """

    def __init__(self):
        self.primary_model = VISION_MODEL
        # Determine secondary model for cross-validation
        if VISION_MODEL.startswith("openai:"):
            self.secondary_model = "anthropic:claude-3-5-sonnet-latest"
        else:
            self.secondary_model = "openai:gpt-4o-mini"

    async def validate_with_cross_model(
        self,
        primary_result: VisionAnalysisResult,
        photo_path: str,
        caption: Optional[str] = None,
        visual_patterns: Optional[str] = None
    ) -> Tuple[VisionAnalysisResult, List[str]]:
        """
        Validate primary vision result with a secondary model.

        Args:
            primary_result: Result from primary vision model
            photo_path: Path to food photo
            caption: User caption
            visual_patterns: User's visual patterns

        Returns:
            Tuple of (validated_result, warnings)
        """
        warnings = []

        # Only do cross-validation if we have both API keys
        has_openai = OPENAI_API_KEY and OPENAI_API_KEY != "your-openai-api-key-here"
        has_anthropic = ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "your-anthropic-api-key-here"

        if not (has_openai and has_anthropic):
            logger.info("Cross-model validation skipped: missing API keys")
            return primary_result, warnings

        # Get secondary analysis
        try:
            from src.utils.vision import analyze_with_openai, analyze_with_anthropic
            import base64

            # Read image
            with open(photo_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # Call secondary model
            if self.secondary_model.startswith("openai:"):
                secondary_result = await analyze_with_openai(
                    image_data, photo_path, caption, visual_patterns
                )
            else:
                secondary_result = await analyze_with_anthropic(
                    image_data, photo_path, caption, visual_patterns
                )

            # Compare results
            comparison_warnings = self._compare_results(primary_result, secondary_result)
            warnings.extend(comparison_warnings)

            # If significant discrepancy, blend the results
            if len(comparison_warnings) > 0:
                logger.info("Significant discrepancy detected, blending results")
                blended_result = self._blend_results(primary_result, secondary_result)
                return blended_result, warnings

        except Exception as e:
            logger.error(f"Cross-model validation error: {e}", exc_info=True)
            warnings.append("⚠️ Cross-model validation failed, using single model result")

        return primary_result, warnings

    def _compare_results(
        self,
        result1: VisionAnalysisResult,
        result2: VisionAnalysisResult
    ) -> List[str]:
        """
        Compare two vision analysis results for discrepancies.

        Args:
            result1: First analysis result
            result2: Second analysis result

        Returns:
            List of warning messages
        """
        warnings = []

        # Compare total calories
        total_cal_1 = sum(food.calories for food in result1.foods)
        total_cal_2 = sum(food.calories for food in result2.foods)

        if total_cal_1 > 0 and total_cal_2 > 0:
            cal_diff_percent = abs(total_cal_1 - total_cal_2) / max(total_cal_1, total_cal_2) * 100

            if cal_diff_percent > 20:  # More than 20% difference
                warnings.append(
                    f"⚠️ Cross-model disagreement: Model 1 estimates {total_cal_1} cal, "
                    f"Model 2 estimates {total_cal_2} cal ({cal_diff_percent:.0f}% difference)"
                )

        # Compare individual foods if same count
        if len(result1.foods) == len(result2.foods):
            for i, (food1, food2) in enumerate(zip(result1.foods, result2.foods)):
                if food1.calories > 0 and food2.calories > 0:
                    item_diff_percent = abs(food1.calories - food2.calories) / max(food1.calories, food2.calories) * 100

                    if item_diff_percent > 30:  # More than 30% difference per item
                        warnings.append(
                            f"⚠️ '{food1.name}': Model 1 says {food1.calories} cal, "
                            f"Model 2 says {food2.calories} cal ({item_diff_percent:.0f}% difference)"
                        )

        return warnings

    def _blend_results(
        self,
        result1: VisionAnalysisResult,
        result2: VisionAnalysisResult
    ) -> VisionAnalysisResult:
        """
        Blend two vision results by averaging their estimates.

        Args:
            result1: First result
            result2: Second result

        Returns:
            Blended VisionAnalysisResult
        """
        # If different number of foods, use the primary (result1)
        if len(result1.foods) != len(result2.foods):
            logger.warning("Cannot blend results with different food counts, using primary")
            return result1

        blended_foods = []

        for food1, food2 in zip(result1.foods, result2.foods):
            # Average calories and macros
            blended_calories = int((food1.calories + food2.calories) / 2)
            blended_macros = FoodMacros(
                protein=(food1.macros.protein + food2.macros.protein) / 2,
                carbs=(food1.macros.carbs + food2.macros.carbs) / 2,
                fat=(food1.macros.fat + food2.macros.fat) / 2
            )

            blended_food = FoodItem(
                name=food1.name,  # Use primary name
                quantity=food1.quantity,  # Use primary quantity
                calories=blended_calories,
                macros=blended_macros
            )

            blended_foods.append(blended_food)

        return VisionAnalysisResult(
            foods=blended_foods,
            confidence="medium",  # Blended results have medium confidence
            clarifying_questions=result1.clarifying_questions + result2.clarifying_questions,
            timestamp=result1.timestamp
        )

    async def validate(
        self,
        vision_result: VisionAnalysisResult,
        photo_path: str,
        caption: Optional[str] = None,
        visual_patterns: Optional[str] = None,
        usda_verified_items: Optional[List[FoodItem]] = None,
        enable_cross_validation: bool = True
    ) -> Tuple[VisionAnalysisResult, List[str]]:
        """
        Comprehensive validation of vision analysis results.

        Args:
            vision_result: Primary vision analysis result
            photo_path: Path to food photo
            caption: User caption
            visual_patterns: User's visual patterns
            usda_verified_items: USDA-verified items (if available)
            enable_cross_validation: Whether to perform cross-model validation

        Returns:
            Tuple of (validated_result, all_warnings)
        """
        all_warnings = []

        # Step 1: Cross-model validation (if enabled)
        if enable_cross_validation:
            vision_result, cross_warnings = await self.validate_with_cross_model(
                vision_result, photo_path, caption, visual_patterns
            )
            all_warnings.extend(cross_warnings)

        # Step 2: Reasonableness checks
        _, reasonableness_warnings = validate_food_items(vision_result.foods)
        all_warnings.extend(reasonableness_warnings)

        # Step 3: USDA comparison (if available)
        if usda_verified_items:
            usda_warnings = self._compare_with_usda(vision_result.foods, usda_verified_items)
            all_warnings.extend(usda_warnings)

        # Step 4: Determine if we should flag for review
        if len(all_warnings) >= 3:
            all_warnings.append(
                "🚨 MULTIPLE VALIDATION ISSUES DETECTED. Please review these estimates carefully."
            )

        # Log validation results
        if all_warnings:
            logger.warning(f"Validation found {len(all_warnings)} issues: {all_warnings}")
        else:
            logger.info("Validation passed: all estimates appear reasonable")

        return vision_result, all_warnings

    def _compare_with_usda(
        self,
        ai_foods: List[FoodItem],
        usda_foods: List[FoodItem]
    ) -> List[str]:
        """
        Compare AI estimates with USDA verified data.

        Args:
            ai_foods: Foods from vision AI
            usda_foods: Foods verified by USDA

        Returns:
            List of warning messages
        """
        warnings = []

        if len(ai_foods) != len(usda_foods):
            return warnings  # Can't compare if different counts

        for ai_food, usda_food in zip(ai_foods, usda_foods):
            # Only compare if USDA has high confidence
            if hasattr(usda_food, 'confidence_score') and usda_food.confidence_score < 0.7:
                continue

            # Compare calories
            if ai_food.calories > 0 and usda_food.calories > 0:
                cal_diff_percent = abs(ai_food.calories - usda_food.calories) / usda_food.calories * 100

                if cal_diff_percent > 25:  # More than 25% difference
                    warnings.append(
                        f"⚠️ '{ai_food.name}': AI estimates {ai_food.calories} cal, "
                        f"but USDA data suggests {usda_food.calories} cal ({cal_diff_percent:.0f}% difference)"
                    )

        return warnings


# Singleton instance
_validator_instance = None


def get_validator() -> NutritionValidator:
    """Get singleton validator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = NutritionValidator()
    return _validator_instance
