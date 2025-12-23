# UPDATED Implementation Plan: Food Accuracy for ALL Logging Methods

**Issue:** #28 - "accuracy of food content"
**Critical Update:** Apply validation to ALL food logging (photos AND text)
**User Request:** "i want this workflow, or the relevant parts of it to be used in all food logging. even if user types the food and amount in message"

---

## Key Finding: Photo Validation Already Implemented!

**Good news:** The photo workflow (`src/bot.py` lines 939-950) ALREADY has multi-agent validation:
```python
# Phase 1: Multi-Agent Validation
from src.agent.nutrition_validator import get_validator
validator = get_validator()

validated_analysis, validation_warnings = await validator.validate(
    vision_result=analysis,
    photo_path=str(photo_path),
    caption=caption,
    visual_patterns=visual_patterns,
    usda_verified_items=verified_foods,
    enable_cross_validation=True  # Enable multi-model cross-checking
)
```

**Problem:** Text-based food logging (when user types "I ate chicken breast") does NOT use this validation!

---

## Updated Phase 1: Apply Validation to Text Food Logging

### Current Flow for Text Messages

**File:** `src/bot.py` - `handle_message()` function (line 706)

When user sends text message:
1. Calls `get_agent_response()` - AI agent processes naturally
2. Agent MAY use tools to log food (unclear if validation applied)
3. No explicit validation pipeline like photos have

### Required Changes

**1. Add Agent Tool: `log_food_from_text_validated`**

**File:** `src/agent/__init__.py`

```python
class FoodEntryValidatedResult(BaseModel):
    """Result of validated food entry from text"""
    success: bool
    message: str
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    foods: list[dict]
    validation_warnings: Optional[list[str]] = None
    confidence: str  # high/medium/low
    entry_id: Optional[str] = None


@agent.tool
async def log_food_from_text_validated(
    ctx,
    food_description: str,
    quantity: Optional[str] = None,
    meal_type: Optional[str] = None
) -> FoodEntryValidatedResult:
    """
    **LOG FOOD FROM TEXT WITH VALIDATION** - Use when user describes food they ate

    This tool applies the SAME rigorous validation as photo analysis:
    - Multi-agent cross-checking
    - USDA verification
    - Reasonableness validation
    - Calibration from user corrections

    Use this when:
    - User says "I ate X"
    - User describes a meal in text
    - User provides food + quantity

    Examples:
    - "I ate 150g chicken breast and a small salad"
    - "Just had a Chipotle burrito bowl"
    - "Lunch: 2 eggs, toast with butter"

    Args:
        food_description: What they ate (e.g., "grilled chicken and rice")
        quantity: Amount if specified (e.g., "150g", "1 serving", "medium bowl")
        meal_type: breakfast/lunch/dinner/snack (optional)

    Returns:
        FoodEntryValidatedResult with calories, macros, and validation warnings
    """
    deps: AgentDeps = ctx.deps

    try:
        # Step 1: Parse text description into structured food data
        from src.utils.food_text_parser import parse_food_description

        logger.info(f"Parsing food description: {food_description}")

        parsed_result = await parse_food_description(
            description=food_description,
            quantity=quantity,
            user_id=deps.telegram_id
        )

        # Step 2: Apply SAME validation pipeline as photos
        from src.agent.nutrition_validator import get_validator
        from src.utils.nutrition_search import verify_food_items

        # USDA verification
        verified_foods = await verify_food_items(parsed_result.foods)

        # Multi-agent validation
        validator = get_validator()
        validated_analysis, validation_warnings = await validator.validate(
            vision_result=parsed_result,
            photo_path=None,  # No photo for text entries
            caption=food_description,
            visual_patterns=None,
            usda_verified_items=verified_foods,
            enable_cross_validation=True  # Same as photos!
        )

        # Step 3: Apply learned corrections (Phase 4 feature)
        from src.utils.food_calibration import calibrate_foods
        calibrated_foods = await calibrate_foods(
            validated_analysis.foods,
            deps.telegram_id
        )

        # Step 4: Calculate totals
        total_calories = sum(f.calories for f in calibrated_foods)
        total_protein = sum(f.macros.protein for f in calibrated_foods)
        total_carbs = sum(f.macros.carbs for f in calibrated_foods)
        total_fat = sum(f.macros.fat for f in calibrated_foods)

        # Step 5: Save to database
        from src.models.food import FoodEntry, FoodMacros
        from src.db.queries import save_food_entry
        from datetime import datetime

        entry = FoodEntry(
            user_id=deps.telegram_id,
            timestamp=datetime.now(),
            photo_path=None,  # Text entry
            foods=calibrated_foods,
            total_calories=total_calories,
            total_macros=FoodMacros(
                protein=total_protein,
                carbs=total_carbs,
                fat=total_fat
            ),
            meal_type=meal_type,
            notes=food_description
        )

        await save_food_entry(entry)
        logger.info(f"Saved validated text food entry for {deps.telegram_id}")

        # Step 6: Format response with validation info
        foods_list = [
            {
                "name": f.name,
                "quantity": f.quantity,
                "calories": f.calories,
                "protein": f.macros.protein,
                "verification_source": f.verification_source
            }
            for f in calibrated_foods
        ]

        # Build response message with warnings
        message_parts = [
            f"✅ Logged: {food_description}",
            f"\n**Total:** {total_calories} cal | P: {total_protein}g | C: {total_carbs}g | F: {total_fat}g",
            f"\n_Confidence: {validated_analysis.confidence}_"
        ]

        if validation_warnings:
            message_parts.append("\n\n⚠️ **Validation Alerts:**")
            for warning in validation_warnings:
                message_parts.append(f"• {warning}")

        if validated_analysis.clarifying_questions:
            message_parts.append("\n\n**Questions to improve accuracy:**")
            for q in validated_analysis.clarifying_questions:
                message_parts.append(f"• {q}")

        message = "\n".join(message_parts)

        return FoodEntryValidatedResult(
            success=True,
            message=message,
            total_calories=total_calories,
            total_protein=total_protein,
            total_carbs=total_carbs,
            total_fat=total_fat,
            foods=foods_list,
            validation_warnings=validation_warnings,
            confidence=validated_analysis.confidence,
            entry_id=entry.id
        )

    except Exception as e:
        logger.error(f"Error in log_food_from_text_validated: {e}", exc_info=True)
        return FoodEntryValidatedResult(
            success=False,
            message=f"Error logging food: {str(e)}",
            total_calories=0.0,
            total_protein=0.0,
            total_carbs=0.0,
            total_fat=0.0,
            foods=[],
            validation_warnings=None,
            confidence="low"
        )
```

**2. Create Food Text Parser**

**File:** `src/utils/food_text_parser.py` (NEW)

```python
"""Parse food descriptions from text into structured data"""
import logging
from typing import Optional
from openai import AsyncOpenAI
import json

from src.config import OPENAI_API_KEY
from src.models.food import FoodItem, FoodMacros
from src.utils.vision import VisionAnalysisResult
from datetime import datetime

logger = logging.getLogger(__name__)


async def parse_food_description(
    description: str,
    quantity: Optional[str] = None,
    user_id: Optional[str] = None
) -> VisionAnalysisResult:
    """
    Parse text description into structured food data.

    Uses LLM to extract foods, quantities, and initial calorie estimates.
    Returns same VisionAnalysisResult format as photo analysis for consistency.

    Args:
        description: User's food description (e.g., "150g chicken breast and salad")
        quantity: Optional quantity override
        user_id: User ID for context (optional)

    Returns:
        VisionAnalysisResult with foods array
    """
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""Extract food items from this description: "{description}"

IMPORTANT:
- Be CONSERVATIVE with calorie estimates (better to underestimate than overestimate)
- If quantity is unclear, use typical serving sizes
- For vague descriptions like "small salad", estimate on the LOWER end
- Break down combined foods (e.g., "chicken and rice" = 2 items)

Return valid JSON only:
{{
  "foods": [
    {{
      "name": "food name",
      "quantity": "amount with unit (e.g., 150g, 1 cup)",
      "calories": estimated_calories_number,
      "macros": {{
        "protein": grams,
        "carbs": grams,
        "fat": grams
      }},
      "confidence": "high/medium/low"
    }}
  ],
  "overall_confidence": "high/medium/low",
  "clarifying_questions": ["question if uncertain"]
}}

Examples:
- "I ate 170g chicken breast" → {{"name": "Chicken breast (grilled)", "quantity": "170g", "calories": 280}}
- "small salad" → {{"name": "Mixed green salad", "quantity": "1 cup", "calories": 50}}
- "Chipotle bowl" → Break down into rice, beans, chicken, etc.
"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,  # Low temperature for consistency
            max_tokens=800
        )

        content = response.choices[0].message.content.strip()

        # Parse JSON
        if content.startswith("```json"):
            content = content.split("```json")[1].split("```")[0].strip()
        elif content.startswith("```"):
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
                confidence=food_data.get("confidence", "medium"),
                verification_source="ai_text_parse",  # Distinguish from photo AI
                food_category=None  # Will be categorized later
            )
            foods.append(food_item)

        # Build result
        result = VisionAnalysisResult(
            foods=foods,
            confidence=data.get("overall_confidence", "medium"),
            clarifying_questions=data.get("clarifying_questions", []),
            timestamp=datetime.now()
        )

        logger.info(f"Parsed {len(foods)} foods from text: {description[:50]}")
        return result

    except Exception as e:
        logger.error(f"Error parsing food description: {e}", exc_info=True)

        # Return minimal fallback
        fallback_food = FoodItem(
            name=description,
            quantity="1 serving",
            calories=200,  # Conservative estimate
            macros=FoodMacros(protein=10, carbs=20, fat=8),
            confidence="low",
            verification_source="fallback"
        )

        return VisionAnalysisResult(
            foods=[fallback_food],
            confidence="low",
            clarifying_questions=["Could you provide more details about portions?"],
            timestamp=datetime.now()
        )
```

**3. Update Agent System Prompt**

**File:** `src/memory/system_prompt.py`

Add to system prompt:

```python
FOOD_LOGGING_GUIDANCE = """
## Food Logging (CRITICAL)

When users describe food they ate in text (not photo), YOU MUST use the validation tool:

**ALWAYS use log_food_from_text_validated for:**
- "I ate X"
- "Just had X for lunch"
- "Breakfast was X"
- "I'm having X"

**DO NOT:**
- Make up calorie estimates yourself
- Log food without validation
- Trust initial estimates - always validate!

The tool applies multi-agent validation, USDA verification, and learned corrections.
This ensures accuracy and builds user trust.

**Example:**
User: "I ate 150g chicken breast and a small salad"
You: [Call log_food_from_text_validated with food_description="150g chicken breast and a small salad"]
Then respond with the validated results + any warnings.
"""
```

**4. Enable USDA Verification**

**File:** `.env`

```bash
# Enable nutrition verification for all food logging
ENABLE_NUTRITION_VERIFICATION=true

# Get free API key from: https://fdc.nal.usda.gov/api-key-signup.html
USDA_API_KEY=your_api_key_here
```

---

## Testing Strategy for Phase 1

### Test Case 1: Text Food Entry with Validation

**Scenario:** User types food description

**Test:**
```
User: "I ate 150g chicken breast and a small salad for lunch"

Expected Flow:
1. AI agent calls log_food_from_text_validated
2. Text parser extracts: ["Chicken breast 150g", "Mixed salad small"]
3. Multi-agent validation runs
4. USDA verification blends data
5. Reasonableness checks applied
6. Response includes warnings if needed

Expected Response:
✅ Logged: 150g chicken breast and a small salad

**Total:** 330 cal | P: 52g | C: 12g | F: 8g
_Confidence: high_

Foods:
• Chicken breast ✓ (150g) - 248 cal
• Mixed green salad ~ (1 cup) - 82 cal

✅ USDA verified (chicken breast)
⚠️ Salad estimate is approximate - no dressing included
```

### Test Case 2: Ambiguous Description

**Test:**
```
User: "I had a bowl from Chipotle"

Expected:
⚠️ Medium Confidence (60%)

I need more details to give you an accurate estimate:
• What protein did you choose?
• Rice type (white/brown/none)?
• Beans included?
• Toppings (guac, cheese, sour cream)?

Based on typical bowl: ~800 cal (estimate)
```

### Test Case 3: User Correction

**Test:**
```
User: "I ate a chicken breast"
AI: "Logged: 1 medium chicken breast (200g) - 330 cal"
User: "That's too high, it was smaller, maybe 120g"
AI: [Calls update_food_entry_tool]
AI: "✅ Updated to 120g - 198 cal. Correction saved!"

[Next time user says "chicken breast", system remembers to ask about size]
```

---

## Remaining Phases (Unchanged)

### Phase 2: Consensus System (3-4 days)
- Already planned - applies to both photo and text
- 3-agent validation with explanations
- See original plan

### Phase 3: Web Search Integration (2-3 days)
- Already planned - applies to both photo and text
- Fallback for uncommon foods
- See original plan

### Phase 4: Correction Feedback Loop (2-3 days)
- Already planned - applies to both photo and text
- User corrections improve future estimates
- See original plan

---

## Implementation Timeline

**Phase 1 (Updated): Enable Validation for ALL Food Logging**
- Day 1: Create `food_text_parser.py` (2-3 hours)
- Day 1: Add `log_food_from_text_validated` tool (3-4 hours)
- Day 2: Update system prompt guidance (1 hour)
- Day 2: Enable USDA verification (.env) (5 min)
- Day 2-3: Testing (photo + text validation)
- Day 3: Commit Phase 1

**Phase 2-4:** As originally planned (see main document)

**Total:** ~4 weeks (10-12 dev days)

---

## Success Criteria

✅ **Photos:** Multi-agent validation working (ALREADY DONE)
✅ **Text:** Same validation pipeline as photos
✅ **Consistency:** 90%+ accuracy for both methods
✅ **User Trust:** Transparency through warnings and confidence scores
✅ **Self-Improvement:** Corrections reduce repeat errors by 50%+

---

## Files to Create/Modify

**New Files:**
- `src/utils/food_text_parser.py`
- `src/utils/food_calibration.py` (Phase 4)
- `src/agent/nutrition_consensus.py` (Phase 2)

**Modified Files:**
- `src/agent/__init__.py` - Add tool
- `src/memory/system_prompt.py` - Add guidance
- `.env` - Enable verification
- `tests/unit/test_food_text_validation.py` (new)
- `tests/integration/test_food_accuracy_workflow.py` (update)

---

## Ready for Implementation!

This updated plan ensures validation applies to **ALL food logging methods**, exactly as the user requested.

Next step: **Implement Phase 1** 🚀
