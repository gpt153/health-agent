"""
Integration Tests for Plate Recognition Service

Full workflow tests with real database operations.
Epic 009 - Phase 2: Plate Recognition & Calibration
"""
import pytest
import asyncio
from pathlib import Path
from datetime import datetime
import uuid

from src.services.plate_recognition import (
    get_plate_recognition_service,
    PlateRecognitionService,
    PlateRecognitionError
)
from src.services.image_embedding import get_embedding_service
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
from src.db.connection import db


# ================================================================
# Test Fixtures
# ================================================================

@pytest.fixture
async def cleanup_test_data():
    """Clean up test data after each test"""
    yield

    # Cleanup test plates and links
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM food_entry_plates WHERE user_id LIKE 'test_%'"
            )
            await cur.execute(
                "DELETE FROM recognized_plates WHERE user_id LIKE 'test_%'"
            )
            await conn.commit()


@pytest.fixture
def test_user_id():
    """Generate unique test user ID"""
    return f"test_user_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_food_entry_id():
    """Generate test food entry ID"""
    return str(uuid.uuid4())


@pytest.fixture
def mock_embedding():
    """Create mock 512-dimensional embedding"""
    return [0.1 + (i * 0.001) for i in range(512)]


@pytest.fixture
def mock_plate_metadata():
    """Create mock plate metadata"""
    return PlateMetadata(
        plate_type="bowl",
        color="white",
        shape="round",
        estimated_diameter_cm=None,
        estimated_capacity_ml=None
    )


@pytest.fixture
async def plate_service():
    """Get plate recognition service instance"""
    return get_plate_recognition_service()


# ================================================================
# Database Integration Tests
# ================================================================

class TestPlateRegistration:
    """Test plate registration and storage"""

    @pytest.mark.asyncio
    async def test_register_new_plate_stores_in_database(
        self, plate_service, test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """Test that registering a plate creates database entry"""
        # Register plate
        plate = await plate_service.register_new_plate(
            test_user_id,
            mock_embedding,
            mock_plate_metadata
        )

        # Verify plate was created
        assert plate.id is not None
        assert plate.user_id == test_user_id
        assert plate.plate_name == "White Bowl #1"
        assert plate.plate_type == "bowl"
        assert plate.times_recognized == 1
        assert plate.is_calibrated is False

        # Verify in database
        retrieved_plate = await plate_service.get_plate_by_id(plate.id)
        assert retrieved_plate is not None
        assert retrieved_plate.id == plate.id
        assert retrieved_plate.user_id == test_user_id

    @pytest.mark.asyncio
    async def test_register_multiple_plates_increments_names(
        self, plate_service, test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """Test that multiple plates get sequential names"""
        # Register first plate
        plate1 = await plate_service.register_new_plate(
            test_user_id,
            mock_embedding,
            mock_plate_metadata
        )
        assert plate1.plate_name == "White Bowl #1"

        # Register second plate
        embedding2 = [x + 0.1 for x in mock_embedding]
        plate2 = await plate_service.register_new_plate(
            test_user_id,
            embedding2,
            mock_plate_metadata
        )
        assert plate2.plate_name == "White Bowl #2"

        # Register third plate
        embedding3 = [x + 0.2 for x in mock_embedding]
        plate3 = await plate_service.register_new_plate(
            test_user_id,
            embedding3,
            mock_plate_metadata
        )
        assert plate3.plate_name == "White Bowl #3"


class TestPlateMatching:
    """Test plate matching using pgvector"""

    @pytest.mark.asyncio
    async def test_match_exact_plate(
        self, plate_service, test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """Test matching an exact plate"""
        # Register plate
        original_plate = await plate_service.register_new_plate(
            test_user_id,
            mock_embedding,
            mock_plate_metadata
        )

        # Match with same embedding
        matched_plate = await plate_service.match_plate(
            mock_embedding,
            test_user_id,
            threshold=0.85
        )

        assert matched_plate is not None
        assert matched_plate.id == original_plate.id

    @pytest.mark.asyncio
    async def test_match_similar_plate(
        self, plate_service, test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """Test matching a very similar plate"""
        # Register plate
        original_plate = await plate_service.register_new_plate(
            test_user_id,
            mock_embedding,
            mock_plate_metadata
        )

        # Create slightly different embedding (should still match)
        similar_embedding = [x + 0.001 for x in mock_embedding]

        matched_plate = await plate_service.match_plate(
            similar_embedding,
            test_user_id,
            threshold=0.85
        )

        # Should still match due to high similarity
        assert matched_plate is not None
        assert matched_plate.id == original_plate.id

    @pytest.mark.asyncio
    async def test_no_match_for_different_plate(
        self, plate_service, test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """Test that different plate doesn't match"""
        # Register plate
        await plate_service.register_new_plate(
            test_user_id,
            mock_embedding,
            mock_plate_metadata
        )

        # Create very different embedding
        different_embedding = [0.9 - x for x in mock_embedding]

        matched_plate = await plate_service.match_plate(
            different_embedding,
            test_user_id,
            threshold=0.85
        )

        # Should not match
        assert matched_plate is None

    @pytest.mark.asyncio
    async def test_user_isolation_in_matching(
        self, plate_service, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """Test that plates are isolated by user"""
        user1 = f"test_user_{uuid.uuid4().hex[:8]}"
        user2 = f"test_user_{uuid.uuid4().hex[:8]}"

        # User 1 registers a plate
        await plate_service.register_new_plate(
            user1,
            mock_embedding,
            mock_plate_metadata
        )

        # User 2 tries to match (should not find user 1's plate)
        matched_plate = await plate_service.match_plate(
            mock_embedding,
            user2,
            threshold=0.85
        )

        assert matched_plate is None


class TestPlateCalibration:
    """Test plate calibration workflows"""

    @pytest.mark.asyncio
    async def test_calibrate_from_reference_portion(
        self, plate_service, test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """Test calibration from reference portion"""
        # Register plate
        plate = await plate_service.register_new_plate(
            test_user_id,
            mock_embedding,
            mock_plate_metadata
        )

        # Calibrate
        calibration_input = CalibrationInput(
            plate_id=plate.id,
            method="reference_portion",
            reference_portion_grams=170.0,
            visual_fill_percentage=0.5,
            confidence=0.8
        )

        result = await plate_service.calibrate_plate(calibration_input)

        assert result.success is True
        assert result.estimated_capacity_ml == 340.0
        assert result.confidence == 0.8

        # Verify plate is marked as calibrated in database
        calibrated_plate = await plate_service.get_plate_by_id(plate.id)
        assert calibrated_plate.is_calibrated is True
        assert calibrated_plate.estimated_capacity_ml == 340.0
        assert calibrated_plate.calibration_confidence == 0.8

    @pytest.mark.asyncio
    async def test_calibrate_from_user_input(
        self, plate_service, test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """Test calibration from user-provided dimensions"""
        # Register plate
        plate = await plate_service.register_new_plate(
            test_user_id,
            mock_embedding,
            mock_plate_metadata
        )

        # Calibrate
        calibration_input = CalibrationInput(
            plate_id=plate.id,
            method="user_input",
            user_provided_diameter_cm=20.0,
            confidence=0.9
        )

        result = await plate_service.calibrate_plate(calibration_input)

        assert result.success is True
        assert result.estimated_diameter_cm == 20.0
        assert result.estimated_capacity_ml is not None  # Should be calculated

        # Verify in database
        calibrated_plate = await plate_service.get_plate_by_id(plate.id)
        assert calibrated_plate.is_calibrated is True
        assert calibrated_plate.estimated_diameter_cm == 20.0

    @pytest.mark.asyncio
    async def test_multiple_calibrations_merge(
        self, plate_service, test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """Test that multiple calibrations merge correctly"""
        # Register plate
        plate = await plate_service.register_new_plate(
            test_user_id,
            mock_embedding,
            mock_plate_metadata
        )

        # First calibration
        calibration1 = CalibrationInput(
            plate_id=plate.id,
            method="reference_portion",
            reference_portion_grams=170.0,
            visual_fill_percentage=0.5,
            confidence=0.7
        )
        result1 = await plate_service.calibrate_plate(calibration1)
        assert result1.estimated_capacity_ml == 340.0

        # Second calibration (slightly different)
        calibration2 = CalibrationInput(
            plate_id=plate.id,
            method="reference_portion",
            reference_portion_grams=160.0,
            visual_fill_percentage=0.5,
            confidence=0.8
        )
        result2 = await plate_service.calibrate_plate(calibration2)

        # Should be weighted average
        # (340*0.7 + 320*0.8) / (0.7+0.8) ≈ 329
        assert 325.0 < result2.estimated_capacity_ml < 335.0

        # Confidence should increase
        assert result2.confidence > 0.7


class TestFoodEntryPlateLink:
    """Test linking food entries to plates"""

    @pytest.mark.asyncio
    async def test_link_food_entry_to_plate(
        self, plate_service, test_user_id, test_food_entry_id,
        mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """Test linking a food entry to a plate"""
        # Register plate
        plate = await plate_service.register_new_plate(
            test_user_id,
            mock_embedding,
            mock_plate_metadata
        )

        # Link food entry
        link = await plate_service.link_food_entry_to_plate(
            food_entry_id=test_food_entry_id,
            recognized_plate_id=plate.id,
            user_id=test_user_id,
            confidence_score=0.92,
            detection_method="auto_detected"
        )

        assert link.food_entry_id == test_food_entry_id
        assert link.recognized_plate_id == plate.id
        assert link.confidence_score == 0.92

    @pytest.mark.asyncio
    async def test_link_updates_plate_usage(
        self, plate_service, test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """Test that linking updates plate usage statistics"""
        # Register plate
        plate = await plate_service.register_new_plate(
            test_user_id,
            mock_embedding,
            mock_plate_metadata
        )

        initial_count = plate.times_recognized
        assert initial_count == 1

        # Link first food entry
        await plate_service.link_food_entry_to_plate(
            food_entry_id=str(uuid.uuid4()),
            recognized_plate_id=plate.id,
            user_id=test_user_id,
            confidence_score=0.9
        )

        # Check usage updated
        updated_plate = await plate_service.get_plate_by_id(plate.id)
        assert updated_plate.times_recognized == 2

        # Link second food entry
        await plate_service.link_food_entry_to_plate(
            food_entry_id=str(uuid.uuid4()),
            recognized_plate_id=plate.id,
            user_id=test_user_id,
            confidence_score=0.85
        )

        # Check usage updated again
        updated_plate2 = await plate_service.get_plate_by_id(plate.id)
        assert updated_plate2.times_recognized == 3


class TestPortionEstimation:
    """Test portion estimation from calibrated plates"""

    @pytest.mark.asyncio
    async def test_estimate_portion_from_calibrated_plate(
        self, plate_service, test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """Test portion estimation with calibrated plate"""
        # Register and calibrate plate
        plate = await plate_service.register_new_plate(
            test_user_id,
            mock_embedding,
            mock_plate_metadata
        )

        calibration_input = CalibrationInput(
            plate_id=plate.id,
            method="reference_portion",
            reference_portion_grams=170.0,
            visual_fill_percentage=0.5,
            confidence=0.8
        )
        await plate_service.calibrate_plate(calibration_input)

        # Estimate portion
        estimate = await plate_service.estimate_portion_from_plate(
            plate_id=plate.id,
            fill_percentage=0.5,
            food_density_g_per_ml=1.0
        )

        assert estimate.method == "calibrated_plate"
        assert estimate.estimated_grams == 170.0
        assert estimate.confidence > 0.5
        assert estimate.plate_id == plate.id

    @pytest.mark.asyncio
    async def test_estimate_portion_uncalibrated_fallback(
        self, plate_service, test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """Test portion estimation falls back gracefully when uncalibrated"""
        # Register but don't calibrate
        plate = await plate_service.register_new_plate(
            test_user_id,
            mock_embedding,
            mock_plate_metadata
        )

        # Estimate portion
        estimate = await plate_service.estimate_portion_from_plate(
            plate_id=plate.id,
            fill_percentage=0.5
        )

        assert estimate.method == "visual_estimation"
        assert estimate.confidence < 0.5  # Low confidence
        assert "not calibrated" in estimate.notes.lower()


class TestPlateStatistics:
    """Test user plate statistics"""

    @pytest.mark.asyncio
    async def test_get_user_plate_statistics(
        self, plate_service, test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """Test retrieving user plate statistics"""
        # Register multiple plates
        plate1 = await plate_service.register_new_plate(
            test_user_id,
            mock_embedding,
            mock_plate_metadata
        )

        embedding2 = [x + 0.1 for x in mock_embedding]
        plate2 = await plate_service.register_new_plate(
            test_user_id,
            embedding2,
            mock_plate_metadata
        )

        # Calibrate one plate
        calibration = CalibrationInput(
            plate_id=plate1.id,
            method="reference_portion",
            reference_portion_grams=170.0,
            visual_fill_percentage=0.5,
            confidence=0.8
        )
        await plate_service.calibrate_plate(calibration)

        # Link food entries to make plate1 more used
        for _ in range(3):
            await plate_service.link_food_entry_to_plate(
                food_entry_id=str(uuid.uuid4()),
                recognized_plate_id=plate1.id,
                user_id=test_user_id,
                confidence_score=0.9
            )

        # Get statistics
        stats = await plate_service.get_user_plate_statistics(test_user_id)

        assert stats.total_plates == 2
        assert stats.calibrated_plates == 1
        assert stats.total_recognitions >= 4  # 1 initial + 3 links for plate1, + 1 for plate2
        assert stats.most_used_plate_id == plate1.id

    @pytest.mark.asyncio
    async def test_empty_statistics_for_new_user(
        self, plate_service, cleanup_test_data
    ):
        """Test statistics for user with no plates"""
        new_user = f"test_user_{uuid.uuid4().hex[:8]}"

        stats = await plate_service.get_user_plate_statistics(new_user)

        assert stats.total_plates == 0
        assert stats.calibrated_plates == 0
        assert stats.total_recognitions == 0
        assert stats.most_used_plate_id is None


# ================================================================
# Full Workflow Integration Tests
# ================================================================

class TestFullWorkflow:
    """Test complete plate recognition workflows"""

    @pytest.mark.asyncio
    async def test_complete_plate_lifecycle(
        self, plate_service, test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """Test full lifecycle: register → link → calibrate → estimate"""
        # 1. Register plate
        plate = await plate_service.register_new_plate(
            test_user_id,
            mock_embedding,
            mock_plate_metadata
        )
        assert plate.is_calibrated is False

        # 2. Link to food entry
        food_entry_id = str(uuid.uuid4())
        link = await plate_service.link_food_entry_to_plate(
            food_entry_id=food_entry_id,
            recognized_plate_id=plate.id,
            user_id=test_user_id,
            confidence_score=0.88
        )
        assert link is not None

        # 3. Calibrate from reference portion
        calibration = CalibrationInput(
            plate_id=plate.id,
            method="reference_portion",
            reference_portion_grams=170.0,
            visual_fill_percentage=0.5,
            confidence=0.8
        )
        result = await plate_service.calibrate_plate(calibration)
        assert result.success is True

        # 4. Estimate portion for new meal
        estimate = await plate_service.estimate_portion_from_plate(
            plate_id=plate.id,
            fill_percentage=0.75,
            food_density_g_per_ml=1.0
        )
        assert estimate.method == "calibrated_plate"
        assert estimate.estimated_grams == 255.0  # 340ml * 0.75

        # 5. Verify statistics
        stats = await plate_service.get_user_plate_statistics(test_user_id)
        assert stats.total_plates == 1
        assert stats.calibrated_plates == 1

    @pytest.mark.asyncio
    async def test_match_or_register_workflow(
        self, plate_service, test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """Test workflow: try to match, register if not found"""
        # First attempt - no existing plates
        matched = await plate_service.match_plate(
            mock_embedding,
            test_user_id,
            threshold=0.85
        )
        assert matched is None

        # Register new plate
        registered = await plate_service.register_new_plate(
            test_user_id,
            mock_embedding,
            mock_plate_metadata
        )

        # Second attempt - should match now
        matched = await plate_service.match_plate(
            mock_embedding,
            test_user_id,
            threshold=0.85
        )
        assert matched is not None
        assert matched.id == registered.id


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
