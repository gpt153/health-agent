"""Tests for multi-agent nutrition validator"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.agent.nutrition_validator import NutritionValidator
from src.models.food import FoodItem, FoodMacros, VisionAnalysisResult


@pytest.fixture
def validator():
    """Create validator instance"""
    return NutritionValidator()


@pytest.fixture
def good_vision_result():
    """Vision result with reasonable estimates"""
    return VisionAnalysisResult(
        foods=[
            FoodItem(
                name="Chicken Breast",
                quantity="100g",
                calories=165,
                macros=FoodMacros(protein=31.0, carbs=0.0, fat=3.6)
            )
        ],
        confidence="high",
        clarifying_questions=[],
        timestamp=None
    )


@pytest.fixture
def bad_vision_result():
    """Vision result with unreasonable estimates"""
    return VisionAnalysisResult(
        foods=[
            FoodItem(
                name="Small Salad",
                quantity="200g",
                calories=450,  # Unreasonable!
                macros=FoodMacros(protein=5.0, carbs=10.0, fat=40.0)
            )
        ],
        confidence="high",
        clarifying_questions=[],
        timestamp=None
    )


@pytest.mark.asyncio
async def test_validate_good_estimates(validator, good_vision_result):
    """Test validation of reasonable estimates"""
    validated_result, warnings = await validator.validate(
        vision_result=good_vision_result,
        photo_path="/tmp/test.jpg",
        enable_cross_validation=False  # Skip cross-validation for this test
    )

    # Should pass validation with no warnings
    assert len(warnings) == 0
    assert validated_result.foods[0].name == "Chicken Breast"
    assert validated_result.foods[0].calories == 165


@pytest.mark.asyncio
async def test_validate_bad_estimates(validator, bad_vision_result):
    """Test validation catches unreasonable estimates"""
    validated_result, warnings = await validator.validate(
        vision_result=bad_vision_result,
        photo_path="/tmp/test.jpg",
        enable_cross_validation=False
    )

    # Should have warnings about unreasonable salad calories
    assert len(warnings) > 0
    assert any("Salad" in w and "HIGH" in w for w in warnings)


@pytest.mark.asyncio
async def test_cross_model_comparison(validator):
    """Test cross-model validation detects discrepancies"""
    result1 = VisionAnalysisResult(
        foods=[
            FoodItem(
                name="Apple",
                quantity="1 item",
                calories=100,
                macros=FoodMacros(protein=0.5, carbs=25.0, fat=0.3)
            )
        ],
        confidence="high",
        clarifying_questions=[],
        timestamp=None
    )

    result2 = VisionAnalysisResult(
        foods=[
            FoodItem(
                name="Apple",
                quantity="1 item",
                calories=200,  # 100% difference!
                macros=FoodMacros(protein=0.5, carbs=50.0, fat=0.3)
            )
        ],
        confidence="high",
        clarifying_questions=[],
        timestamp=None
    )

    warnings = validator._compare_results(result1, result2)

    # Should detect significant discrepancy
    assert len(warnings) > 0
    assert any("disagreement" in w.lower() for w in warnings)


@pytest.mark.asyncio
async def test_blend_results(validator):
    """Test blending of two vision results"""
    result1 = VisionAnalysisResult(
        foods=[
            FoodItem(
                name="Banana",
                quantity="1 item",
                calories=100,
                macros=FoodMacros(protein=1.0, carbs=25.0, fat=0.3)
            )
        ],
        confidence="high",
        clarifying_questions=[],
        timestamp=None
    )

    result2 = VisionAnalysisResult(
        foods=[
            FoodItem(
                name="Banana",
                quantity="1 item",
                calories=120,
                macros=FoodMacros(protein=1.2, carbs=28.0, fat=0.4)
            )
        ],
        confidence="high",
        clarifying_questions=[],
        timestamp=None
    )

    blended = validator._blend_results(result1, result2)

    # Should average the values
    assert blended.foods[0].calories == 110  # (100 + 120) / 2
    assert blended.foods[0].macros.protein == 1.1  # (1.0 + 1.2) / 2
    assert blended.foods[0].macros.carbs == 26.5  # (25.0 + 28.0) / 2
    assert blended.confidence == "medium"  # Blended results = medium confidence


@pytest.mark.asyncio
async def test_usda_comparison(validator):
    """Test comparison with USDA verified data"""
    ai_foods = [
        FoodItem(
            name="Rice",
            quantity="100g",
            calories=200,  # AI estimate
            macros=FoodMacros(protein=4.0, carbs=44.0, fat=0.5)
        )
    ]

    usda_foods = [
        FoodItem(
            name="Rice",
            quantity="100g",
            calories=130,  # USDA says 130
            macros=FoodMacros(protein=2.7, carbs=28.0, fat=0.3),
            verification_source="usda",
            confidence_score=0.9
        )
    ]

    warnings = validator._compare_with_usda(ai_foods, usda_foods)

    # Should detect discrepancy (>25% difference)
    assert len(warnings) > 0
    assert any("USDA" in w and "difference" in w for w in warnings)


@pytest.mark.asyncio
async def test_multiple_validation_issues(validator, bad_vision_result):
    """Test that multiple validation issues trigger review flag"""
    # Create result with multiple problems
    problematic_result = VisionAnalysisResult(
        foods=[
            FoodItem(
                name="Salad",
                quantity="200g",
                calories=450,  # Too high!
                macros=FoodMacros(protein=5.0, carbs=10.0, fat=40.0)
            ),
            FoodItem(
                name="Chicken Breast",
                quantity="100g",
                calories=650,  # Way too high!
                macros=FoodMacros(protein=20.0, carbs=0.0, fat=65.0)
            ),
        ],
        confidence="high",
        clarifying_questions=[],
        timestamp=None
    )

    validated_result, warnings = await validator.validate(
        vision_result=problematic_result,
        photo_path="/tmp/test.jpg",
        enable_cross_validation=False
    )

    # Should have multiple warnings and a review flag
    assert len(warnings) >= 3
    assert any("MULTIPLE VALIDATION ISSUES" in w for w in warnings)


@pytest.mark.asyncio
async def test_validator_singleton():
    """Test that get_validator returns singleton"""
    from src.agent.nutrition_validator import get_validator

    validator1 = get_validator()
    validator2 = get_validator()

    assert validator1 is validator2  # Should be same instance


@pytest.mark.asyncio
async def test_blend_different_food_counts(validator):
    """Test blending fails gracefully with different food counts"""
    result1 = VisionAnalysisResult(
        foods=[
            FoodItem(
                name="Food1",
                quantity="100g",
                calories=100,
                macros=FoodMacros(protein=10.0, carbs=10.0, fat=1.0)
            )
        ],
        confidence="high",
        clarifying_questions=[],
        timestamp=None
    )

    result2 = VisionAnalysisResult(
        foods=[
            FoodItem(
                name="Food1",
                quantity="100g",
                calories=100,
                macros=FoodMacros(protein=10.0, carbs=10.0, fat=1.0)
            ),
            FoodItem(
                name="Food2",
                quantity="50g",
                calories=50,
                macros=FoodMacros(protein=5.0, carbs=5.0, fat=0.5)
            ),
        ],
        confidence="high",
        clarifying_questions=[],
        timestamp=None
    )

    blended = validator._blend_results(result1, result2)

    # Should return primary result when counts don't match
    assert len(blended.foods) == 1
    assert blended.foods[0].name == "Food1"
