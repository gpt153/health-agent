"""Integration tests for Phase 1: Nutrition Accuracy Improvements

Tests the validation layer, USDA verification enhancements, and estimate comparison.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.nutrition_validation import validate_nutrition_estimate
from src.utils.estimate_comparison import compare_estimates


def test_validation_catches_user_reported_issues():
    """Test that validation catches the issues reported by user"""

    print("\n" + "="*60)
    print("TEST 1: Validation catches small salad overestimate")
    print("="*60)

    # User reported: small salad estimated at 450 cal (should be ~50-100)
    result = validate_nutrition_estimate(
        food_name="green salad",
        quantity="small",
        calories=450,
        protein=5,
        carbs=10,
        fat=35
    )

    print(f"Is valid: {result['is_valid']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Issues: {result['issues']}")
    print(f"Suggested: {result['suggested_calories']} kcal")
    print(f"Expected range: {result['expected_range']}")

    # Assertions
    assert result['is_valid'] == False, "Should flag 450 cal as invalid for small salad"
    assert result['confidence'] < 0.5, "Confidence should be low for invalid estimate"
    assert result['suggested_calories'] is not None, "Should provide suggestion"
    assert result['suggested_calories'] < 100, "Suggestion should be reasonable (<100 cal)"

    print("✓ PASS: Small salad overestimate caught\n")

    # Test 2: Chicken breast overestimate
    print("="*60)
    print("TEST 2: Validation catches chicken breast overestimate")
    print("="*60)

    result2 = validate_nutrition_estimate(
        food_name="chicken breast",
        quantity="170g",
        calories=650,
        protein=55,
        carbs=0,
        fat=45
    )

    print(f"Is valid: {result2['is_valid']}")
    print(f"Confidence: {result2['confidence']}")
    print(f"Issues: {result2['issues']}")
    print(f"Suggested: {result2['suggested_calories']} kcal")
    print(f"Expected range: {result2['expected_range']}")

    assert result2['is_valid'] == False, "Should flag 650 cal as invalid for 170g chicken"
    assert result2['confidence'] < 0.5, "Confidence should be low"
    assert 250 < result2['suggested_calories'] < 300, "Suggestion should be in reasonable range"

    print("✓ PASS: Chicken breast overestimate caught\n")


def test_comparison_detects_variance():
    """Test that estimate comparison detects high variance"""

    print("="*60)
    print("TEST 3: Estimate comparison detects variance")
    print("="*60)

    # Simulate the user's salad case: AI says 450, USDA says 120, validation says 50
    estimates = [
        {"source": "vision_ai", "calories": 450},
        {"source": "usda", "calories": 120},
        {"source": "validation", "calories": 50}
    ]

    result = compare_estimates(estimates)

    print(f"Variance: {result['variance']:.1%}")
    print(f"Consensus: {result['consensus']} kcal")
    print(f"Confidence: {result['confidence']:.1%}")
    print(f"Requires debate: {result['requires_debate']}")
    print(f"Reasoning: {result['reasoning']}")

    assert result['variance'] > 0.30, "Should detect high variance (>30%)"
    assert result['requires_debate'] == True, "Should trigger debate for high variance"
    assert result['confidence'] < 0.7, "Confidence should be low for high variance"
    assert 100 < result['consensus'] < 250, "Consensus should be weighted toward USDA"

    print("✓ PASS: High variance detected and flagged\n")


def test_comparison_accepts_low_variance():
    """Test that low variance estimates pass without debate"""

    print("="*60)
    print("TEST 4: Low variance estimates accepted")
    print("="*60)

    # All estimates close together
    estimates = [
        {"source": "vision_ai", "calories": 280},
        {"source": "usda", "calories": 275},
        {"source": "validation", "calories": 285}
    ]

    result = compare_estimates(estimates)

    print(f"Variance: {result['variance']:.1%}")
    print(f"Consensus: {result['consensus']} kcal")
    print(f"Confidence: {result['confidence']:.1%}")
    print(f"Requires debate: {result['requires_debate']}")

    assert result['variance'] < 0.10, "Variance should be low (<10%)"
    assert result['requires_debate'] == False, "Should not trigger debate"
    assert result['confidence'] > 0.8, "Confidence should be high"

    print("✓ PASS: Low variance accepted without debate\n")


def test_weighted_average_favors_usda():
    """Test that USDA estimates are weighted more heavily"""

    print("="*60)
    print("TEST 5: Weighted average favors USDA")
    print("="*60)

    # AI says 300, USDA says 200 (should lean toward USDA)
    estimates = [
        {"source": "vision_ai", "calories": 300},
        {"source": "usda", "calories": 200}
    ]

    result = compare_estimates(estimates)

    print(f"Consensus: {result['consensus']} kcal")
    print(f"Simple average would be: {(300 + 200) / 2} kcal")
    print(f"Weighted average (USDA 2x): {result['consensus']} kcal")

    # With USDA weighted 2x: (300*1 + 200*2) / (1+2) = 700/3 ≈ 233
    assert result['consensus'] < 250, "Should be closer to USDA (200) than AI (300)"
    assert result['consensus'] > 200, "But not exactly USDA due to AI input"

    print("✓ PASS: USDA weighted correctly\n")


def test_end_to_end_correction():
    """Test complete flow from bad estimate to corrected value"""

    print("="*60)
    print("TEST 6: End-to-end correction flow")
    print("="*60)

    # Start with user's reported issue
    food_name = "small salad"
    quantity = "small"
    ai_estimate = 450  # AI's bad estimate
    usda_estimate = 120  # USDA's lookup

    # Step 1: Validate AI estimate
    validation = validate_nutrition_estimate(
        food_name=food_name,
        quantity=quantity,
        calories=ai_estimate,
        protein=5,
        carbs=10,
        fat=35
    )

    print(f"Step 1 - Validation:")
    print(f"  AI estimate {ai_estimate} kcal is valid: {validation['is_valid']}")
    print(f"  Suggested correction: {validation['suggested_calories']} kcal")

    # Step 2: Prepare estimates
    estimates = [
        {"source": "vision_ai", "calories": ai_estimate},
        {"source": "usda", "calories": usda_estimate}
    ]

    if not validation['is_valid'] and validation['suggested_calories']:
        estimates.append({
            "source": "validation",
            "calories": validation['suggested_calories']
        })

    # Step 3: Compare and get consensus
    comparison = compare_estimates(estimates)

    print(f"\nStep 2 - Comparison:")
    print(f"  Variance: {comparison['variance']:.1%}")
    print(f"  Final estimate: {comparison['consensus']} kcal")
    print(f"  Confidence: {comparison['confidence']:.1%}")
    print(f"  Requires debate: {comparison['requires_debate']}")

    # Final result should be much better than original
    final_estimate = comparison['consensus']

    print(f"\nResult:")
    print(f"  Original AI: {ai_estimate} kcal (WRONG)")
    print(f"  Corrected: {final_estimate} kcal (BETTER)")
    print(f"  Improvement: {((ai_estimate - final_estimate) / ai_estimate * 100):.1f}% reduction")

    # Assertions
    assert final_estimate < ai_estimate * 0.6, "Should reduce by at least 40%"
    assert final_estimate < 200, "Final should be reasonable for small salad"
    assert comparison['requires_debate'] == True, "Should flag high variance"

    print("\n✓ PASS: End-to-end correction successful\n")


if __name__ == "__main__":
    print("\n" + "🧪 PHASE 1 INTEGRATION TESTS 🧪".center(60, "="))
    print("Testing nutrition accuracy improvements\n")

    try:
        test_validation_catches_user_reported_issues()
        test_comparison_detects_variance()
        test_comparison_accepts_low_variance()
        test_weighted_average_favors_usda()
        test_end_to_end_correction()

        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED".center(60))
        print("="*60)
        print("\nPhase 1 implementation is working correctly!")
        print("- Validation layer catches bad estimates")
        print("- Comparison detects variance and triggers debate")
        print("- USDA estimates are weighted appropriately")
        print("- User-reported issues are now corrected")
        print("\n")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        raise
    except Exception as e:
        print(f"\n💥 ERROR: {e}\n")
        raise
