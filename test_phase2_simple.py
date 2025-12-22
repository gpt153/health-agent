"""Simple Phase 2 test - validates multi-agent system works"""

# Direct imports to avoid __init__.py issues
import sys
sys.path.insert(0, 'src/agent')

from nutrition_moderator import synthesize_consensus
from nutrition_debate import _generate_argument, _generate_rebuttal

print("🤖 PHASE 2: MULTI-AGENT SYSTEM TEST")
print("="*60)

# Test the user's small salad case
agents = [
    {"agent": "vision_ai", "source": "vision_ai", "calories": 450, "macros": {"protein": 5, "carbs": 10, "fat": 35}, "confidence": 0.7},
    {"agent": "usda_database", "source": "usda", "calories": 120, "macros": {"protein": 2, "carbs": 8, "fat": 6}, "confidence": 0.9},
    {"agent": "validation_rules", "source": "validation", "calories": 50, "macros": {"protein": 1, "carbs": 5, "fat": 2}, "confidence": 0.8}
]

# Generate debate
debate_log = []
for round_num in [1, 2]:
    for agent in agents:
        if round_num == 1:
            arg = _generate_argument(agent, round_num, agents, {"variance": 1.034})
            debate_log.append(arg)
            print(f"R{round_num} {agent['agent']}: {agent['calories']} kcal")
        else:
            prev_args = [a for a in debate_log if a["round"] == 1]
            reb = _generate_rebuttal(agent, round_num, prev_args, {"variance": 1.034})
            debate_log.append(reb)

# Synthesize
comparison = {"variance": 1.034, "consensus": 170, "confidence": 0.35}
result = synthesize_consensus(agents, debate_log, comparison)

print("\n" + "="*60)
print(f"ORIGINAL: 450 kcal (Vision AI)")
print(f"CORRECTED: {result['calories']} kcal (Multi-Agent Consensus)")
print(f"IMPROVEMENT: {((450 - result['calories']) / 450 * 100):.1f}% reduction")
print(f"CONFIDENCE: {result['confidence']:.1%}")
print("="*60)

# Validate
assert result['calories'] < 200, f"Should be <200 kcal, got {result['calories']}"
assert result['calories'] > 100, f"Should be >100 kcal, got {result['calories']}"
assert result['confidence'] > 0.35, f"Confidence should improve, got {result['confidence']}"

print("\n✅ PHASE 2 TEST PASSED")
print("Multi-agent debate system is working correctly!\n")
