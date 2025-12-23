"""
Multi-Agent Nutrition Consensus System

Implements 3-agent validation with voting and explanations:
- Agent 1: OpenAI GPT-4o-mini (vision analysis)
- Agent 2: Anthropic Claude 3.5 Sonnet (vision analysis)
- Agent 3: Validator Agent (reasonableness checking & consensus)

Phase 2 of food accuracy improvements (Issue #28)
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field
from datetime import datetime

from src.models.food import FoodItem, VisionAnalysisResult, FoodMacros
from src.config import OPENAI_API_KEY, ANTHROPIC_API_KEY, AGENT_MODEL
from src.utils.reasonableness_rules import validate_food_items

logger = logging.getLogger(__name__)


class AgentEstimate(BaseModel):
    """Estimate from a single agent"""
    agent_name: str  # "openai", "anthropic", "validator"
    foods: List[FoodItem]
    total_calories: int
    confidence: str  # high/medium/low
    reasoning: Optional[str] = None


class ConsensusResult(BaseModel):
    """Result of multi-agent consensus"""
    final_foods: List[FoodItem]
    total_calories: int
    total_macros: FoodMacros
    agreement_level: str  # "high", "medium", "low"
    confidence_score: float  # 0.0-1.0
    agent_estimates: List[AgentEstimate]
    consensus_explanation: str
    discrepancies: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarifying_questions: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class NutritionConsensusEngine:
    """
    3-agent consensus system for nutrition validation.

    Workflow:
    1. Get estimates from OpenAI vision model
    2. Get estimates from Anthropic vision model
    3. Compare results with validator agent
    4. Determine consensus level (high/medium/low)
    5. Blend results or request clarification
    6. Provide explanation to user
    """

    def __init__(self):
        self.validator_model = AGENT_MODEL  # Claude 3.5 Sonnet for validation

    async def get_consensus(
        self,
        photo_path: Optional[str] = None,
        image_data: Optional[str] = None,
        caption: Optional[str] = None,
        visual_patterns: Optional[str] = None,
        parsed_text_result: Optional[VisionAnalysisResult] = None
    ) -> ConsensusResult:
        """
        Get multi-agent consensus on food nutrition estimate.

        Works for both:
        - Photo analysis (provide photo_path or image_data)
        - Text parsing (provide parsed_text_result)

        Args:
            photo_path: Path to food photo (for photo analysis)
            image_data: Base64 encoded image (for photo analysis)
            caption: User caption/description
            visual_patterns: User's visual eating patterns
            parsed_text_result: Pre-parsed text result (for text analysis)

        Returns:
            ConsensusResult with final estimate and consensus details
        """
        agent_estimates = []

        try:
            # Photo analysis: get estimates from both vision models
            if photo_path or image_data:
                logger.info("Getting consensus for photo-based food entry")

                # Ensure we have image data
                if not image_data and photo_path:
                    import base64
                    with open(photo_path, "rb") as f:
                        image_data = base64.b64encode(f.read()).decode('utf-8')

                # Agent 1: OpenAI
                openai_estimate = await self._get_openai_estimate(
                    image_data, photo_path, caption, visual_patterns
                )
                agent_estimates.append(openai_estimate)

                # Agent 2: Anthropic
                anthropic_estimate = await self._get_anthropic_estimate(
                    image_data, photo_path, caption, visual_patterns
                )
                agent_estimates.append(anthropic_estimate)

            # Text analysis: use parsed result as first estimate, get second opinion
            elif parsed_text_result:
                logger.info("Getting consensus for text-based food entry")

                # Agent 1: Pre-parsed text result (from GPT-4o-mini)
                text_estimate = AgentEstimate(
                    agent_name="openai_text_parser",
                    foods=parsed_text_result.foods,
                    total_calories=sum(f.calories for f in parsed_text_result.foods),
                    confidence=parsed_text_result.confidence,
                    reasoning="Initial text parsing with conservative estimates"
                )
                agent_estimates.append(text_estimate)

                # Agent 2: Get second opinion from Anthropic on text description
                anthropic_text_estimate = await self._get_anthropic_text_estimate(
                    caption or "food description",
                    visual_patterns
                )
                agent_estimates.append(anthropic_text_estimate)

            else:
                raise ValueError("Must provide either photo data or parsed_text_result")

            # Agent 3: Validator agent analyzes both estimates
            validator_analysis = await self._validate_with_agent(
                agent_estimates[0],
                agent_estimates[1],
                photo_path,
                caption
            )

            # Determine consensus
            consensus = await self._determine_consensus(
                agent_estimates,
                validator_analysis
            )

            logger.info(f"Consensus achieved: {consensus.agreement_level} agreement, "
                       f"confidence {consensus.confidence_score:.2f}")

            return consensus

        except Exception as e:
            logger.error(f"Error in consensus engine: {e}", exc_info=True)

            # Fallback: return first estimate with warnings
            if agent_estimates:
                return self._create_fallback_consensus(agent_estimates[0], str(e))
            else:
                raise

    async def _get_openai_estimate(
        self,
        image_data: str,
        photo_path: Optional[str],
        caption: Optional[str],
        visual_patterns: Optional[str]
    ) -> AgentEstimate:
        """Get nutrition estimate from OpenAI vision model"""
        try:
            from src.utils.vision import analyze_with_openai

            result = await analyze_with_openai(
                image_data, photo_path, caption, visual_patterns
            )

            return AgentEstimate(
                agent_name="openai_gpt4o_mini",
                foods=result.foods,
                total_calories=sum(f.calories for f in result.foods),
                confidence=result.confidence,
                reasoning="OpenAI vision analysis"
            )

        except Exception as e:
            logger.error(f"OpenAI estimate error: {e}")
            raise

    async def _get_anthropic_estimate(
        self,
        image_data: str,
        photo_path: Optional[str],
        caption: Optional[str],
        visual_patterns: Optional[str]
    ) -> AgentEstimate:
        """Get nutrition estimate from Anthropic vision model"""
        try:
            from src.utils.vision import analyze_with_anthropic

            result = await analyze_with_anthropic(
                image_data, photo_path, caption, visual_patterns
            )

            return AgentEstimate(
                agent_name="anthropic_claude_3_5_sonnet",
                foods=result.foods,
                total_calories=sum(f.calories for f in result.foods),
                confidence=result.confidence,
                reasoning="Anthropic vision analysis"
            )

        except Exception as e:
            logger.error(f"Anthropic estimate error: {e}")
            raise

    async def _get_anthropic_text_estimate(
        self,
        food_description: str,
        visual_patterns: Optional[str]
    ) -> AgentEstimate:
        """Get second opinion from Anthropic for text-based food entry"""
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

            prompt = f"""Analyze this food description and provide a conservative nutrition estimate.

Food description: "{food_description}"

User eating patterns (context): {visual_patterns or "Unknown"}

IMPORTANT:
- Be CONSERVATIVE with estimates (better to underestimate than overestimate)
- Use typical portion sizes if not specified
- Break down combined foods into individual items
- Provide reasoning for your estimates

Respond in JSON format:
{{
  "foods": [
    {{
      "name": "food name",
      "quantity": "amount with unit",
      "calories": number,
      "macros": {{"protein": g, "carbs": g, "fat": g}},
      "reasoning": "why this estimate"
    }}
  ],
  "confidence": "high/medium/low",
  "overall_reasoning": "explanation of estimates"
}}"""

            response = await client.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=1000,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse response
            import json
            content = response.content[0].text.strip()

            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

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
                    confidence_score=0.7,
                    verification_source="anthropic_text_analysis"
                )
                foods.append(food_item)

            return AgentEstimate(
                agent_name="anthropic_text_validator",
                foods=foods,
                total_calories=sum(f.calories for f in foods),
                confidence=data.get("confidence", "medium"),
                reasoning=data.get("overall_reasoning", "Second opinion on text estimate")
            )

        except Exception as e:
            logger.error(f"Anthropic text estimate error: {e}")
            # Return empty estimate instead of failing
            return AgentEstimate(
                agent_name="anthropic_text_validator",
                foods=[],
                total_calories=0,
                confidence="low",
                reasoning=f"Error: {str(e)}"
            )

    async def _validate_with_agent(
        self,
        estimate1: AgentEstimate,
        estimate2: AgentEstimate,
        photo_path: Optional[str],
        caption: Optional[str]
    ) -> Dict[str, Any]:
        """
        Use validator agent to compare two estimates and determine consensus.

        Returns dict with:
        - agreement: "high"/"medium"/"low"
        - explanation: Why estimates agree/disagree
        - recommended_action: "use_average"/"favor_estimate1"/"favor_estimate2"/"request_clarification"
        - discrepancies: List of specific differences
        """
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

            # Format estimates for comparison
            estimate1_summary = self._format_estimate_for_comparison(estimate1)
            estimate2_summary = self._format_estimate_for_comparison(estimate2)

            prompt = f"""You are a nutrition accuracy validator. Two AI models analyzed the same food:

User description: "{caption or 'No description'}"

**Estimate 1 ({estimate1.agent_name}):**
{estimate1_summary}
Total: {estimate1.total_calories} calories
Confidence: {estimate1.confidence}

**Estimate 2 ({estimate2.agent_name}):**
{estimate2_summary}
Total: {estimate2.total_calories} calories
Confidence: {estimate2.confidence}

Your tasks:
1. Compare the estimates and identify discrepancies (>20% difference in calories or macros)
2. Check reasonableness against known nutrition ranges for these foods
3. Determine agreement level: high (estimates within 15%), medium (15-30% diff), low (>30% diff)
4. Explain any significant disagreements
5. Recommend action: use_average, favor_estimate1, favor_estimate2, or request_clarification

Respond in JSON format:
{{
  "agreement": "high/medium/low",
  "explanation": "detailed explanation of comparison",
  "recommended_action": "use_average/favor_estimate1/favor_estimate2/request_clarification",
  "discrepancies": ["list of specific differences found"],
  "reasoning": "why you recommend this action",
  "confidence_score": 0.0-1.0
}}"""

            response = await client.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=1500,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse response
            import json
            content = response.content[0].text.strip()

            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            validation = json.loads(content)

            logger.info(f"Validator analysis: {validation['agreement']} agreement, "
                       f"action: {validation['recommended_action']}")

            return validation

        except Exception as e:
            logger.error(f"Validator agent error: {e}", exc_info=True)

            # Fallback: simple comparison
            return self._simple_comparison(estimate1, estimate2)

    def _format_estimate_for_comparison(self, estimate: AgentEstimate) -> str:
        """Format estimate for validator agent"""
        lines = []
        for food in estimate.foods:
            lines.append(
                f"• {food.name} ({food.quantity}): {food.calories} cal | "
                f"P: {food.macros.protein}g | C: {food.macros.carbs}g | F: {food.macros.fat}g"
            )
        return "\n".join(lines) if lines else "No foods detected"

    def _simple_comparison(
        self,
        estimate1: AgentEstimate,
        estimate2: AgentEstimate
    ) -> Dict[str, Any]:
        """Fallback: simple percentage-based comparison"""

        cal1 = estimate1.total_calories
        cal2 = estimate2.total_calories

        if cal1 == 0 or cal2 == 0:
            return {
                "agreement": "low",
                "explanation": "One estimate has zero calories",
                "recommended_action": "favor_estimate1" if cal1 > cal2 else "favor_estimate2",
                "discrepancies": ["Missing data in one estimate"],
                "reasoning": "Favoring estimate with data",
                "confidence_score": 0.5
            }

        diff_percent = abs(cal1 - cal2) / max(cal1, cal2) * 100

        if diff_percent < 15:
            agreement = "high"
            action = "use_average"
        elif diff_percent < 30:
            agreement = "medium"
            action = "use_average"
        else:
            agreement = "low"
            action = "request_clarification"

        return {
            "agreement": agreement,
            "explanation": f"Estimates differ by {diff_percent:.0f}%",
            "recommended_action": action,
            "discrepancies": [f"Total calories: {cal1} vs {cal2} ({diff_percent:.0f}% difference)"],
            "reasoning": f"Based on {diff_percent:.0f}% difference threshold",
            "confidence_score": max(0.3, 1.0 - (diff_percent / 100))
        }

    async def _determine_consensus(
        self,
        agent_estimates: List[AgentEstimate],
        validator_analysis: Dict[str, Any]
    ) -> ConsensusResult:
        """
        Determine final consensus based on agent estimates and validator analysis.
        """
        agreement_level = validator_analysis.get("agreement", "medium")
        recommended_action = validator_analysis.get("recommended_action", "use_average")

        # Extract validation warnings from reasonableness checks
        validation_warnings = []

        # Check reasonableness for each estimate
        for estimate in agent_estimates:
            _, warnings = validate_food_items(estimate.foods)
            validation_warnings.extend(warnings)

        # Deduplicate warnings
        validation_warnings = list(set(validation_warnings))

        # Determine final estimate based on recommended action
        if recommended_action == "use_average":
            final_foods = self._average_estimates(agent_estimates)
            confidence_score = validator_analysis.get("confidence_score", 0.8)

        elif recommended_action == "favor_estimate1":
            final_foods = agent_estimates[0].foods
            confidence_score = validator_analysis.get("confidence_score", 0.7)

        elif recommended_action == "favor_estimate2":
            final_foods = agent_estimates[1].foods
            confidence_score = validator_analysis.get("confidence_score", 0.7)

        else:  # request_clarification
            # Use average but flag for review
            final_foods = self._average_estimates(agent_estimates)
            confidence_score = validator_analysis.get("confidence_score", 0.5)

        # Calculate totals
        total_calories = sum(f.calories for f in final_foods)
        total_macros = FoodMacros(
            protein=sum(f.macros.protein for f in final_foods),
            carbs=sum(f.macros.carbs for f in final_foods),
            fat=sum(f.macros.fat for f in final_foods)
        )

        # Build consensus explanation
        explanation = self._build_consensus_explanation(
            agent_estimates,
            validator_analysis,
            agreement_level,
            recommended_action
        )

        # Generate clarifying questions if needed
        clarifying_questions = []
        needs_clarification = recommended_action == "request_clarification"

        if needs_clarification:
            clarifying_questions = [
                "Could you provide more details about portion sizes?",
                "Were there any additions or toppings not visible in the photo?",
                "Is this estimate in the range you expected?"
            ]

        return ConsensusResult(
            final_foods=final_foods,
            total_calories=int(total_calories),
            total_macros=total_macros,
            agreement_level=agreement_level,
            confidence_score=confidence_score,
            agent_estimates=agent_estimates,
            consensus_explanation=explanation,
            discrepancies=validator_analysis.get("discrepancies", []),
            validation_warnings=validation_warnings,
            needs_clarification=needs_clarification,
            clarifying_questions=clarifying_questions
        )

    def _average_estimates(self, estimates: List[AgentEstimate]) -> List[FoodItem]:
        """Average nutrition values from multiple estimates"""

        if not estimates:
            return []

        # If estimates have different number of foods, use the first one
        if len(estimates) < 2 or len(estimates[0].foods) != len(estimates[1].foods):
            logger.warning("Cannot average estimates with different food counts")
            return estimates[0].foods

        averaged_foods = []

        for i in range(len(estimates[0].foods)):
            food1 = estimates[0].foods[i]
            food2 = estimates[1].foods[i]

            # Average calories and macros
            avg_calories = int((food1.calories + food2.calories) / 2)
            avg_macros = FoodMacros(
                protein=(food1.macros.protein + food2.macros.protein) / 2,
                carbs=(food1.macros.carbs + food2.macros.carbs) / 2,
                fat=(food1.macros.fat + food2.macros.fat) / 2
            )

            # Use food1 name and quantity
            averaged_food = FoodItem(
                name=food1.name,
                quantity=food1.quantity,
                calories=avg_calories,
                macros=avg_macros,
                verification_source="consensus_average",
                confidence_score=0.8
            )

            averaged_foods.append(averaged_food)

        return averaged_foods

    def _build_consensus_explanation(
        self,
        estimates: List[AgentEstimate],
        validator_analysis: Dict[str, Any],
        agreement_level: str,
        recommended_action: str
    ) -> str:
        """Build user-friendly explanation of consensus"""

        lines = []

        # Header based on agreement level
        if agreement_level == "high":
            lines.append("✅ **High Confidence** - All models agree closely")
        elif agreement_level == "medium":
            lines.append("⚠️ **Medium Confidence** - Models show some variation")
        else:
            lines.append("⚠️ **Low Confidence** - Significant disagreement between models")

        # Show individual estimates
        lines.append("\n**Agent Estimates:**")
        for est in estimates:
            lines.append(f"• {est.agent_name}: {est.total_calories} cal ({est.confidence} confidence)")

        # Add validator explanation
        lines.append(f"\n**Analysis:** {validator_analysis.get('explanation', 'Estimates compared')}")

        # Add discrepancies if any
        discrepancies = validator_analysis.get("discrepancies", [])
        if discrepancies:
            lines.append("\n**Discrepancies Found:**")
            for disc in discrepancies[:3]:  # Limit to 3
                lines.append(f"• {disc}")

        # Add reasoning
        reasoning = validator_analysis.get("reasoning", "")
        if reasoning:
            lines.append(f"\n{reasoning}")

        return "\n".join(lines)

    def _create_fallback_consensus(
        self,
        estimate: AgentEstimate,
        error_msg: str
    ) -> ConsensusResult:
        """Create fallback consensus when consensus fails"""

        total_calories = sum(f.calories for f in estimate.foods)
        total_macros = FoodMacros(
            protein=sum(f.macros.protein for f in estimate.foods),
            carbs=sum(f.macros.carbs for f in estimate.foods),
            fat=sum(f.macros.fat for f in estimate.foods)
        )

        return ConsensusResult(
            final_foods=estimate.foods,
            total_calories=int(total_calories),
            total_macros=total_macros,
            agreement_level="low",
            confidence_score=0.5,
            agent_estimates=[estimate],
            consensus_explanation=f"⚠️ Consensus validation failed: {error_msg}\nUsing single estimate with low confidence.",
            discrepancies=[],
            validation_warnings=["Consensus validation unavailable - please verify estimate"],
            needs_clarification=True,
            clarifying_questions=["Does this estimate seem reasonable for your meal?"]
        )


# Singleton instance
_consensus_engine_instance = None


def get_consensus_engine() -> NutritionConsensusEngine:
    """Get singleton consensus engine instance"""
    global _consensus_engine_instance
    if _consensus_engine_instance is None:
        _consensus_engine_instance = NutritionConsensusEngine()
    return _consensus_engine_instance
