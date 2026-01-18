"""Debate-driven consensus for nutrition estimates

This module implements the debate mechanism where agents argue their cases
and a moderator synthesizes the discussion to reach consensus.

Based on MIT research showing 3 agents with 2 debate rounds improves
accuracy from ~70% to ~95%.
"""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


async def run_debate_rounds(
    agents: List[Dict],
    comparison: Dict,
    max_rounds: int = 2
) -> Dict:
    """
    Run debate between agents to reach consensus.

    Args:
        agents: List of agent estimates with reasoning
        comparison: Comparison results (variance, consensus, etc.)
        max_rounds: Maximum number of debate rounds

    Returns:
        {
            "final_estimate": {...},
            "debate_log": [...]
        }
    """
    logger.info(f"Starting debate with {len(agents)} agents, max {max_rounds} rounds")

    debate_log = []

    # Round 1: Initial arguments
    round_1_arguments = []

    for agent in agents:
        argument = _generate_argument(
            agent=agent,
            round_num=1,
            other_agents=agents,
            comparison=comparison
        )
        round_1_arguments.append(argument)
        debate_log.append(argument)

        logger.debug(f"Round 1 - {agent['agent']}: {argument['summary']}")

    # Round 2: Rebuttals (if max_rounds > 1)
    if max_rounds > 1:
        round_2_rebuttals = []

        for agent in agents:
            rebuttal = _generate_rebuttal(
                agent=agent,
                round_num=2,
                arguments=round_1_arguments,
                comparison=comparison
            )
            round_2_rebuttals.append(rebuttal)
            debate_log.append(rebuttal)

            logger.debug(f"Round 2 - {agent['agent']}: {rebuttal['summary']}")

    # Synthesize consensus
    from src.agent.nutrition_moderator import synthesize_consensus

    final_estimate = synthesize_consensus(
        agents=agents,
        debate_log=debate_log,
        comparison=comparison
    )

    logger.info(f"Debate complete. Final estimate: {final_estimate['calories']} kcal")

    return {
        "final_estimate": final_estimate,
        "debate_log": debate_log
    }


def _generate_argument(
    agent: Dict,
    round_num: int,
    other_agents: List[Dict],
    comparison: Dict
) -> Dict:
    """
    Generate argument for an agent's estimate.

    Args:
        agent: Agent making the argument
        round_num: Current round number
        other_agents: All agents (including this one)
        comparison: Comparison results

    Returns:
        Argument dict with reasoning
    """
    agent_name = agent["agent"]
    calories = agent["calories"]

    # Build argument based on agent type
    if agent_name == "vision_ai":
        summary = (
            f"I analyzed the photo using computer vision and identified the food items. "
            f"Based on visual appearance and portion size, I estimate {calories} kcal."
        )
        strengths = [
            "Direct analysis of actual food in photo",
            "Accounts for visible preparation method",
            "Can detect portion sizes from visual cues"
        ]
        weaknesses = [
            "May overestimate portion sizes",
            "Cannot see all ingredients",
            "No access to verified nutritional databases"
        ]

    elif agent_name == "usda_database":
        summary = (
            f"I matched this food to the USDA FoodData Central database. "
            f"Based on {agent.get('food_match', 'the closest match')}, I estimate {calories} kcal."
        )
        strengths = [
            "Based on laboratory-analyzed nutritional data",
            "Standardized portions and measurements",
            "High reliability for common foods"
        ]
        weaknesses = [
            "May not match exact preparation method",
            "Relies on quantity parsing accuracy",
            "Generic matches may not reflect actual food"
        ]

    elif agent_name == "validation_rules":
        summary = (
            f"I checked the estimates against typical nutritional ranges. "
            f"Based on nutritional science and USDA averages, I suggest {calories} kcal."
        )
        strengths = [
            "Catches unrealistic estimates",
            "Based on validated nutritional ranges",
            "Accounts for common estimation errors"
        ]
        weaknesses = [
            "Cannot account for unique preparations",
            "May be too conservative",
            "Relies on typical ranges, not specific analysis"
        ]

    else:
        summary = f"{agent_name} estimates {calories} kcal"
        strengths = []
        weaknesses = []

    # Add context about variance
    if comparison["variance"] > 0.50:
        context = f"Note: There is high disagreement ({comparison['variance']:.0%} variance) among agents."
    else:
        context = f"There is {comparison['variance']:.0%} variance among estimates."

    argument = {
        "round": round_num,
        "agent": agent_name,
        "calories": calories,
        "summary": summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "context": context,
        "confidence": agent.get("confidence", 0.7)
    }

    return argument


def _generate_rebuttal(
    agent: Dict,
    round_num: int,
    arguments: List[Dict],
    comparison: Dict
) -> Dict:
    """
    Generate rebuttal addressing other agents' arguments.

    Args:
        agent: Agent making the rebuttal
        round_num: Current round number
        arguments: Previous round arguments
        comparison: Comparison results

    Returns:
        Rebuttal dict
    """
    agent_name = agent["agent"]
    calories = agent["calories"]

    # Find arguments from other agents
    other_arguments = [arg for arg in arguments if arg["agent"] != agent_name]

    # Build rebuttal
    rebuttals = []

    for other in other_arguments:
        diff = abs(calories - other["calories"])
        diff_pct = (diff / max(calories, other["calories"])) * 100

        if diff_pct > 50:  # More than 50% difference
            rebuttals.append(
                f"The {other['agent']} estimate of {other['calories']} kcal "
                f"differs by {diff_pct:.0f}% from mine. "
                f"This suggests either {_identify_issue(agent_name, other)}."
            )
        elif diff_pct > 20:  # 20-50% difference
            rebuttals.append(
                f"While {other['agent']} estimated {other['calories']} kcal, "
                f"my analysis suggests a {diff_pct:.0f}% difference, likely due to "
                f"{_identify_likely_cause(agent_name, other)}."
            )

    summary = (
        f"After reviewing the other estimates, I maintain my estimate of {calories} kcal. "
        f"{' '.join(rebuttals) if rebuttals else 'The variance is within acceptable range.'}"
    )

    # Adjust confidence based on agreement
    if comparison["variance"] < 0.15:  # Low variance
        adjusted_confidence = min(1.0, agent.get("confidence", 0.7) + 0.1)
    elif comparison["variance"] > 0.50:  # High variance
        adjusted_confidence = max(0.3, agent.get("confidence", 0.7) - 0.2)
    else:
        adjusted_confidence = agent.get("confidence", 0.7)

    return {
        "round": round_num,
        "agent": agent_name,
        "calories": calories,
        "summary": summary,
        "rebuttals": rebuttals,
        "adjusted_confidence": adjusted_confidence
    }


def _identify_issue(agent_name: str, other_agent: Dict) -> str:
    """Identify likely issue causing disagreement"""
    if agent_name == "vision_ai" and other_agent["agent"] == "validation_rules":
        return "I overestimated portion size or the validation range is too conservative"
    elif agent_name == "usda_database" and other_agent["agent"] == "vision_ai":
        return "the visual estimate didn't account for actual density/weight or my database match was too generic"
    elif agent_name == "validation_rules" and other_agent["agent"] == "vision_ai":
        return "the visual AI significantly overestimated, which my range check flagged"
    else:
        return "different estimation methodologies or data sources"


def _identify_likely_cause(agent_name: str, other_agent: Dict) -> str:
    """Identify likely cause of moderate disagreement"""
    if agent_name == "vision_ai":
        return "portion size interpretation differences"
    elif agent_name == "usda_database":
        return "preparation method or ingredient variations"
    elif agent_name == "validation_rules":
        return "conservative range estimates vs specific analysis"
    else:
        return "methodological differences"


# Example usage
if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.DEBUG)

    async def test_debate():
        """Test debate mechanism"""

        logger.info("\n" + "="*60)
        logger.info("DEBATE MECHANISM TEST")
        logger.info("="*60)

        # Simulate the small salad case with high variance
        agents = [
            {
                "agent": "vision_ai",
                "source": "vision_ai",
                "calories": 450,
                "macros": {"protein": 5, "carbs": 10, "fat": 35},
                "confidence": 0.7,
                "reasoning": "Visual analysis of photo"
            },
            {
                "agent": "usda_database",
                "source": "usda",
                "calories": 120,
                "macros": {"protein": 2, "carbs": 8, "fat": 6},
                "confidence": 0.9,
                "reasoning": "USDA database match"
            },
            {
                "agent": "validation_rules",
                "source": "validation",
                "calories": 50,
                "macros": {"protein": 1, "carbs": 5, "fat": 2},
                "confidence": 0.8,
                "reasoning": "Typical range for small green salad"
            }
        ]

        comparison = {
            "variance": 1.034,  # 103.4%
            "consensus": 170,
            "confidence": 0.35,
            "requires_debate": True
        }

        result = await run_debate_rounds(
            agents=agents,
            comparison=comparison,
            max_rounds=2
        )

        logger.info("\nDebate Log:")
        for entry in result["debate_log"]:
            logger.info(f"\nRound {entry['round']} - {entry['agent']}:")
            logger.info(f"  Estimate: {entry['calories']} kcal")
            logger.info(f"  {entry['summary']}")

        logger.info(f"\n\nFinal Estimate: {result['final_estimate']['calories']} kcal")
        logger.info(f"Confidence: {result['final_estimate']['confidence']:.1%}")

        logger.info("\n" + "="*60)
        logger.info("TEST COMPLETE")
        logger.info("="*60)

    asyncio.run(test_debate())
