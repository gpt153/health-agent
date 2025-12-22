"""Integration tests for Phase 2: Multi-Agent Debate System

Tests the complete multi-agent coordination, debate mechanism, and moderator synthesis.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Test can run without pydantic by directly testing the core logic
from src.agent.nutrition_moderator import synthesize_consensus, _build_reasoning, _calculate_final_variance
from src.agent.nutrition_debate import _generate_argument, _generate_rebuttal


def test_moderator_synthesis():
    """Test that moderator synthesizes debate correctly"""

    print("\n" + "="*60)
    print("TEST 1: Moderator Synthesis")
    print("="*60)

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
        "variance": 1.034,
        "consensus": 170,
        "confidence": 0.35
    }

    result = synthesize_consensus(agents, debate_log, comparison)

    print(f"Result: {result['calories']} kcal")
    print(f"Confidence: {result['confidence']:.1%}")
    print(f"Source: {result['source']}")
    print(f"Reasoning: {result['reasoning'][:100]}...")

    # Assertions
    assert result['calories'] < 200, "Should be much lower than original 450 kcal"
    assert result['calories'] > 100, "Should be above validation's very conservative 50 kcal"
    assert result['confidence'] > 0.35, "Confidence should improve after debate"
    assert result['source'] == "debate_consensus"
    assert "USDA" in result['reasoning'], "Should explain USDA weighting"

    print("✓ PASS: Moderator synthesis works correctly\n")


def test_usda_weighted_higher():
    """Test that USDA estimates are weighted 2x"""

    print("="*60)
    print("TEST 2: USDA Weighting (2x)")
    print("="*60)

    # Simple case: AI says 300, USDA says 200
    agents = [
        {"agent": "vision_ai", "source": "vision_ai", "calories": 300, "macros": {}, "confidence": 0.7},
        {"agent": "usda_database", "source": "usda", "calories": 200, "macros": {}, "confidence": 0.9}
    ]

    debate_log = [
        {"round": 1, "agent": "vision_ai", "calories": 300, "adjusted_confidence": 0.7},
        {"round": 1, "agent": "usda_database", "calories": 200, "adjusted_confidence": 0.9}
    ]

    comparison = {"variance": 0.20, "consensus": 250, "confidence": 0.7}

    result = synthesize_consensus(agents, debate_log, comparison)

    # Expected: (300*1*0.7 + 200*2*0.9) / (1*0.7 + 2*0.9) = (210 + 360) / 2.5 = 228
    print(f"AI: 300 kcal, USDA: 200 kcal")
    print(f"Simple average: 250 kcal")
    print(f"Weighted (USDA 2x): {result['calories']} kcal")

    assert result['calories'] < 250, "Should lean toward USDA (200)"
    assert result['calories'] > 200, "But not exactly USDA due to AI input"
    assert 220 <= result['calories'] <= 235, "Should be around 228"

    print(f"✓ PASS: USDA correctly weighted (expected ~228, got {result['calories']})\n")


def test_debate_argument_generation():
    """Test that agents generate proper arguments"""

    print("="*60)
    print("TEST 3: Debate Argument Generation")
    print("="*60)

    agent = {
        "agent": "vision_ai",
        "calories": 450,
        "macros": {},
        "confidence": 0.7
    }

    other_agents = [agent]  # Simplified for test
    comparison = {"variance": 0.50}

    argument = _generate_argument(agent, 1, other_agents, comparison)

    print(f"Agent: {argument['agent']}")
    print(f"Summary: {argument['summary'][:80]}...")
    print(f"Strengths: {len(argument['strengths'])}")
    print(f"Weaknesses: {len(argument['weaknesses'])}")

    assert argument['agent'] == "vision_ai"
    assert argument['calories'] == 450
    assert len(argument['strengths']) > 0, "Should list strengths"
    assert len(argument['weaknesses']) > 0, "Should list weaknesses"
    assert "photo" in argument['summary'].lower() or "visual" in argument['summary'].lower()

    print("✓ PASS: Arguments generated correctly\n")


def test_debate_rebuttal_generation():
    """Test that agents generate rebuttals"""

    print("="*60)
    print("TEST 4: Debate Rebuttal Generation")
    print("="*60)

    agent = {"agent": "usda_database", "calories": 120, "confidence": 0.9}

    arguments = [
        {"agent": "vision_ai", "calories": 450, "summary": "Vision AI argument"},
        {"agent": "usda_database", "calories": 120, "summary": "USDA argument"}
    ]

    comparison = {"variance": 0.80}

    rebuttal = _generate_rebuttal(agent, 2, arguments, comparison)

    print(f"Agent: {rebuttal['agent']}")
    print(f"Rebuttals: {len(rebuttal.get('rebuttals', []))}")
    print(f"Adjusted confidence: {rebuttal.get('adjusted_confidence', 0):.1%}")

    assert rebuttal['agent'] == "usda_database"
    assert len(rebuttal.get('rebuttals', [])) > 0, "Should rebut vision_ai's high estimate"
    assert rebuttal['adjusted_confidence'] is not None

    print("✓ PASS: Rebuttals generated correctly\n")


def test_variance_calculation():
    """Test final variance calculation"""

    print("="*60)
    print("TEST 5: Final Variance Calculation")
    print("="*60)

    # Low variance case
    entries_low = [
        {"calories": 100},
        {"calories": 105},
        {"calories": 95}
    ]

    variance_low = _calculate_final_variance(entries_low)

    print(f"Low variance case: {variance_low:.1%}")

    assert variance_low < 0.10, "Should be very low variance"

    # High variance case
    entries_high = [
        {"calories": 450},
        {"calories": 120},
        {"calories": 50}
    ]

    variance_high = _calculate_final_variance(entries_high)

    print(f"High variance case: {variance_high:.1%}")

    assert variance_high > 0.50, "Should be high variance"

    print("✓ PASS: Variance calculated correctly\n")


def test_reasoning_builder():
    """Test that reasoning is human-readable"""

    print("="*60)
    print("TEST 6: Reasoning Builder")
    print("="*60)

    agents = [
        {"agent": "vision_ai", "calories": 450, "macros": {}},
        {"agent": "usda_database", "calories": 120, "macros": {}},
        {"agent": "validation_rules", "calories": 50, "macros": {}}
    ]

    debate_log = [
        {"round": 1, "agent": "vision_ai", "calories": 450},
        {"round": 2, "agent": "usda_database", "calories": 120}
    ]

    comparison = {"variance": 1.034}

    reasoning = _build_reasoning(agents, 144, comparison, debate_log)

    print(f"Reasoning length: {len(reasoning)} chars")
    print(f"First 150 chars: {reasoning[:150]}...")

    assert "variance" in reasoning.lower(), "Should mention variance"
    assert "144" in reasoning or "consensus" in reasoning.lower(), "Should mention final estimate"
    assert len(reasoning) > 50, "Should be substantial explanation"
    assert "USDA" in reasoning, "Should explain USDA weighting"

    print("✓ PASS: Reasoning is clear and explanatory\n")


def test_end_to_end_multi_agent():
    """Test complete multi-agent flow"""

    print("="*60)
    print("TEST 7: End-to-End Multi-Agent Flow")
    print("="*60)

    # Start: User's reported issue (small salad, 450 kcal)
    print("Starting estimate: 450 kcal (AI vision)")

    # Step 1: All agents provide estimates
    agents = [
        {"agent": "vision_ai", "source": "vision_ai", "calories": 450, "macros": {"protein": 5, "carbs": 10, "fat": 35}, "confidence": 0.7},
        {"agent": "usda_database", "source": "usda", "calories": 120, "macros": {"protein": 2, "carbs": 8, "fat": 6}, "confidence": 0.9},
        {"agent": "validation_rules", "source": "validation", "calories": 50, "macros": {"protein": 1, "carbs": 5, "fat": 2}, "confidence": 0.8}
    ]

    print("Agent estimates: 450, 120, 50 kcal")

    # Step 2: Debate (2 rounds)
    debate_log = []
    for round_num in [1, 2]:
        for agent in agents:
            if round_num == 1:
                arg = _generate_argument(agent, round_num, agents, {"variance": 1.034})
                debate_log.append(arg)
            else:
                prev_args = [a for a in debate_log if a["round"] == 1]
                reb = _generate_rebuttal(agent, round_num, prev_args, {"variance": 1.034})
                debate_log.append(reb)

    print(f"Debate completed: {len(debate_log)} arguments/rebuttals")

    # Step 3: Moderator synthesis
    comparison = {"variance": 1.034, "consensus": 170, "confidence": 0.35}
    result = synthesize_consensus(agents, debate_log, comparison)

    print(f"\nFinal estimate: {result['calories']} kcal")
    print(f"Confidence: {result['confidence']:.1%}")
    print(f"Improvement: {((450 - result['calories']) / 450 * 100):.1f}% reduction from original")

    # Assertions
    assert result['calories'] < 450 * 0.5, "Should reduce by at least 50%"
    assert result['calories'] > 50, "Should be above validation's conservative estimate"
    assert 100 < result['calories'] < 200, "Should be in reasonable range"
    assert result['confidence'] > 0.35, "Confidence should improve after debate"

    print("\n✓ PASS: Complete multi-agent flow successful\n")


if __name__ == "__main__":
    print("\n" + "🤖 PHASE 2 INTEGRATION TESTS 🤖".center(60, "="))
    print("Testing multi-agent debate system\n")

    try:
        test_moderator_synthesis()
        test_usda_weighted_higher()
        test_debate_argument_generation()
        test_debate_rebuttal_generation()
        test_variance_calculation()
        test_reasoning_builder()
        test_end_to_end_multi_agent()

        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED (7/7)".center(60))
        print("="*60)
        print("\nPhase 2 implementation is working correctly!")
        print("- Multi-agent coordination ✓")
        print("- Debate mechanism ✓")
        print("- Moderator synthesis ✓")
        print("- USDA weighted 2x ✓")
        print("- User-reported issues corrected ✓")
        print("\n")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        raise
    except Exception as e:
        print(f"\n💥 ERROR: {e}\n")
        raise
