"""
Integration Tests for Portion Comparison

End-to-end testing for Epic 009 - Phase 4: Portion Comparison
"""
import pytest
import asyncio
from pathlib import Path
from datetime import datetime

from src.services.portion_comparison import get_portion_comparison_service, PortionComparisonError
from src.models.portion import PortionComparison, PortionAccuracyStats


@pytest.mark.asyncio
@pytest.mark.integration
class TestPortionComparisonIntegration:
    """Integration tests for portion comparison workflow"""

    @pytest.fixture
    def service(self):
        """Get portion comparison service"""
        return get_portion_comparison_service()

    @pytest.fixture
    def test_user_id(self):
        """Test user ID"""
        return "test_user_portion_123"

    @pytest.mark.skip(reason="Requires database setup")
    async def test_end_to_end_portion_comparison(self, service, test_user_id):
        """
        Test complete portion comparison workflow

        1. Detect food items in current and reference images
        2. Compare portions
        3. Generate comparison context
        4. Track accuracy
        """
        # Mock photo paths (would be real in production)
        current_photo = "/path/to/current_photo.jpg"
        reference_photo = "/path/to/reference_photo.jpg"

        current_entry_id = "entry_current"
        reference_entry_id = "entry_reference"

        # Step 1: Compare portions
        comparisons = await service.compare_portions(
            current_photo_path=current_photo,
            reference_photo_path=reference_photo,
            user_id=test_user_id,
            current_food_entry_id=current_entry_id,
            reference_food_entry_id=reference_entry_id,
            current_food_names=["rice", "chicken"],
            reference_food_names=["rice", "chicken"]
        )

        assert len(comparisons) > 0
        assert all(isinstance(c, PortionComparison) for c in comparisons)

        # Step 2: Generate context
        context = await service.generate_comparison_context(comparisons)
        assert context is not None
        assert len(context.portion_differences) <= len(comparisons)

        # Step 3: Track accuracy (simulate user confirmation)
        if comparisons:
            first_comparison = comparisons[0]
            accuracy = await service.track_estimate_accuracy(
                portion_comparison_id=first_comparison.id,
                user_id=test_user_id,
                estimated_grams=first_comparison.estimated_grams_difference or 50.0,
                user_confirmed_grams=55.0,  # User's confirmation
                food_item_type=first_comparison.item_name
            )

            assert accuracy.variance_percentage < 100  # Should be reasonable

    @pytest.mark.skip(reason="Requires database and Phase 1 setup")
    async def test_find_reference_image(self, service, test_user_id):
        """Test finding reference image using Phase 1 visual similarity"""
        current_photo = "/path/to/test_photo.jpg"

        reference = await service.find_reference_image(
            current_photo_path=current_photo,
            user_id=test_user_id
        )

        # May or may not find a reference (depends on user's history)
        if reference:
            ref_photo, ref_entry_id, ref_date = reference
            assert isinstance(ref_photo, str)
            assert isinstance(ref_entry_id, str)
            assert isinstance(ref_date, datetime)

    @pytest.mark.skip(reason="Requires database setup")
    async def test_get_user_accuracy_stats(self, service, test_user_id):
        """Test retrieving user accuracy statistics"""
        stats = await service.get_user_accuracy_stats(test_user_id)

        assert isinstance(stats, PortionAccuracyStats)
        assert stats.total_estimates >= 0
        assert 0.0 <= stats.accuracy_rate <= 100.0

    @pytest.mark.skip(reason="Requires database setup")
    async def test_comparison_with_calibrated_plate(self, service, test_user_id):
        """Test portion comparison using calibrated plate data"""
        # This test would require:
        # 1. A recognized plate from Phase 2
        # 2. Calibration data for that plate
        # 3. Food entries to compare

        # Mock for demonstration
        plate_id = "test_plate_id"

        comparisons = await service.compare_portions(
            current_photo_path="/path/current.jpg",
            reference_photo_path="/path/reference.jpg",
            user_id=test_user_id,
            current_food_entry_id="current",
            reference_food_entry_id="reference",
            current_food_names=["rice"],
            reference_food_names=["rice"],
            plate_id=plate_id
        )

        # With calibrated plate, confidence should be higher
        if comparisons:
            assert comparisons[0].confidence > 0.5

    @pytest.mark.skip(reason="Performance test - run manually")
    async def test_portion_comparison_performance(self, service):
        """Test performance of portion comparison operations"""
        import time

        # Test detection speed
        start = time.time()
        detections = await service.detect_food_items(
            photo_path="/path/test.jpg",
            user_id="test_user",
            food_entry_id="test_entry",
            food_names=["rice", "chicken", "vegetables"]
        )
        detection_time = time.time() - start

        assert detection_time < 0.5  # Should be fast (< 500ms)

        # Test comparison calculation speed
        if len(detections) >= 2:
            start = time.time()
            # Mock comparison calculation
            estimated_diff, confidence = await service.calculate_portion_estimate(
                area_difference_ratio=0.3,
                reference_grams=100.0,
                food_density=1.0
            )
            calc_time = time.time() - start

            assert calc_time < 0.1  # Should be very fast (< 100ms)


@pytest.mark.integration
class TestPortionComparisonWithVisionAI:
    """Integration tests with Vision AI"""

    @pytest.mark.skip(reason="Requires Vision AI setup")
    async def test_vision_ai_with_comparison_context(self):
        """Test Vision AI receives and uses comparison context"""
        from src.utils.vision import analyze_food_photo
        from src.services.portion_comparison import get_portion_comparison_service

        service = get_portion_comparison_service()
        photo_path = "/path/to/test_photo.jpg"
        user_id = "test_user"

        # Find reference
        reference = await service.find_reference_image(photo_path, user_id)

        portion_context = None
        if reference:
            # Generate comparison context
            ref_photo, ref_entry_id, ref_date = reference

            # Would need actual comparisons here
            # For now, create mock context
            from src.models.portion import ComparisonContext
            portion_context = ComparisonContext(
                portion_differences=["More rice (+30g)"],
                confidence_notes="Medium confidence",
                summary="Similar to yesterday's meal"
            ).to_prompt_text()

        # Analyze with comparison context
        result = await analyze_food_photo(
            photo_path=photo_path,
            user_id=user_id,
            portion_comparison_context=portion_context
        )

        assert result is not None
        assert len(result.foods) > 0


@pytest.mark.integration
class TestPortionComparisonDatabase:
    """Integration tests for database operations"""

    @pytest.mark.skip(reason="Requires database migration 024")
    async def test_database_migration_applied(self):
        """Test that migration 024 has been applied"""
        from src.db.connection import db

        async with db.connection() as conn:
            async with conn.cursor() as cur:
                # Check tables exist
                await cur.execute("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_name IN (
                        'food_item_detections',
                        'portion_comparisons',
                        'portion_estimate_accuracy'
                    )
                """)
                tables = await cur.fetchall()
                assert len(tables) == 3

                # Check functions exist
                await cur.execute("""
                    SELECT routine_name FROM information_schema.routines
                    WHERE routine_name IN (
                        'get_user_portion_accuracy',
                        'get_food_item_portion_history'
                    )
                """)
                functions = await cur.fetchall()
                assert len(functions) == 2

    @pytest.mark.skip(reason="Requires database setup")
    async def test_store_and_retrieve_portion_comparison(self):
        """Test storing and retrieving portion comparison from database"""
        from src.db.connection import db

        async with db.connection() as conn:
            async with conn.cursor() as cur:
                # Insert test comparison
                await cur.execute("""
                    INSERT INTO portion_comparisons
                    (user_id, current_food_entry_id, reference_food_entry_id,
                     item_name, current_area, reference_area, area_difference_ratio,
                     estimated_grams_difference, confidence)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    "test_user",
                    "current_entry",
                    "ref_entry",
                    "rice",
                    0.3,
                    0.2,
                    0.5,
                    50.0,
                    0.8
                ))

                row = await cur.fetchone()
                comparison_id = row["id"]

                # Retrieve
                await cur.execute("""
                    SELECT * FROM portion_comparisons WHERE id = %s
                """, (comparison_id,))

                result = await cur.fetchone()
                assert result["item_name"] == "rice"
                assert result["area_difference_ratio"] == 0.5
                assert result["confidence"] == 0.8

                # Cleanup
                await cur.execute(
                    "DELETE FROM portion_comparisons WHERE id = %s",
                    (comparison_id,)
                )
                await conn.commit()
