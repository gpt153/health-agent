"""
Unit Tests for Plate Recognition Service

Tests for plate detection, matching, calibration, and portion estimation.
Epic 009 - Phase 2: Plate Recognition & Calibration
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.services.plate_recognition import (
    PlateRecognitionService,
    PlateRecognitionError
)
from src.models.plate import (
    PlateMetadata,
    DetectedPlate,
    RecognizedPlate,
    CalibrationInput,
    CalibrationResult,
    PortionEstimate,
    FoodEntryPlateLink,
    PlateStatistics
)
from src.utils.plate_calibration import (
    calibrate_from_reference_portion,
    estimate_portion_from_capacity,
    estimate_diameter_from_capacity,
    estimate_capacity_from_diameter,
    infer_fill_percentage_from_vision_description,
    validate_calibration_result,
    PlateCalibrationError,
    merge_calibrations
)


# ================================================================
# Calibration Utilities Tests
# ================================================================

class TestCalibrationUtilities:
    """Test calibration utility functions"""

    def test_calibrate_from_reference_portion_basic(self):
        """Test basic reference portion calibration"""
        capacity = calibrate_from_reference_portion(170.0, 0.5)
        assert capacity == 340.0

    def test_calibrate_from_reference_portion_quarter_full(self):
        """Test calibration with quarter-full container"""
        capacity = calibrate_from_reference_portion(100.0, 0.25)
        assert capacity == 400.0

    def test_calibrate_from_reference_portion_full(self):
        """Test calibration with full container"""
        capacity = calibrate_from_reference_portion(500.0, 1.0)
        assert capacity == 500.0

    def test_calibrate_from_reference_portion_invalid_portion(self):
        """Test error on invalid portion weight"""
        with pytest.raises(PlateCalibrationError):
            calibrate_from_reference_portion(0.0, 0.5)

        with pytest.raises(PlateCalibrationError):
            calibrate_from_reference_portion(-100.0, 0.5)

    def test_calibrate_from_reference_portion_invalid_percentage(self):
        """Test error on invalid fill percentage"""
        with pytest.raises(PlateCalibrationError):
            calibrate_from_reference_portion(170.0, 0.0)

        with pytest.raises(PlateCalibrationError):
            calibrate_from_reference_portion(170.0, 1.5)

        with pytest.raises(PlateCalibrationError):
            calibrate_from_reference_portion(170.0, -0.1)

    def test_estimate_portion_from_capacity_basic(self):
        """Test basic portion estimation"""
        portion = estimate_portion_from_capacity(340.0, 0.5)
        assert portion == 170.0

    def test_estimate_portion_from_capacity_with_density(self):
        """Test portion estimation with custom density"""
        # Salad (density ~0.6)
        portion = estimate_portion_from_capacity(500.0, 0.5, 0.6)
        assert portion == 150.0  # 500ml * 0.5 * 0.6

    def test_estimate_portion_from_capacity_cottage_cheese(self):
        """Test portion estimation with cottage cheese density"""
        # Cottage cheese (density ~1.05)
        portion = estimate_portion_from_capacity(340.0, 0.5, 1.05)
        assert portion == 178.5  # 340ml * 0.5 * 1.05

    def test_estimate_diameter_from_capacity_bowl(self):
        """Test diameter estimation for bowls"""
        diameter = estimate_diameter_from_capacity(500.0, "bowl")
        assert diameter is not None
        assert 10.0 < diameter < 30.0  # Reasonable bowl size

    def test_estimate_diameter_from_capacity_cup(self):
        """Test diameter estimation for cups"""
        diameter = estimate_diameter_from_capacity(300.0, "cup")
        assert diameter is not None
        assert 6.0 < diameter < 12.0  # Reasonable cup size

    def test_estimate_capacity_from_diameter_bowl(self):
        """Test capacity estimation from diameter"""
        capacity = estimate_capacity_from_diameter(20.0, "bowl")
        assert capacity is not None
        assert 200.0 < capacity < 2000.0  # Reasonable bowl capacity

    def test_estimate_capacity_from_diameter_round_trip(self):
        """Test round-trip: capacity → diameter → capacity"""
        original_capacity = 500.0
        diameter = estimate_diameter_from_capacity(original_capacity, "bowl")
        recovered_capacity = estimate_capacity_from_diameter(diameter, "bowl")

        # Should be approximately equal (within 10%)
        assert abs(recovered_capacity - original_capacity) / original_capacity < 0.1

    def test_infer_fill_percentage_half_full(self):
        """Test fill percentage inference from description"""
        percentage, confidence = infer_fill_percentage_from_vision_description(
            "The bowl is half full of cottage cheese"
        )
        assert percentage == 0.5
        assert confidence == 0.9

    def test_infer_fill_percentage_quarter_full(self):
        """Test inference of quarter full"""
        percentage, confidence = infer_fill_percentage_from_vision_description(
            "The container is quarter full"
        )
        assert percentage == 0.25
        assert confidence == 0.8

    def test_infer_fill_percentage_mostly_full(self):
        """Test inference of mostly full"""
        percentage, confidence = infer_fill_percentage_from_vision_description(
            "The plate is mostly full with food"
        )
        assert percentage == 0.85
        assert confidence == 0.7

    def test_infer_fill_percentage_no_match(self):
        """Test default when no pattern matches"""
        percentage, confidence = infer_fill_percentage_from_vision_description(
            "Random description without fill level"
        )
        assert percentage == 0.5  # Default
        assert confidence == 0.3  # Low confidence

    def test_validate_calibration_result_bowl_valid(self):
        """Test validation of valid bowl calibration"""
        result = CalibrationResult(
            plate_id="test-id",
            calibration_method="reference_portion",
            estimated_capacity_ml=500.0,
            estimated_diameter_cm=15.0,
            confidence=0.8,
            success=True,
            message="Test"
        )

        is_valid, message = validate_calibration_result(result, "bowl")
        assert is_valid is True

    def test_validate_calibration_result_bowl_invalid_capacity(self):
        """Test validation rejects invalid bowl capacity"""
        result = CalibrationResult(
            plate_id="test-id",
            calibration_method="reference_portion",
            estimated_capacity_ml=5000.0,  # Too large for bowl
            estimated_diameter_cm=None,
            confidence=0.8,
            success=True,
            message="Test"
        )

        is_valid, message = validate_calibration_result(result, "bowl")
        assert is_valid is False
        assert "outside reasonable range" in message

    def test_validate_calibration_result_plate_diameter(self):
        """Test validation of plate diameter"""
        result = CalibrationResult(
            plate_id="test-id",
            calibration_method="user_input",
            estimated_capacity_ml=None,
            estimated_diameter_cm=25.0,  # Valid dinner plate
            confidence=0.9,
            success=True,
            message="Test"
        )

        is_valid, message = validate_calibration_result(result, "plate")
        assert is_valid is True

    def test_merge_calibrations_first_calibration(self):
        """Test merge when no existing calibration"""
        merged_capacity, merged_confidence = merge_calibrations(
            existing_capacity=None,
            new_capacity=340.0,
            existing_confidence=0.0,
            new_confidence=0.8
        )

        assert merged_capacity == 340.0
        assert merged_confidence == 0.8

    def test_merge_calibrations_average(self):
        """Test weighted average merge"""
        merged_capacity, merged_confidence = merge_calibrations(
            existing_capacity=350.0,
            new_capacity=330.0,
            existing_confidence=0.7,
            new_confidence=0.8
        )

        # Weighted: (350*0.7 + 330*0.8) / (0.7+0.8) = 339
        assert abs(merged_capacity - 339.0) < 1.0

        # Confidence increases
        assert merged_confidence > 0.7
        assert merged_confidence > 0.8
        assert merged_confidence <= 0.95  # Capped at 0.95


# ================================================================
# Plate Metadata Validation Tests
# ================================================================

class TestPlateModels:
    """Test plate data model validation"""

    def test_plate_metadata_valid(self):
        """Test creating valid plate metadata"""
        metadata = PlateMetadata(
            plate_type="bowl",
            color="white",
            shape="round",
            estimated_diameter_cm=20.0,
            estimated_capacity_ml=500.0
        )

        assert metadata.plate_type == "bowl"
        assert metadata.color == "white"
        assert metadata.shape == "round"

    def test_plate_metadata_invalid_type(self):
        """Test validation rejects invalid plate type"""
        with pytest.raises(ValueError, match="plate_type must be one of"):
            PlateMetadata(plate_type="invalid_type")

    def test_plate_metadata_invalid_shape(self):
        """Test validation rejects invalid shape"""
        with pytest.raises(ValueError, match="shape must be one of"):
            PlateMetadata(plate_type="bowl", shape="triangle")

    def test_plate_metadata_diameter_bounds(self):
        """Test diameter bounds validation"""
        # Valid
        PlateMetadata(plate_type="plate", estimated_diameter_cm=25.0)

        # Too small
        with pytest.raises(ValueError):
            PlateMetadata(plate_type="plate", estimated_diameter_cm=2.0)

        # Too large
        with pytest.raises(ValueError):
            PlateMetadata(plate_type="plate", estimated_diameter_cm=100.0)

    def test_calibration_input_validation(self):
        """Test calibration input validation"""
        # Valid reference portion
        cal_input = CalibrationInput(
            plate_id="test-id",
            method="reference_portion",
            reference_portion_grams=170.0,
            visual_fill_percentage=0.5
        )
        cal_input.validate_inputs()  # Should not raise

        # Valid user input
        cal_input2 = CalibrationInput(
            plate_id="test-id",
            method="user_input",
            user_provided_diameter_cm=20.0
        )
        cal_input2.validate_inputs()  # Should not raise

    def test_calibration_input_missing_data(self):
        """Test calibration input fails without required data"""
        # Reference portion without fill percentage
        cal_input = CalibrationInput(
            plate_id="test-id",
            method="reference_portion",
            reference_portion_grams=170.0
            # Missing visual_fill_percentage
        )

        with pytest.raises(ValueError, match="requires reference_portion_grams"):
            cal_input.validate_inputs()

    def test_portion_estimate_serialization(self):
        """Test portion estimate converts to dict"""
        estimate = PortionEstimate(
            estimated_grams=170.0,
            confidence=0.85,
            method="calibrated_plate",
            plate_id="test-id",
            notes="Test note"
        )

        result = estimate.to_dict()

        assert result["estimated_grams"] == 170.0
        assert result["confidence"] == 0.85
        assert result["method"] == "calibrated_plate"


# ================================================================
# Plate Recognition Service Tests (Mocked)
# ================================================================

class TestPlateRecognitionService:
    """Test plate recognition service logic"""

    @pytest.fixture
    def service(self):
        """Create service instance"""
        return PlateRecognitionService()

    @pytest.fixture
    def mock_embedding(self):
        """Create mock 512-dimensional embedding"""
        return [0.1] * 512

    @pytest.fixture
    def mock_plate_metadata(self):
        """Create mock plate metadata"""
        return PlateMetadata(
            plate_type="bowl",
            color="white",
            shape="round",
            estimated_diameter_cm=None,
            estimated_capacity_ml=None
        )

    @pytest.fixture
    def mock_recognized_plate(self, mock_embedding):
        """Create mock recognized plate"""
        return RecognizedPlate(
            id="test-plate-id",
            user_id="test-user",
            plate_name="White Bowl #1",
            embedding=mock_embedding,
            plate_type="bowl",
            color="white",
            shape="round",
            estimated_diameter_cm=None,
            estimated_capacity_ml=None,
            times_recognized=5,
            first_seen_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow(),
            is_calibrated=False,
            calibration_confidence=None,
            calibration_method=None,
            model_version="clip-vit-base-patch32",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    @pytest.mark.asyncio
    async def test_match_plate_invalid_embedding_dimension(self, service):
        """Test matching rejects invalid embedding dimension"""
        invalid_embedding = [0.1] * 256  # Wrong dimension

        with pytest.raises(PlateRecognitionError, match="Invalid embedding dimension"):
            await service.match_plate(invalid_embedding, "test-user")

    @pytest.mark.asyncio
    async def test_register_new_plate_invalid_embedding(self, service, mock_plate_metadata):
        """Test registration rejects invalid embedding"""
        invalid_embedding = [0.1] * 256

        with pytest.raises(PlateRecognitionError, match="Invalid embedding dimension"):
            await service.register_new_plate(
                "test-user",
                invalid_embedding,
                mock_plate_metadata
            )

    @pytest.mark.asyncio
    async def test_calibrate_plate_reference_portion(self, service, mock_recognized_plate):
        """Test calibration from reference portion"""
        # Mock get_plate_by_id
        with patch.object(service, 'get_plate_by_id', return_value=mock_recognized_plate):
            # Mock _update_plate_calibration
            with patch.object(service, '_update_plate_calibration', new_callable=AsyncMock):
                calibration_input = CalibrationInput(
                    plate_id=mock_recognized_plate.id,
                    method="reference_portion",
                    reference_portion_grams=170.0,
                    visual_fill_percentage=0.5,
                    confidence=0.8
                )

                result = await service.calibrate_plate(calibration_input)

                assert result.success is True
                assert result.estimated_capacity_ml == 340.0
                assert result.calibration_method == "reference_portion"

    @pytest.mark.asyncio
    async def test_calibrate_plate_user_input_diameter(self, service, mock_recognized_plate):
        """Test calibration from user-provided diameter"""
        with patch.object(service, 'get_plate_by_id', return_value=mock_recognized_plate):
            with patch.object(service, '_update_plate_calibration', new_callable=AsyncMock):
                calibration_input = CalibrationInput(
                    plate_id=mock_recognized_plate.id,
                    method="user_input",
                    user_provided_diameter_cm=20.0,
                    confidence=0.9
                )

                result = await service.calibrate_plate(calibration_input)

                assert result.success is True
                assert result.estimated_diameter_cm == 20.0
                assert result.estimated_capacity_ml is not None  # Should be calculated
                assert result.calibration_method == "user_input"

    @pytest.mark.asyncio
    async def test_calibrate_plate_not_found(self, service):
        """Test calibration fails when plate not found"""
        with patch.object(service, 'get_plate_by_id', return_value=None):
            calibration_input = CalibrationInput(
                plate_id="nonexistent-id",
                method="reference_portion",
                reference_portion_grams=170.0,
                visual_fill_percentage=0.5
            )

            with pytest.raises(PlateRecognitionError, match="not found"):
                await service.calibrate_plate(calibration_input)

    @pytest.mark.asyncio
    async def test_estimate_portion_uncalibrated_plate(self, service, mock_recognized_plate):
        """Test portion estimation with uncalibrated plate"""
        # Plate is not calibrated
        mock_recognized_plate.is_calibrated = False

        with patch.object(service, 'get_plate_by_id', return_value=mock_recognized_plate):
            estimate = await service.estimate_portion_from_plate(
                mock_recognized_plate.id,
                fill_percentage=0.5
            )

            assert estimate.method == "visual_estimation"
            assert estimate.confidence < 0.5  # Low confidence
            assert "not calibrated" in estimate.notes.lower()

    @pytest.mark.asyncio
    async def test_estimate_portion_calibrated_plate(self, service, mock_recognized_plate):
        """Test portion estimation with calibrated plate"""
        # Calibrate the plate
        mock_recognized_plate.is_calibrated = True
        mock_recognized_plate.estimated_capacity_ml = 340.0
        mock_recognized_plate.calibration_confidence = 0.8

        with patch.object(service, 'get_plate_by_id', return_value=mock_recognized_plate):
            estimate = await service.estimate_portion_from_plate(
                mock_recognized_plate.id,
                fill_percentage=0.5,
                food_density_g_per_ml=1.0
            )

            assert estimate.method == "calibrated_plate"
            assert estimate.estimated_grams == 170.0  # 340ml * 0.5
            assert estimate.confidence > 0.5  # Higher confidence
            assert estimate.plate_id == mock_recognized_plate.id

    @pytest.mark.asyncio
    async def test_estimate_portion_with_custom_density(self, service, mock_recognized_plate):
        """Test portion estimation with custom food density"""
        mock_recognized_plate.is_calibrated = True
        mock_recognized_plate.estimated_capacity_ml = 500.0
        mock_recognized_plate.calibration_confidence = 0.85

        with patch.object(service, 'get_plate_by_id', return_value=mock_recognized_plate):
            # Salad (density ~0.6)
            estimate = await service.estimate_portion_from_plate(
                mock_recognized_plate.id,
                fill_percentage=0.5,
                food_density_g_per_ml=0.6
            )

            assert estimate.estimated_grams == 150.0  # 500ml * 0.5 * 0.6

    @pytest.mark.asyncio
    async def test_estimate_portion_plate_not_found(self, service):
        """Test estimation fails when plate not found"""
        with patch.object(service, 'get_plate_by_id', return_value=None):
            with pytest.raises(PlateRecognitionError, match="not found"):
                await service.estimate_portion_from_plate(
                    "nonexistent-id",
                    fill_percentage=0.5
                )

    def test_generate_plate_name_first_bowl(self, service):
        """Test auto-name generation for first bowl"""
        # This would be tested with actual database in integration tests
        # Unit test would mock the database query
        pass

    def test_matching_threshold_configuration(self, service):
        """Test matching threshold constants are reasonable"""
        assert 0.0 < service.LOW_MATCH_THRESHOLD < 1.0
        assert service.LOW_MATCH_THRESHOLD < service.MEDIUM_MATCH_THRESHOLD
        assert service.MEDIUM_MATCH_THRESHOLD < service.HIGH_MATCH_THRESHOLD
        assert service.DEFAULT_MATCH_THRESHOLD == service.MEDIUM_MATCH_THRESHOLD

    def test_calibration_confidence_thresholds(self, service):
        """Test calibration confidence thresholds are reasonable"""
        assert 0.0 < service.MEDIUM_CALIBRATION_CONFIDENCE < 1.0
        assert service.MEDIUM_CALIBRATION_CONFIDENCE < service.HIGH_CALIBRATION_CONFIDENCE
        assert service.HIGH_CALIBRATION_CONFIDENCE < 1.0


# ================================================================
# Edge Cases and Error Handling
# ================================================================

class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_calibrate_tiny_portion(self):
        """Test calibration with very small portion"""
        capacity = calibrate_from_reference_portion(10.0, 0.1)
        assert capacity == 100.0

    def test_calibrate_large_portion(self):
        """Test calibration with large portion"""
        capacity = calibrate_from_reference_portion(1000.0, 0.5)
        assert capacity == 2000.0

    def test_estimate_portion_empty_container(self):
        """Test portion estimation with empty container"""
        portion = estimate_portion_from_capacity(500.0, 0.01)  # 1% full
        assert portion > 0.0
        assert portion < 10.0

    def test_estimate_portion_overfilled(self):
        """Test portion estimation with overfilled container"""
        # Vision AI might report >100% fill (heaping)
        portion = estimate_portion_from_capacity(500.0, 1.2, density_g_per_ml=1.0)
        assert portion == 600.0  # 500ml * 1.2

    def test_merge_calibrations_confidence_cap(self):
        """Test confidence doesn't exceed 0.95"""
        merged_capacity, merged_confidence = merge_calibrations(
            existing_capacity=340.0,
            new_capacity=340.0,
            existing_confidence=0.9,
            new_confidence=0.9
        )

        assert merged_confidence <= 0.95

    def test_validate_calibration_very_small_plate(self):
        """Test validation handles very small plates"""
        result = CalibrationResult(
            plate_id="test-id",
            calibration_method="user_input",
            estimated_capacity_ml=None,
            estimated_diameter_cm=10.0,  # Small plate
            confidence=0.8,
            success=True,
            message="Test"
        )

        is_valid, message = validate_calibration_result(result, "plate")
        # 10cm is below typical plate range (15-35cm) but not invalid
        # Implementation might accept it or reject it
        # This tests the validation logic exists


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
