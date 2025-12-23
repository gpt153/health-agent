"""Tests for multi-agent consensus system (Phase 2)"""
import pytest
from datetime import datetime
from src.agent.nutrition_consensus import (
    NutritionConsensusEngine,
    AgentEstimate,
    ConsensusResult
)
from src.models.food import FoodItem, FoodMacros


@pytest.mark.asyncio
async def test_consensus_high_agreement():
    """Test consensus when agents agree closely"""

    # Create two similar estimates (within 15% difference)
    food1 = FoodItem(
        name="Chicken breast",
        quantity="150g",
        calories=248,
        macros=FoodMacros(protein=52, carbs=0, fat=5)
    )

    food2 = FoodItem(
        name="Chicken breast",
        quantity="150g",
        calories=255,  # ~3% difference - should be high agreement
        macros=FoodMacros(protein=54, carbs=0, fat=5)
    )

    estimate1 = AgentEstimate(
        agent_name="openai",
        foods=[food1],
        total_calories=248,
        confidence="high"
    )

    estimate2 = AgentEstimate(
        agent_name="anthropic",
        foods=[food2],
        total_calories=255,
        confidence="high"
    )

    engine = NutritionConsensusEngine()

    # Test simple comparison
    comparison = engine._simple_comparison(estimate1, estimate2)

    assert comparison["agreement"] == "high"
    assert comparison["recommended_action"] == "use_average"
    assert comparison["confidence_score"] > 0.8


@pytest.mark.asyncio
async def test_consensus_medium_disagreement():
    """Test consensus when agents show moderate disagreement"""

    # Create estimates with 20% difference
    food1 = FoodItem(
        name="Salad",
        quantity="1 cup",
        calories=100,
        macros=FoodMacros(protein=3, carbs=12, fat=2)
    )

    food2 = FoodItem(
        name="Salad",
        quantity="1 cup",
        calories=120,  # 20% difference - medium agreement
        macros=FoodMacros(protein=4, carbs=14, fat=2)
    )

    estimate1 = AgentEstimate(
        agent_name="openai",
        foods=[food1],
        total_calories=100,
        confidence="medium"
    )

    estimate2 = AgentEstimate(
        agent_name="anthropic",
        foods=[food2],
        total_calories=120,
        confidence="medium"
    )

    engine = NutritionConsensusEngine()
    comparison = engine._simple_comparison(estimate1, estimate2)

    assert comparison["agreement"] == "medium"
    assert comparison["recommended_action"] == "use_average"


@pytest.mark.asyncio
async def test_consensus_low_agreement():
    """Test consensus when agents strongly disagree"""

    # Create estimates with >30% difference
    food1 = FoodItem(
        name="Salad",
        quantity="1 cup",
        calories=80,  # Conservative
        macros=FoodMacros(protein=2, carbs=8, fat=1)
    )

    food2 = FoodItem(
        name="Salad",
        quantity="1 cup",
        calories=450,  # Way too high! (Issue #28 example)
        macros=FoodMacros(protein=10, carbs=40, fat=20)
    )

    estimate1 = AgentEstimate(
        agent_name="openai",
        foods=[food1],
        total_calories=80,
        confidence="high"
    )

    estimate2 = AgentEstimate(
        agent_name="anthropic",
        foods=[food2],
        total_calories=450,
        confidence="low"
    )

    engine = NutritionConsensusEngine()
    comparison = engine._simple_comparison(estimate1, estimate2)

    assert comparison["agreement"] == "low"
    assert comparison["recommended_action"] == "request_clarification"
    assert comparison["confidence_score"] < 0.5


@pytest.mark.asyncio
async def test_average_estimates():
    """Test that estimates are averaged correctly"""

    food1 = FoodItem(
        name="Rice",
        quantity="1 cup",
        calories=200,
        macros=FoodMacros(protein=4, carbs=44, fat=1)
    )

    food2 = FoodItem(
        name="Rice",
        quantity="1 cup",
        calories=220,
        macros=FoodMacros(protein=5, carbs=46, fat=1)
    )

    estimate1 = AgentEstimate(
        agent_name="openai",
        foods=[food1],
        total_calories=200,
        confidence="high"
    )

    estimate2 = AgentEstimate(
        agent_name="anthropic",
        foods=[food2],
        total_calories=220,
        confidence="high"
    )

    engine = NutritionConsensusEngine()
    averaged = engine._average_estimates([estimate1, estimate2])

    assert len(averaged) == 1
    assert averaged[0].calories == 210  # (200 + 220) / 2
    assert averaged[0].macros.protein == 4.5  # (4 + 5) / 2
    assert averaged[0].macros.carbs == 45  # (44 + 46) / 2
    assert averaged[0].verification_source == "consensus_average"


@pytest.mark.asyncio
async def test_format_estimate_for_comparison():
    """Test estimate formatting for validator agent"""

    foods = [
        FoodItem(
            name="Chicken",
            quantity="150g",
            calories=248,
            macros=FoodMacros(protein=52, carbs=0, fat=5)
        ),
        FoodItem(
            name="Rice",
            quantity="1 cup",
            calories=200,
            macros=FoodMacros(protein=4, carbs=44, fat=1)
        )
    ]

    estimate = AgentEstimate(
        agent_name="openai",
        foods=foods,
        total_calories=448,
        confidence="high"
    )

    engine = NutritionConsensusEngine()
    formatted = engine._format_estimate_for_comparison(estimate)

    assert "Chicken" in formatted
    assert "150g" in formatted
    assert "248 cal" in formatted
    assert "Rice" in formatted
    assert "1 cup" in formatted


@pytest.mark.asyncio
async def test_build_consensus_explanation():
    """Test building user-friendly consensus explanation"""

    estimate1 = AgentEstimate(
        agent_name="openai_gpt4o_mini",
        foods=[],
        total_calories=250,
        confidence="high"
    )

    estimate2 = AgentEstimate(
        agent_name="anthropic_claude_3_5_sonnet",
        foods=[],
        total_calories=260,
        confidence="high"
    )

    validator_analysis = {
        "agreement": "high",
        "explanation": "Both models agree within 4%",
        "recommended_action": "use_average",
        "discrepancies": [],
        "reasoning": "Estimates are very close, average is reliable",
        "confidence_score": 0.92
    }

    engine = NutritionConsensusEngine()
    explanation = engine._build_consensus_explanation(
        [estimate1, estimate2],
        validator_analysis,
        "high",
        "use_average"
    )

    assert "High Confidence" in explanation
    assert "openai_gpt4o_mini: 250 cal" in explanation
    assert "anthropic_claude_3_5_sonnet: 260 cal" in explanation
    assert "Both models agree within 4%" in explanation


@pytest.mark.asyncio
async def test_consensus_with_different_food_counts():
    """Test consensus when agents detect different number of foods"""

    # Agent 1: detects 2 foods
    foods1 = [
        FoodItem(
            name="Chicken and rice bowl",
            quantity="1 bowl",
            calories=450,
            macros=FoodMacros(protein=35, carbs=50, fat=10)
        )
    ]

    # Agent 2: breaks it down into 2 items
    foods2 = [
        FoodItem(
            name="Chicken",
            quantity="150g",
            calories=250,
            macros=FoodMacros(protein=52, carbs=0, fat=5)
        ),
        FoodItem(
            name="Rice",
            quantity="1 cup",
            calories=200,
            macros=FoodMacros(protein=4, carbs=44, fat=1)
        )
    ]

    estimate1 = AgentEstimate(
        agent_name="openai",
        foods=foods1,
        total_calories=450,
        confidence="medium"
    )

    estimate2 = AgentEstimate(
        agent_name="anthropic",
        foods=foods2,
        total_calories=450,
        confidence="high"
    )

    engine = NutritionConsensusEngine()

    # Should still work - use first estimate when counts differ
    averaged = engine._average_estimates([estimate1, estimate2])
    assert len(averaged) == 1  # Uses first estimate structure
    assert averaged[0].name == "Chicken and rice bowl"


@pytest.mark.asyncio
async def test_fallback_consensus():
    """Test fallback when consensus process fails"""

    food = FoodItem(
        name="Test food",
        quantity="1 serving",
        calories=200,
        macros=FoodMacros(protein=10, carbs=20, fat=8)
    )

    estimate = AgentEstimate(
        agent_name="test_agent",
        foods=[food],
        total_calories=200,
        confidence="medium"
    )

    engine = NutritionConsensusEngine()
    fallback = engine._create_fallback_consensus(estimate, "Test error message")

    assert fallback.final_foods == [food]
    assert fallback.total_calories == 200
    assert fallback.agreement_level == "low"
    assert fallback.confidence_score == 0.5
    assert fallback.needs_clarification == True
    assert "Test error message" in fallback.consensus_explanation


@pytest.mark.asyncio
async def test_consensus_catches_overestimation():
    """Test that consensus catches the 450 cal salad error from Issue #28"""

    # Agent 1: Conservative estimate (correct)
    food1 = FoodItem(
        name="Small salad",
        quantity="1 cup",
        calories=82,  # Reasonable
        macros=FoodMacros(protein=2, carbs=8, fat=1)
    )

    # Agent 2: Over-estimated (the bug we're fixing)
    food2 = FoodItem(
        name="Small salad",
        quantity="1 cup",
        calories=450,  # WAY TOO HIGH!
        macros=FoodMacros(protein=15, carbs=40, fat=20)
    )

    estimate1 = AgentEstimate(
        agent_name="openai",
        foods=[food1],
        total_calories=82,
        confidence="high"
    )

    estimate2 = AgentEstimate(
        agent_name="anthropic",
        foods=[food2],
        total_calories=450,
        confidence="low"
    )

    engine = NutritionConsensusEngine()
    comparison = engine._simple_comparison(estimate1, estimate2)

    # Should detect LOW agreement and request clarification
    assert comparison["agreement"] == "low"
    assert comparison["recommended_action"] == "request_clarification"

    # Discrepancies should mention the huge difference
    assert len(comparison["discrepancies"]) > 0
    assert "82 vs 450" in comparison["discrepancies"][0]


@pytest.mark.asyncio
async def test_zero_calorie_handling():
    """Test handling of zero-calorie estimates (missing data)"""

    food1 = FoodItem(
        name="Unknown food",
        quantity="1 serving",
        calories=0,  # No data
        macros=FoodMacros(protein=0, carbs=0, fat=0)
    )

    food2 = FoodItem(
        name="Unknown food",
        quantity="1 serving",
        calories=200,  # Has data
        macros=FoodMacros(protein=10, carbs=20, fat=8)
    )

    estimate1 = AgentEstimate(
        agent_name="openai",
        foods=[food1],
        total_calories=0,
        confidence="low"
    )

    estimate2 = AgentEstimate(
        agent_name="anthropic",
        foods=[food2],
        total_calories=200,
        confidence="medium"
    )

    engine = NutritionConsensusEngine()
    comparison = engine._simple_comparison(estimate1, estimate2)

    # Should favor the estimate with actual data
    assert comparison["agreement"] == "low"
    assert comparison["recommended_action"] == "favor_estimate2"
    assert "Missing data" in comparison["discrepancies"][0]
