"""Compare multiple nutritional estimates and detect variance

This module helps identify when different estimation sources disagree significantly,
which triggers additional verification steps (debate/consensus).
"""

import logging
from typing import List, Dict, Optional
from statistics import mean, stdev

logger = logging.getLogger(__name__)


def calculate_variance(estimates: List[Dict]) -> float:
    """
    Calculate variance between estimates.

    Args:
        estimates: List of estimate dicts with 'calories' field

    Returns:
        Variance as a percentage (0.0 to 1.0+)
        e.g., 0.30 = 30% variance
    """
    if not estimates or len(estimates) < 2:
        return 0.0

    calories = [e.get('calories', 0) for e in estimates if e.get('calories')]

    if not calories or len(calories) < 2:
        return 0.0

    avg = mean(calories)

    if avg == 0:
        return 0.0

    # Calculate coefficient of variation (stdev / mean)
    variance = stdev(calories) / avg

    logger.debug(f"Variance for {calories}: {variance:.2%}")

    return variance


def weighted_average(estimates: List[Dict], weights: Optional[Dict[str, float]] = None) -> int:
    """
    Calculate weighted average of calorie estimates.

    Args:
        estimates: List of estimate dicts with 'source' and 'calories'
        weights: Optional dict mapping source names to weights
                 e.g., {"usda": 2.0, "vision_ai": 1.0, "validation": 1.5}

    Returns:
        Weighted average calories (rounded to int)
    """
    if not estimates:
        return 0

    # Default weights (USDA is most reliable)
    if weights is None:
        weights = {
            "usda": 2.0,
            "vision_ai": 1.0,
            "validation": 1.5,
            "rules": 1.5
        }

    total_weighted_calories = 0.0
    total_weight = 0.0

    for estimate in estimates:
        source = estimate.get('source', 'unknown')
        calories = estimate.get('calories', 0)

        # Get weight for this source (default to 1.0)
        weight = weights.get(source, 1.0)

        total_weighted_calories += calories * weight
        total_weight += weight

        logger.debug(f"  {source}: {calories} kcal (weight: {weight})")

    if total_weight == 0:
        return 0

    weighted_avg = total_weighted_calories / total_weight

    logger.debug(f"Weighted average: {weighted_avg:.1f} kcal")

    return int(weighted_avg)


def calculate_confidence(variance: float, estimate_count: int) -> float:
    """
    Calculate confidence score based on variance and number of estimates.

    Args:
        variance: Variance percentage (0.0 to 1.0+)
        estimate_count: Number of estimates being compared

    Returns:
        Confidence score (0.0 to 1.0)
    """
    if estimate_count == 0:
        return 0.0

    # Base confidence on low variance
    if variance <= 0.10:  # <= 10% variance
        base_confidence = 0.95
    elif variance <= 0.20:  # <= 20% variance
        base_confidence = 0.85
    elif variance <= 0.30:  # <= 30% variance
        base_confidence = 0.70
    elif variance <= 0.50:  # <= 50% variance
        base_confidence = 0.50
    else:  # > 50% variance
        base_confidence = 0.30

    # Boost confidence if we have more estimates
    if estimate_count >= 3:
        base_confidence = min(1.0, base_confidence + 0.05)

    logger.debug(f"Confidence: {base_confidence:.2f} (variance: {variance:.2%}, n={estimate_count})")

    return base_confidence


def compare_estimates(
    estimates: List[Dict],
    variance_threshold: float = 0.30,
    weights: Optional[Dict[str, float]] = None
) -> Dict:
    """
    Compare estimates from multiple sources and determine if debate is needed.

    Args:
        estimates: List of estimate dicts with 'source', 'calories', 'macros'
        variance_threshold: Threshold for triggering debate (default: 0.30 = 30%)
        weights: Optional custom weights for each source

    Returns:
        {
            "variance": float,
            "consensus": int,  # Weighted average calories
            "confidence": float,
            "requires_debate": bool,
            "all_estimates": list,  # Copy of input for transparency
            "reasoning": str
        }
    """
    if not estimates:
        return {
            "variance": 0.0,
            "consensus": 0,
            "confidence": 0.0,
            "requires_debate": False,
            "all_estimates": [],
            "reasoning": "No estimates provided"
        }

    # Calculate variance
    variance = calculate_variance(estimates)

    # Calculate consensus (weighted average)
    consensus = weighted_average(estimates, weights)

    # Calculate confidence
    confidence = calculate_confidence(variance, len(estimates))

    # Determine if debate is needed
    requires_debate = variance > variance_threshold

    # Build reasoning
    if requires_debate:
        reasoning = (
            f"High variance detected ({variance:.1%} > {variance_threshold:.1%}). "
            f"Estimates range from {min(e.get('calories', 0) for e in estimates)} "
            f"to {max(e.get('calories', 0) for e in estimates)} kcal. "
            f"Debate recommended to reach consensus."
        )
    else:
        reasoning = (
            f"Low variance ({variance:.1%}). "
            f"All estimates are reasonably close. "
            f"Consensus: {consensus} kcal (confidence: {confidence:.1%})"
        )

    logger.info(f"Estimate comparison: {len(estimates)} sources, variance={variance:.1%}, debate={requires_debate}")

    return {
        "variance": variance,
        "consensus": consensus,
        "confidence": confidence,
        "requires_debate": requires_debate,
        "all_estimates": estimates.copy(),
        "reasoning": reasoning
    }


def format_comparison_report(comparison: Dict) -> str:
    """
    Format comparison results for user display.

    Args:
        comparison: Result from compare_estimates()

    Returns:
        Formatted string for display
    """
    estimates = comparison.get('all_estimates', [])

    report = "📊 **Nutrition Estimate Comparison**\n\n"

    # Show all estimates
    report += "**Sources:**\n"
    for est in estimates:
        source = est.get('source', 'unknown')
        calories = est.get('calories', 0)
        macros = est.get('macros', {})

        report += f"- {source.replace('_', ' ').title()}: {calories} kcal"

        if macros:
            p = macros.get('protein', 0)
            c = macros.get('carbs', 0)
            f = macros.get('fat', 0)
            report += f" (P: {p}g, C: {c}g, F: {f}g)"

        report += "\n"

    # Show variance
    variance = comparison.get('variance', 0)
    report += f"\n**Variance:** {variance:.1%}\n"

    # Show consensus
    consensus = comparison.get('consensus', 0)
    confidence = comparison.get('confidence', 0)
    report += f"**Consensus:** {consensus} kcal\n"
    report += f"**Confidence:** {confidence:.1%}\n"

    # Show reasoning
    reasoning = comparison.get('reasoning', '')
    report += f"\n{reasoning}\n"

    return report


# Example usage and tests
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print("=" * 60)
    print("ESTIMATE COMPARISON TESTS")
    print("=" * 60)

    # Test 1: Low variance (all estimates close)
    print("\n1. Low variance - all estimates agree:")
    estimates1 = [
        {"source": "vision_ai", "calories": 280, "macros": {"protein": 53, "carbs": 0, "fat": 6}},
        {"source": "usda", "calories": 275, "macros": {"protein": 52, "carbs": 0, "fat": 6}},
        {"source": "validation", "calories": 285, "macros": {"protein": 54, "carbs": 0, "fat": 6}}
    ]

    result1 = compare_estimates(estimates1)
    print(format_comparison_report(result1))
    print(f"   Requires debate: {result1['requires_debate']}")

    # Test 2: High variance (user's reported issue)
    print("\n2. High variance - disagreement (small salad case):")
    estimates2 = [
        {"source": "vision_ai", "calories": 450, "macros": {"protein": 5, "carbs": 10, "fat": 35}},
        {"source": "usda", "calories": 120, "macros": {"protein": 2, "carbs": 8, "fat": 6}},
        {"source": "validation", "calories": 50, "macros": {"protein": 1, "carbs": 5, "fat": 2}}
    ]

    result2 = compare_estimates(estimates2)
    print(format_comparison_report(result2))
    print(f"   Requires debate: {result2['requires_debate']}")
    print(f"   Weighted consensus: {result2['consensus']} kcal")

    # Test 3: Medium variance (borderline case)
    print("\n3. Medium variance - borderline:")
    estimates3 = [
        {"source": "vision_ai", "calories": 300},
        {"source": "usda", "calories": 220},
        {"source": "validation", "calories": 260}
    ]

    result3 = compare_estimates(estimates3, variance_threshold=0.30)
    print(format_comparison_report(result3))
    print(f"   Requires debate: {result3['requires_debate']}")

    print("\n" + "=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)
