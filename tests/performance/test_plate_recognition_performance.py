"""
Performance Benchmarks for Plate Recognition Service

Tests performance targets for plate detection, matching, and estimation.
Epic 009 - Phase 2: Plate Recognition & Calibration
"""
import pytest
import asyncio
import time
from pathlib import Path
import uuid

from src.services.plate_recognition import get_plate_recognition_service
from src.models.plate import PlateMetadata, CalibrationInput
from src.db.connection import db


# ================================================================
# Test Fixtures
# ================================================================

@pytest.fixture
async def cleanup_test_data():
    """Clean up test data after each test"""
    yield

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM food_entry_plates WHERE user_id LIKE 'perf_test_%'"
            )
            await cur.execute(
                "DELETE FROM recognized_plates WHERE user_id LIKE 'perf_test_%'"
            )
            await conn.commit()


@pytest.fixture
def perf_test_user_id():
    """Generate unique performance test user ID"""
    return f"perf_test_user_{uuid.uuid4().hex[:8]}"


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
        shape="round"
    )


@pytest.fixture
async def plate_service():
    """Get plate recognition service instance"""
    return get_plate_recognition_service()


@pytest.fixture
async def setup_test_plates(plate_service, perf_test_user_id, cleanup_test_data):
    """Set up test plates for performance testing"""
    plates = []

    # Create 100 test plates
    for i in range(100):
        embedding = [0.1 + (i * 0.01) + (j * 0.001) for j in range(512)]
        metadata = PlateMetadata(
            plate_type="bowl" if i % 2 == 0 else "plate",
            color="white" if i % 3 == 0 else "blue",
            shape="round"
        )

        plate = await plate_service.register_new_plate(
            perf_test_user_id,
            embedding,
            metadata
        )
        plates.append(plate)

    return plates


# ================================================================
# Performance Benchmarks
# ================================================================

class TestPlateMatchingPerformance:
    """Test plate matching speed with pgvector"""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_plate_matching_speed_small_dataset(
        self, plate_service, perf_test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """
        Test matching speed with 10 plates
        Target: <100ms
        """
        # Register 10 plates
        for i in range(10):
            embedding = [x + (i * 0.01) for x in mock_embedding]
            await plate_service.register_new_plate(
                perf_test_user_id,
                embedding,
                mock_plate_metadata
            )

        # Benchmark matching
        query_embedding = [x + 0.05 for x in mock_embedding]

        start_time = time.time()
        matched_plate = await plate_service.match_plate(
            query_embedding,
            perf_test_user_id,
            threshold=0.85
        )
        elapsed_ms = (time.time() - start_time) * 1000

        print(f"\nPlate matching (10 plates): {elapsed_ms:.2f}ms")
        assert elapsed_ms < 100, f"Matching took {elapsed_ms}ms, expected <100ms"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_plate_matching_speed_medium_dataset(
        self, plate_service, perf_test_user_id, mock_embedding, cleanup_test_data
    ):
        """
        Test matching speed with 50 plates
        Target: <100ms
        """
        # Register 50 plates
        for i in range(50):
            embedding = [0.1 + (i * 0.01) + (j * 0.001) for j in range(512)]
            metadata = PlateMetadata(
                plate_type="bowl",
                color="white",
                shape="round"
            )
            await plate_service.register_new_plate(
                perf_test_user_id,
                embedding,
                metadata
            )

        # Benchmark matching
        query_embedding = [0.1 + (j * 0.001) for j in range(512)]

        start_time = time.time()
        matched_plate = await plate_service.match_plate(
            query_embedding,
            perf_test_user_id,
            threshold=0.85
        )
        elapsed_ms = (time.time() - start_time) * 1000

        print(f"\nPlate matching (50 plates): {elapsed_ms:.2f}ms")
        assert elapsed_ms < 100, f"Matching took {elapsed_ms}ms, expected <100ms"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_plate_matching_speed_large_dataset(
        self, plate_service, setup_test_plates, perf_test_user_id, mock_embedding
    ):
        """
        Test matching speed with 100 plates
        Target: <100ms (HNSW index should handle this)
        """
        plates = await setup_test_plates

        # Benchmark matching
        query_embedding = [0.1 + (j * 0.001) for j in range(512)]

        start_time = time.time()
        matched_plate = await plate_service.match_plate(
            query_embedding,
            perf_test_user_id,
            threshold=0.85
        )
        elapsed_ms = (time.time() - start_time) * 1000

        print(f"\nPlate matching (100 plates): {elapsed_ms:.2f}ms")
        assert elapsed_ms < 100, f"Matching took {elapsed_ms}ms, expected <100ms"


class TestPlateRegistrationPerformance:
    """Test plate registration speed"""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_plate_registration_speed(
        self, plate_service, perf_test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """
        Test plate registration speed
        Target: <200ms (includes database insert)
        """
        start_time = time.time()
        plate = await plate_service.register_new_plate(
            perf_test_user_id,
            mock_embedding,
            mock_plate_metadata
        )
        elapsed_ms = (time.time() - start_time) * 1000

        print(f"\nPlate registration: {elapsed_ms:.2f}ms")
        assert elapsed_ms < 200, f"Registration took {elapsed_ms}ms, expected <200ms"
        assert plate.id is not None


class TestCalibrationPerformance:
    """Test calibration operation speed"""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_calibration_speed(
        self, plate_service, perf_test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """
        Test calibration speed
        Target: <100ms
        """
        # Register plate
        plate = await plate_service.register_new_plate(
            perf_test_user_id,
            mock_embedding,
            mock_plate_metadata
        )

        # Benchmark calibration
        calibration_input = CalibrationInput(
            plate_id=plate.id,
            method="reference_portion",
            reference_portion_grams=170.0,
            visual_fill_percentage=0.5,
            confidence=0.8
        )

        start_time = time.time()
        result = await plate_service.calibrate_plate(calibration_input)
        elapsed_ms = (time.time() - start_time) * 1000

        print(f"\nPlate calibration: {elapsed_ms:.2f}ms")
        assert elapsed_ms < 100, f"Calibration took {elapsed_ms}ms, expected <100ms"
        assert result.success is True


class TestPortionEstimationPerformance:
    """Test portion estimation speed"""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_portion_estimation_speed(
        self, plate_service, perf_test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """
        Test portion estimation speed
        Target: <50ms (simple calculation)
        """
        # Register and calibrate plate
        plate = await plate_service.register_new_plate(
            perf_test_user_id,
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

        # Benchmark estimation
        start_time = time.time()
        estimate = await plate_service.estimate_portion_from_plate(
            plate_id=plate.id,
            fill_percentage=0.5,
            food_density_g_per_ml=1.0
        )
        elapsed_ms = (time.time() - start_time) * 1000

        print(f"\nPortion estimation: {elapsed_ms:.2f}ms")
        assert elapsed_ms < 50, f"Estimation took {elapsed_ms}ms, expected <50ms"
        assert estimate.estimated_grams == 170.0


class TestConcurrentOperations:
    """Test concurrent plate operations"""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_plate_matching(
        self, plate_service, perf_test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """
        Test concurrent matching operations
        Target: 10 concurrent matches in <500ms total
        """
        # Register 50 plates
        for i in range(50):
            embedding = [x + (i * 0.01) for x in mock_embedding]
            await plate_service.register_new_plate(
                perf_test_user_id,
                embedding,
                mock_plate_metadata
            )

        # Benchmark 10 concurrent matches
        async def match_plate():
            query = [x + 0.05 for x in mock_embedding]
            return await plate_service.match_plate(
                query,
                perf_test_user_id,
                threshold=0.85
            )

        start_time = time.time()
        results = await asyncio.gather(*[match_plate() for _ in range(10)])
        elapsed_ms = (time.time() - start_time) * 1000

        print(f"\n10 concurrent matches: {elapsed_ms:.2f}ms total")
        assert elapsed_ms < 500, f"Concurrent matches took {elapsed_ms}ms, expected <500ms"
        assert len(results) == 10

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_plate_registration(
        self, plate_service, perf_test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """
        Test concurrent registration operations
        Target: 5 concurrent registrations in <1000ms
        """
        async def register_plate(index):
            embedding = [x + (index * 0.1) for x in mock_embedding]
            return await plate_service.register_new_plate(
                perf_test_user_id,
                embedding,
                mock_plate_metadata
            )

        start_time = time.time()
        results = await asyncio.gather(*[register_plate(i) for i in range(5)])
        elapsed_ms = (time.time() - start_time) * 1000

        print(f"\n5 concurrent registrations: {elapsed_ms:.2f}ms total")
        assert elapsed_ms < 1000, f"Concurrent registrations took {elapsed_ms}ms, expected <1000ms"
        assert len(results) == 5
        assert all(p.id is not None for p in results)


class TestFullPipelinePerformance:
    """Test complete workflow performance"""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_full_pipeline_detect_match_link(
        self, plate_service, perf_test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """
        Test full pipeline: detect (mocked) → match → link
        Target: <200ms for match + link (excluding actual image processing)
        """
        # Pre-register a plate
        plate = await plate_service.register_new_plate(
            perf_test_user_id,
            mock_embedding,
            mock_plate_metadata
        )

        # Benchmark match + link
        start_time = time.time()

        # Match plate
        matched = await plate_service.match_plate(
            mock_embedding,
            perf_test_user_id,
            threshold=0.85
        )

        # Link to food entry
        food_entry_id = str(uuid.uuid4())
        link = await plate_service.link_food_entry_to_plate(
            food_entry_id=food_entry_id,
            recognized_plate_id=matched.id,
            user_id=perf_test_user_id,
            confidence_score=0.9
        )

        elapsed_ms = (time.time() - start_time) * 1000

        print(f"\nFull pipeline (match + link): {elapsed_ms:.2f}ms")
        assert elapsed_ms < 200, f"Pipeline took {elapsed_ms}ms, expected <200ms"
        assert link is not None

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_full_pipeline_with_calibration_and_estimation(
        self, plate_service, perf_test_user_id, mock_embedding, mock_plate_metadata, cleanup_test_data
    ):
        """
        Test complete workflow including calibration and estimation
        Target: <300ms total
        """
        # Register plate
        plate = await plate_service.register_new_plate(
            perf_test_user_id,
            mock_embedding,
            mock_plate_metadata
        )

        start_time = time.time()

        # Calibrate
        calibration_input = CalibrationInput(
            plate_id=plate.id,
            method="reference_portion",
            reference_portion_grams=170.0,
            visual_fill_percentage=0.5,
            confidence=0.8
        )
        cal_result = await plate_service.calibrate_plate(calibration_input)

        # Estimate portion
        estimate = await plate_service.estimate_portion_from_plate(
            plate_id=plate.id,
            fill_percentage=0.75,
            food_density_g_per_ml=1.0
        )

        elapsed_ms = (time.time() - start_time) * 1000

        print(f"\nCalibration + estimation: {elapsed_ms:.2f}ms")
        assert elapsed_ms < 300, f"Workflow took {elapsed_ms}ms, expected <300ms"
        assert cal_result.success is True
        assert estimate.method == "calibrated_plate"


# ================================================================
# Summary Report
# ================================================================

@pytest.mark.asyncio
@pytest.mark.performance
async def test_performance_summary(capsys):
    """
    Print performance summary

    Target metrics:
    - Plate matching: <100ms
    - Registration: <200ms
    - Calibration: <100ms
    - Portion estimation: <50ms
    - Full pipeline: <300ms
    - Concurrent operations: 10 matches in <500ms
    """
    print("\n" + "="*60)
    print("PLATE RECOGNITION PERFORMANCE TARGETS")
    print("="*60)
    print("\nTarget Metrics:")
    print("  - Plate matching (pgvector):     <100ms")
    print("  - Plate registration:            <200ms")
    print("  - Calibration:                   <100ms")
    print("  - Portion estimation:            <50ms")
    print("  - Full pipeline (match + link):  <200ms")
    print("  - 10 concurrent matches:         <500ms")
    print("\nBased on Phase 1 benchmarks, pgvector HNSW index should")
    print("provide consistent <100ms search times even with 100+ plates.")
    print("\nRun with: pytest tests/performance/test_plate_recognition_performance.py -v -m performance")
    print("="*60 + "\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])
