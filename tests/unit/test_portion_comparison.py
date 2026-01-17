"""
Unit Tests for Portion Comparison Service

Tests for Epic 009 - Phase 4: Portion Comparison
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.services.portion_comparison import (
    PortionComparisonService,
    PortionComparisonError
)
from src.models.portion import (
    BoundingBox,
    FoodItemDetection,
    PortionComparison,
    ComparisonContext,
    PortionEstimateAccuracy,
    PortionAccuracyStats
)


class TestBoundingBox:
    """Test BoundingBox model"""

    def test_bounding_box_creation(self):
        """Test creating a bounding box"""
        bbox = BoundingBox(x=0.1, y=0.2, width=0.5, height=0.6)

        assert bbox.x == 0.1
        assert bbox.y == 0.2
        assert bbox.width == 0.5
        assert bbox.height == 0.6

    def test_bounding_box_area_calculation(self):
        """Test area calculation"""
        bbox = BoundingBox(x=0.0, y=0.0, width=0.5, height=0.4)
        assert bbox.area == 0.2

    def test_bounding_box_center(self):
        """Test center calculation"""
        bbox = BoundingBox(x=0.1, y=0.2, width=0.4, height=0.6)
        assert bbox.center_x == 0.3  # 0.1 + 0.4/2
        assert bbox.center_y == 0.5  # 0.2 + 0.6/2

    def test_bounding_box_validation(self):
        """Test bbox validation (0-1 range)"""
        with pytest.raises(ValueError):
            BoundingBox(x=-0.1, y=0.0, width=0.5, height=0.5)

        with pytest.raises(ValueError):
            BoundingBox(x=0.0, y=1.5, width=0.5, height=0.5)


class TestPortionComparison:
    """Test PortionComparison model"""

    def test_portion_comparison_creation(self):
        """Test creating a portion comparison"""
        comp = PortionComparison(
            id="test-id",
            user_id="123",
            current_food_entry_id="current-entry",
            reference_food_entry_id="ref-entry",
            item_name="rice",
            current_area=0.3,
            reference_area=0.2,
            area_difference_ratio=0.5,  # 50% increase
            estimated_grams_difference=25.0,
            confidence=0.8
        )

        assert comp.percentage_difference == 50.0
        assert comp.is_larger is True
        assert comp.is_smaller is False

    def test_portion_comparison_smaller(self):
        """Test smaller portion detection"""
        comp = PortionComparison(
            id="test-id",
            user_id="123",
            current_food_entry_id="current",
            reference_food_entry_id="ref",
            item_name="chicken",
            current_area=0.15,
            reference_area=0.2,
            area_difference_ratio=-0.25,  # 25% decrease
            confidence=0.7
        )

        assert comp.is_smaller is True
        assert comp.is_larger is False
        assert comp.percentage_difference == -25.0

    def test_human_readable_difference(self):
        """Test human-readable difference generation"""
        comp = PortionComparison(
            id="test",
            user_id="123",
            current_food_entry_id="c",
            reference_food_entry_id="r",
            item_name="rice",
            current_area=0.3,
            reference_area=0.2,
            area_difference_ratio=0.5,
            confidence=0.8
        )

        diff = comp.get_human_readable_difference()
        assert "Larger portion" in diff
        assert "50%" in diff


class TestPortionComparisonService:
    """Test PortionComparisonService"""

    @pytest.fixture
    def service(self):
        """Create service instance"""
        return PortionComparisonService()

    def test_service_initialization(self, service):
        """Test service initializes correctly"""
        assert service.visual_search_service is not None
        assert service.plate_service is not None

    def test_create_heuristic_bbox_single_item(self, service):
        """Test heuristic bbox for single item"""
        bbox = service._create_heuristic_bbox(0, 1)

        assert bbox.x == 0.15
        assert bbox.y == 0.15
        assert bbox.width == 0.7
        assert bbox.height == 0.7

    def test_create_heuristic_bbox_two_items(self, service):
        """Test heuristic bbox for two items"""
        bbox1 = service._create_heuristic_bbox(0, 2)
        bbox2 = service._create_heuristic_bbox(1, 2)

        # Should split horizontally
        assert bbox1.x < bbox2.x

    def test_items_match_exact(self, service):
        """Test exact item name matching"""
        assert service._items_match("rice", "rice") is True
        assert service._items_match("chicken", "chicken") is True

    def test_items_match_substring(self, service):
        """Test substring matching"""
        assert service._items_match("rice", "fried rice") is True
        assert service._items_match("chicken breast", "chicken") is True

    def test_items_match_no_match(self, service):
        """Test non-matching items"""
        assert service._items_match("rice", "chicken") is False
        assert service._items_match("apple", "orange") is False

    def test_get_food_density(self, service):
        """Test food density lookup"""
        assert service._get_food_density("rice") == 0.75
        assert service._get_food_density("chicken breast") == 1.1
        assert service._get_food_density("unknown food") == 1.0  # Default

    def test_calculate_estimate_confidence(self, service):
        """Test confidence calculation"""
        # Small difference, calibrated plate → high confidence
        conf = service._calculate_estimate_confidence(0.05, True, 10.0)
        assert conf > 0.8

        # Large difference, no calibration → lower confidence
        conf = service._calculate_estimate_confidence(0.6, False, 300.0)
        assert conf < 0.6

    @pytest.mark.asyncio
    async def test_calculate_portion_estimate(self, service):
        """Test portion estimate calculation"""
        estimated_diff, confidence = await service.calculate_portion_estimate(
            area_difference_ratio=0.5,  # 50% increase
            reference_grams=100.0,
            plate_capacity_ml=500.0,
            food_density=1.0
        )

        assert estimated_diff == 50.0  # 50% of 100g
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_generate_comparison_context(self, service):
        """Test comparison context generation"""
        comparisons = [
            PortionComparison(
                id="1",
                user_id="123",
                current_food_entry_id="c",
                reference_food_entry_id="r",
                item_name="rice",
                current_area=0.3,
                reference_area=0.2,
                area_difference_ratio=0.5,
                estimated_grams_difference=50.0,
                confidence=0.8
            ),
            PortionComparison(
                id="2",
                user_id="123",
                current_food_entry_id="c",
                reference_food_entry_id="r",
                item_name="chicken",
                current_area=0.15,
                reference_area=0.2,
                area_difference_ratio=-0.25,
                estimated_grams_difference=-25.0,
                confidence=0.7
            )
        ]

        context = await service.generate_comparison_context(
            comparisons,
            plate_name="Blue Plate #1"
        )

        assert len(context.portion_differences) == 2
        assert any("rice" in diff.lower() for diff in context.portion_differences)
        assert any("chicken" in diff.lower() for diff in context.portion_differences)
        assert context.plate_info == "Using your Blue Plate #1"


class TestComparisonContext:
    """Test ComparisonContext model"""

    def test_comparison_context_to_prompt_text(self):
        """Test conversion to prompt text"""
        context = ComparisonContext(
            portion_differences=["More rice (+30g)", "Less chicken (-20g)"],
            plate_info="Using your white plate #1",
            confidence_notes="Medium confidence estimate",
            summary="Similar to previous meal"
        )

        prompt_text = context.to_prompt_text()

        assert "PORTION COMPARISON" in prompt_text
        assert "More rice" in prompt_text
        assert "Less chicken" in prompt_text
        assert "white plate #1" in prompt_text
        assert "Medium confidence" in prompt_text

    def test_format_time_ago(self):
        """Test time ago formatting"""
        context = ComparisonContext(
            confidence_notes="test",
            reference_date=datetime(2024, 1, 15, 12, 0)
        )

        # Mock datetime.now() to control time
        with patch('src.models.portion.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 16, 12, 0)
            time_str = context._format_time_ago(context.reference_date)
            assert time_str == "yesterday"


class TestPortionAccuracyStats:
    """Test PortionAccuracyStats model"""

    def test_accuracy_stats_creation(self):
        """Test creating accuracy stats"""
        stats = PortionAccuracyStats(
            total_estimates=100,
            avg_variance_percentage=15.5,
            within_20_percent=85,
            within_10_percent=60,
            accuracy_rate=85.0
        )

        assert stats.total_estimates == 100
        assert stats.excellent_rate == 60.0  # 60/100 * 100

    def test_excellent_rate_no_estimates(self):
        """Test excellent rate with no estimates"""
        stats = PortionAccuracyStats(
            total_estimates=0,
            avg_variance_percentage=0.0,
            within_20_percent=0,
            within_10_percent=0,
            accuracy_rate=0.0
        )

        assert stats.excellent_rate == 0.0
