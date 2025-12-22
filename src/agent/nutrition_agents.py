"""Multi-agent nutrition estimation system with debate mechanism

This module implements Phase 2 of the nutrition accuracy improvement plan,
introducing coordinated agents that debate estimates when variance is detected.

Architecture:
- Agent A: Vision AI (analyzes photos)
- Agent B: USDA Database (verified nutritional data)
- Agent C: Validation Rules (reasonableness checks)
- Moderator: Synthesizes debate and produces consensus
"""

import logging
from typing import List, Dict, Optional, Tuple
from src.models.food import FoodItem, FoodMacros
from src.utils.nutrition_validation import validate_nutrition_estimate
from src.utils.nutrition_search import verify_food_items
from src.utils.estimate_comparison import compare_estimates

logger = logging.getLogger(__name__)


class NutritionAgentCoordinator:
    """
    Coordinates multiple agents for nutrition estimation.

    Manages the workflow:
    1. Run all agents in parallel
    2. Compare estimates
    3. If variance > threshold, initiate debate
    4. Return consensus
    """

    def __init__(
        self,
        variance_threshold: float = 0.30,  # 30% variance triggers debate
        max_debate_rounds: int = 2,
        enable_debate: bool = True
    ):
        """
        Initialize coordinator.

        Args:
            variance_threshold: Variance percentage that triggers debate
            max_debate_rounds: Maximum rounds of debate
            enable_debate: Whether to enable debate mechanism
        """
        self.variance_threshold = variance_threshold
        self.max_debate_rounds = max_debate_rounds
        self.enable_debate = enable_debate

        logger.info(
            f"Nutrition coordinator initialized: "
            f"variance_threshold={variance_threshold:.1%}, "
            f"max_rounds={max_debate_rounds}, "
            f"debate={'enabled' if enable_debate else 'disabled'}"
        )

    async def estimate_with_coordination(
        self,
        vision_foods: List[FoodItem],
        food_name: str,
        quantity: str
    ) -> Tuple[FoodItem, Dict]:
        """
        Coordinate agents to produce final estimate.

        Args:
            vision_foods: Food items from vision AI
            food_name: Name of food being analyzed
            quantity: Quantity string

        Returns:
            Tuple of (final_food_item, metadata_dict)
            metadata contains all estimates, variance, confidence, debate_log
        """
        logger.info(f"Coordinating agents for: {food_name} ({quantity})")

        # Prepare metadata
        metadata = {
            "food_name": food_name,
            "quantity": quantity,
            "agent_estimates": [],
            "variance": 0.0,
            "requires_debate": False,
            "debate_rounds": 0,
            "debate_log": [],
            "final_source": "unknown"
        }

        # Step 1: Get estimate from Agent A (Vision AI)
        vision_food = vision_foods[0] if vision_foods else None
        if not vision_food:
            logger.error("No vision AI estimate available")
            raise ValueError("Vision AI estimate required")

        agent_a_estimate = {
            "agent": "vision_ai",
            "source": "vision_ai",
            "calories": vision_food.calories,
            "macros": {
                "protein": vision_food.macros.protein,
                "carbs": vision_food.macros.carbs,
                "fat": vision_food.macros.fat
            },
            "reasoning": "Analyzed from photo using computer vision"
        }
        metadata["agent_estimates"].append(agent_a_estimate)

        logger.debug(f"Agent A (Vision): {vision_food.calories} kcal")

        # Step 2: Get estimate from Agent B (USDA)
        usda_foods = await verify_food_items(vision_foods)
        usda_food = usda_foods[0] if usda_foods else vision_food

        if usda_food.verification_source == "usda":
            agent_b_estimate = {
                "agent": "usda_database",
                "source": "usda",
                "calories": usda_food.calories,
                "macros": {
                    "protein": usda_food.macros.protein,
                    "carbs": usda_food.macros.carbs,
                    "fat": usda_food.macros.fat
                },
                "reasoning": "Retrieved from USDA FoodData Central database",
                "confidence": usda_food.confidence_score or 0.9
            }
            metadata["agent_estimates"].append(agent_b_estimate)
            logger.debug(f"Agent B (USDA): {usda_food.calories} kcal")
        else:
            logger.debug("Agent B (USDA): No match found, using AI estimate")

        # Step 3: Get estimate from Agent C (Validation)
        validation = validate_nutrition_estimate(
            food_name=food_name,
            quantity=quantity,
            calories=vision_food.calories,
            protein=vision_food.macros.protein,
            carbs=vision_food.macros.carbs,
            fat=vision_food.macros.fat
        )

        agent_c_estimate = {
            "agent": "validation_rules",
            "source": "validation",
            "calories": validation.get("suggested_calories") or vision_food.calories,
            "macros": {
                "protein": vision_food.macros.protein,
                "carbs": vision_food.macros.carbs,
                "fat": vision_food.macros.fat
            },
            "reasoning": validation.get("reasoning", "Validation rules applied"),
            "confidence": validation.get("confidence", 0.5),
            "is_valid": validation.get("is_valid", True),
            "issues": validation.get("issues", [])
        }
        metadata["agent_estimates"].append(agent_c_estimate)
        logger.debug(f"Agent C (Validation): {agent_c_estimate['calories']} kcal (valid: {validation['is_valid']})")

        # Step 4: Compare estimates
        estimates_for_comparison = [
            {"source": est["source"], "calories": est["calories"]}
            for est in metadata["agent_estimates"]
        ]

        comparison = compare_estimates(
            estimates_for_comparison,
            variance_threshold=self.variance_threshold
        )

        metadata["variance"] = comparison["variance"]
        metadata["requires_debate"] = comparison["requires_debate"]

        logger.info(
            f"Variance: {comparison['variance']:.1%}, "
            f"Debate required: {comparison['requires_debate']}"
        )

        # Step 5: Debate if needed
        if comparison["requires_debate"] and self.enable_debate:
            logger.info("High variance detected, initiating debate...")

            final_estimate, debate_log = await self._run_debate(
                agent_a_estimate,
                agent_b_estimate if len(metadata["agent_estimates"]) > 2 else None,
                agent_c_estimate,
                comparison
            )

            metadata["debate_rounds"] = len(debate_log)
            metadata["debate_log"] = debate_log
            metadata["final_source"] = "debate_consensus"

        else:
            # No debate needed, use comparison consensus
            logger.info("Low variance, using weighted consensus without debate")

            final_estimate = {
                "calories": comparison["consensus"],
                "macros": usda_food.macros if usda_food.verification_source == "usda" else vision_food.macros,
                "confidence": comparison["confidence"],
                "source": "consensus"
            }
            metadata["final_source"] = "weighted_consensus"

        # Step 6: Build final FoodItem
        final_food = FoodItem(
            name=food_name,
            quantity=quantity,
            calories=final_estimate["calories"],
            macros=final_estimate["macros"],
            verification_source=metadata["final_source"],
            confidence_score=final_estimate.get("confidence", comparison["confidence"])
        )

        logger.info(
            f"Final estimate: {final_food.calories} kcal "
            f"(confidence: {final_food.confidence_score:.1%}, "
            f"source: {final_food.verification_source})"
        )

        return final_food, metadata

    async def _run_debate(
        self,
        agent_a: Dict,
        agent_b: Optional[Dict],
        agent_c: Dict,
        comparison: Dict
    ) -> Tuple[Dict, List[Dict]]:
        """
        Run debate between agents to reach consensus.

        Args:
            agent_a: Vision AI estimate
            agent_b: USDA estimate (optional)
            agent_c: Validation estimate
            comparison: Comparison results

        Returns:
            Tuple of (final_estimate, debate_log)
        """
        from src.agent.nutrition_debate import run_debate_rounds

        # Prepare agents for debate
        agents = [agent_a, agent_c]
        if agent_b:
            agents.append(agent_b)

        # Run debate
        debate_result = await run_debate_rounds(
            agents=agents,
            comparison=comparison,
            max_rounds=self.max_debate_rounds
        )

        return debate_result["final_estimate"], debate_result["debate_log"]


# Example usage
if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.DEBUG)

    async def test_coordinator():
        """Test the coordinator with a problematic case"""

        print("\n" + "="*60)
        print("MULTI-AGENT COORDINATOR TEST")
        print("="*60)

        # Simulate the user's small salad case
        from src.models.food import FoodItem, FoodMacros

        vision_estimate = FoodItem(
            name="small salad",
            quantity="small",
            calories=450,  # AI's bad estimate
            macros=FoodMacros(protein=5, carbs=10, fat=35)
        )

        coordinator = NutritionAgentCoordinator(
            variance_threshold=0.30,
            max_debate_rounds=2,
            enable_debate=True
        )

        final_food, metadata = await coordinator.estimate_with_coordination(
            vision_foods=[vision_estimate],
            food_name="small salad",
            quantity="small"
        )

        print("\nAgent Estimates:")
        for est in metadata["agent_estimates"]:
            print(f"  {est['agent']}: {est['calories']} kcal - {est['reasoning']}")

        print(f"\nVariance: {metadata['variance']:.1%}")
        print(f"Debate required: {metadata['requires_debate']}")
        print(f"Debate rounds: {metadata['debate_rounds']}")

        print(f"\nFinal Estimate:")
        print(f"  Calories: {final_food.calories} kcal")
        print(f"  Confidence: {final_food.confidence_score:.1%}")
        print(f"  Source: {final_food.verification_source}")

        print("\n" + "="*60)
        print("TEST COMPLETE")
        print("="*60)

    # Run test
    asyncio.run(test_coordinator())
