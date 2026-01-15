"""Moderator agent for synthesizing nutrition debate

The moderator analyzes debate arguments and produces a final consensus estimate,
taking into account:
- Agent reliability (USDA weighted 2x)
- Argument strength
- Confidence adjustments from debate
- Variance and outlier detection
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def synthesize_consensus(
    agents: List[Dict],
    debate_log: List[Dict],
    comparison: Dict
) -> Dict:
    """
    Synthesize debate and produce final consensus estimate.

    Weighting strategy:
    - USDA: 2.0x (most reliable, lab-verified data)
    - Validation: 1.5x (domain expertise, catches outliers)
    - Vision AI: 1.0x (direct observation but prone to errors)

    Args:
        agents: Original agent estimates
        debate_log: All debate arguments and rebuttals
        comparison: Comparison results

    Returns:
        Final estimate dict with calories, macros, confidence, reasoning
    """
    logger.info("Moderator synthesizing consensus from debate...")

    # Base weights
    weights = {
        "vision_ai": 1.0,
        "usda_database": 2.0,
        "validation_rules": 1.5
    }

    # Adjust weights based on debate performance
    final_round_entries = [
        entry for entry in debate_log
        if entry["round"] == max(e["round"] for e in debate_log)
    ]

    # Calculate adjusted weights based on confidence changes
    adjusted_weights = {}
    for entry in final_round_entries:
        agent_name = entry["agent"]
        base_weight = weights.get(agent_name, 1.0)

        # Boost weight if confidence increased during debate
        confidence = entry.get("adjusted_confidence") or entry.get("confidence", 0.7)
        adjusted_weights[agent_name] = base_weight * confidence

        logger.debug(
            f"{agent_name}: base_weight={base_weight}, "
            f"confidence={confidence:.2f}, "
            f"final_weight={adjusted_weights[agent_name]:.2f}"
        )

    # Calculate weighted consensus
    total_weighted_calories = 0.0
    total_weight = 0.0

    for agent in agents:
        agent_name = agent["agent"]
        calories = agent["calories"]
        weight = adjusted_weights.get(agent_name, weights.get(agent_name, 1.0))

        total_weighted_calories += calories * weight
        total_weight += weight

        logger.debug(f"{agent_name}: {calories} kcal × {weight:.2f}")

    consensus_calories = int(total_weighted_calories / total_weight) if total_weight > 0 else 0

    logger.info(f"Weighted consensus: {consensus_calories} kcal")

    # Determine final macros (prefer USDA if available)
    usda_agent = next((a for a in agents if a["agent"] == "usda_database"), None)
    if usda_agent:
        final_macros = usda_agent["macros"]
        macro_source = "USDA"
    else:
        # Average macros if no USDA
        avg_protein = sum(a["macros"]["protein"] for a in agents) / len(agents)
        avg_carbs = sum(a["macros"]["carbs"] for a in agents) / len(agents)
        avg_fat = sum(a["macros"]["fat"] for a in agents) / len(agents)

        final_macros = {
            "protein": round(avg_protein, 1),
            "carbs": round(avg_carbs, 1),
            "fat": round(avg_fat, 1)
        }
        macro_source = "averaged"

    logger.debug(f"Final macros ({macro_source}): {final_macros}")

    # Calculate final confidence
    # High variance = low confidence
    # Agreement after debate = higher confidence
    base_confidence = comparison.get("confidence", 0.5)

    # Boost confidence if agents converged during debate
    if comparison["variance"] > 0.50:  # Started with high variance
        # Check if debate reduced disagreement
        final_variance = _calculate_final_variance(final_round_entries)
        if final_variance < comparison["variance"]:
            confidence_boost = 0.1  # Debate helped
        else:
            confidence_boost = 0.0  # Still disagreeing
    else:
        confidence_boost = 0.05  # Low variance to begin with

    final_confidence = min(1.0, base_confidence + confidence_boost)

    logger.debug(
        f"Confidence: base={base_confidence:.2f}, "
        f"boost={confidence_boost:.2f}, "
        f"final={final_confidence:.2f}"
    )

    # Build reasoning summary
    reasoning = _build_reasoning(
        agents=agents,
        consensus_calories=consensus_calories,
        comparison=comparison,
        debate_log=debate_log
    )

    final_estimate = {
        "calories": consensus_calories,
        "macros": final_macros,
        "confidence": final_confidence,
        "source": "debate_consensus",
        "reasoning": reasoning
    }

    logger.info(
        f"Moderator consensus: {consensus_calories} kcal "
        f"(confidence: {final_confidence:.1%})"
    )

    return final_estimate


def _calculate_final_variance(final_round_entries: List[Dict]) -> float:
    """Calculate variance after final debate round"""
    if not final_round_entries or len(final_round_entries) < 2:
        return 0.0

    calories = [entry["calories"] for entry in final_round_entries]
    mean_cal = sum(calories) / len(calories)

    if mean_cal == 0:
        return 0.0

    from statistics import stdev
    return stdev(calories) / mean_cal


def _build_reasoning(
    agents: List[Dict],
    consensus_calories: int,
    comparison: Dict,
    debate_log: List[Dict]
) -> str:
    """Build human-readable reasoning for consensus"""

    # Identify which agents were closest to consensus
    closest_agent = min(
        agents,
        key=lambda a: abs(a["calories"] - consensus_calories)
    )

    reasoning_parts = []

    # Part 1: Variance acknowledgment
    if comparison["variance"] > 0.50:
        reasoning_parts.append(
            f"Agents initially disagreed significantly ({comparison['variance']:.0%} variance). "
        )
    elif comparison["variance"] > 0.20:
        reasoning_parts.append(
            f"Agents showed moderate disagreement ({comparison['variance']:.0%} variance). "
        )
    else:
        reasoning_parts.append(
            f"Agents largely agreed ({comparison['variance']:.0%} variance). "
        )

    # Part 2: Debate process
    rounds = max(entry["round"] for entry in debate_log)
    rounds_text = f"{rounds} rounds of debate" if rounds > 1 else "1 round of discussion"
    reasoning_parts.append(f"After {rounds_text}, ")

    # Part 3: Closest agent
    reasoning_parts.append(
        f"the {closest_agent['agent'].replace('_', ' ')} estimate "
        f"of {closest_agent['calories']} kcal was closest to the weighted consensus. "
    )

    # Part 4: Weighting explanation
    usda_agent = next((a for a in agents if a["agent"] == "usda_database"), None)
    if usda_agent:
        reasoning_parts.append(
            "USDA database data was weighted 2x due to laboratory verification. "
        )

    # Part 5: Final consensus
    reasoning_parts.append(
        f"Final consensus: {consensus_calories} kcal."
    )

    return "".join(reasoning_parts)


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    logger.info("\n" + "="*60)
    logger.info("MODERATOR SYNTHESIS TEST")
    logger.info("="*60)

    # Test case: Small salad with high variance
    agents = [
        {
            "agent": "vision_ai",
            "source": "vision_ai",
            "calories": 450,
            "macros": {"protein": 5, "carbs": 10, "fat": 35},
            "confidence": 0.7
        },
        {
            "agent": "usda_database",
            "source": "usda",
            "calories": 120,
            "macros": {"protein": 2, "carbs": 8, "fat": 6},
            "confidence": 0.9
        },
        {
            "agent": "validation_rules",
            "source": "validation",
            "calories": 50,
            "macros": {"protein": 1, "carbs": 5, "fat": 2},
            "confidence": 0.8
        }
    ]

    debate_log = [
        {"round": 1, "agent": "vision_ai", "calories": 450, "confidence": 0.7},
        {"round": 1, "agent": "usda_database", "calories": 120, "confidence": 0.9},
        {"round": 1, "agent": "validation_rules", "calories": 50, "confidence": 0.8},
        {"round": 2, "agent": "vision_ai", "calories": 450, "adjusted_confidence": 0.5},
        {"round": 2, "agent": "usda_database", "calories": 120, "adjusted_confidence": 0.95},
        {"round": 2, "agent": "validation_rules", "calories": 50, "adjusted_confidence": 0.75}
    ]

    comparison = {
        "variance": 1.034,  # 103%
        "consensus": 170,
        "confidence": 0.35
    }

    result = synthesize_consensus(agents, debate_log, comparison)

    logger.info("\nSynthesis Result:")
    logger.info(f"  Calories: {result['calories']} kcal")
    logger.info(f"  Macros: P:{result['macros']['protein']}g C:{result['macros']['carbs']}g F:{result['macros']['fat']}g")
    logger.info(f"  Confidence: {result['confidence']:.1%}")
    logger.info(f"  Source: {result['source']}")
    logger.info(f"\n  Reasoning:\n  {result['reasoning']}")

    logger.info("\n" + "="*60)
    logger.info("TEST COMPLETE")
    logger.info("="*60)
