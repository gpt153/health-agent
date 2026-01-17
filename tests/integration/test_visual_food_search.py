"""
Integration tests for Visual Food Search

Tests the complete visual search workflow with database integration.
Requires a running PostgreSQL database with pgvector extension.
"""
import pytest
from pathlib import Path
from PIL import Image
import numpy as np
from uuid import uuid4
from datetime import datetime

from src.services.visual_food_search import (
    VisualFoodSearchService,
    VisualSearchError,
    SimilarFoodMatch,
    get_visual_search_service
)
from src.services.image_embedding import ImageEmbeddingService
from src.db.connection import db


@pytest.fixture
async def test_user_id():
    """Get test user ID"""
    return "test_user_visual_search"


@pytest.fixture
async def clean_database(test_user_id):
    """Clean test data before and after tests"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Clean before
            await cur.execute(
                "DELETE FROM food_image_references WHERE user_id = %s",
                (test_user_id,)
            )
            await cur.execute(
                "DELETE FROM image_analysis_cache WHERE photo_path LIKE '/tmp/test_%'"
            )
            await conn.commit()

    yield

    # Clean after
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM food_image_references WHERE user_id = %s",
                (test_user_id,)
            )
            await cur.execute(
                "DELETE FROM image_analysis_cache WHERE photo_path LIKE '/tmp/test_%'"
            )
            await conn.commit()


@pytest.fixture
def create_test_image(tmp_path):
    """Factory function to create test images with different characteristics"""
    def _create(name: str, color: tuple[int, int, int] = (255, 0, 0)) -> Path:
        img_path = tmp_path / name
        img = Image.new("RGB", (800, 600), color=color)
        img.save(img_path, "JPEG")
        return img_path

    return _create


@pytest.fixture
def mock_embedding_service(monkeypatch):
    """Mock the embedding service to avoid API calls"""

    class MockEmbeddingService:
        """Mock embedding service that generates deterministic embeddings"""

        def __init__(self):
            self.call_count = 0

        async def generate_embedding(self, image_path: str | Path, use_cache: bool = True) -> list[float]:
            """Generate a mock embedding based on image path"""
            self.call_count += 1

            # Generate deterministic but different embeddings for different images
            seed = hash(str(image_path)) % 10000
            np.random.seed(seed)

            # Create a 512-dim embedding
            embedding = np.random.randn(512).tolist()

            # Normalize to unit vector
            norm = np.linalg.norm(embedding)
            embedding = (np.array(embedding) / norm).tolist()

            return embedding

    mock_service = MockEmbeddingService()

    def mock_get_embedding_service():
        return mock_service

    monkeypatch.setattr(
        "src.services.visual_food_search.get_embedding_service",
        mock_get_embedding_service
    )

    return mock_service


class TestVisualFoodSearchService:
    """Test suite for VisualFoodSearchService"""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_embedding(
        self,
        clean_database,
        test_user_id,
        create_test_image,
        mock_embedding_service
    ):
        """Test storing and retrieving image embeddings"""
        service = VisualFoodSearchService()

        # Create test image
        img_path = create_test_image("pizza.jpg", color=(255, 100, 50))
        food_entry_id = str(uuid4())

        # Store embedding
        await service.store_image_embedding(
            food_entry_id=food_entry_id,
            user_id=test_user_id,
            photo_path=str(img_path)
        )

        # Verify stored in database
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT food_entry_id, user_id, embedding
                    FROM food_image_references
                    WHERE food_entry_id = %s
                    """,
                    (food_entry_id,)
                )

                row = await cur.fetchone()
                assert row is not None
                assert row["food_entry_id"] == uuid4(food_entry_id)
                assert row["user_id"] == test_user_id
                assert row["embedding"] is not None

    @pytest.mark.asyncio
    async def test_find_similar_foods(
        self,
        clean_database,
        test_user_id,
        create_test_image,
        mock_embedding_service
    ):
        """Test finding similar food images"""
        service = VisualFoodSearchService()

        # Store multiple food images with similar characteristics
        similar_images = [
            ("pizza1.jpg", (255, 100, 50)),  # Similar colors (red/orange)
            ("pizza2.jpg", (250, 110, 45)),
            ("burger.jpg", (100, 50, 20)),  # Different (darker brown)
        ]

        stored_entries = []
        for filename, color in similar_images:
            img_path = create_test_image(filename, color=color)
            entry_id = str(uuid4())

            await service.store_image_embedding(
                food_entry_id=entry_id,
                user_id=test_user_id,
                photo_path=str(img_path)
            )

            stored_entries.append({
                "entry_id": entry_id,
                "path": str(img_path),
                "color": color
            })

        # Query with a similar image (similar to pizza)
        query_img = create_test_image("query_pizza.jpg", color=(255, 105, 48))

        matches = await service.find_similar_foods(
            user_id=test_user_id,
            query_image_path=query_img,
            limit=5
        )

        # Should find at least the similar pizzas
        assert len(matches) > 0
        assert all(isinstance(m, SimilarFoodMatch) for m in matches)

        # Matches should be sorted by similarity (highest first)
        scores = [m.similarity_score for m in matches]
        assert scores == sorted(scores, reverse=True)

        # All matches should have confidence levels
        assert all(m.confidence_level in ["high", "medium", "low"] for m in matches)

    @pytest.mark.asyncio
    async def test_find_similar_with_threshold(
        self,
        clean_database,
        test_user_id,
        create_test_image,
        mock_embedding_service
    ):
        """Test similarity threshold filtering"""
        service = VisualFoodSearchService()

        # Store test images
        img1 = create_test_image("test1.jpg")
        entry_id = str(uuid4())
        await service.store_image_embedding(
            food_entry_id=entry_id,
            user_id=test_user_id,
            photo_path=str(img1)
        )

        # Query with high similarity threshold
        query_img = create_test_image("query.jpg")

        matches_strict = await service.find_similar_foods(
            user_id=test_user_id,
            query_image_path=query_img,
            min_similarity=0.95  # Very high threshold
        )

        matches_lenient = await service.find_similar_foods(
            user_id=test_user_id,
            query_image_path=query_img,
            min_similarity=0.50  # Lower threshold
        )

        # Lenient threshold should return more results
        assert len(matches_lenient) >= len(matches_strict)

    @pytest.mark.asyncio
    async def test_user_isolation(
        self,
        clean_database,
        test_user_id,
        create_test_image,
        mock_embedding_service
    ):
        """Test that users only see their own food images"""
        service = VisualFoodSearchService()

        other_user_id = "other_user_123"

        # Store image for test user
        img1 = create_test_image("user1_food.jpg")
        entry1 = str(uuid4())
        await service.store_image_embedding(
            food_entry_id=entry1,
            user_id=test_user_id,
            photo_path=str(img1)
        )

        # Store image for other user
        img2 = create_test_image("user2_food.jpg")
        entry2 = str(uuid4())
        await service.store_image_embedding(
            food_entry_id=entry2,
            user_id=other_user_id,
            photo_path=str(img2)
        )

        # Query as test user
        query_img = create_test_image("query.jpg")
        matches = await service.find_similar_foods(
            user_id=test_user_id,
            query_image_path=query_img
        )

        # Should only find user's own images
        assert all(m.food_entry_id == entry1 for m in matches)

        # Clean up other user's data
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM food_image_references WHERE user_id = %s",
                    (other_user_id,)
                )
                await conn.commit()

    @pytest.mark.asyncio
    async def test_find_similar_by_embedding(
        self,
        clean_database,
        test_user_id,
        mock_embedding_service
    ):
        """Test finding similar foods using a pre-computed embedding"""
        service = VisualFoodSearchService()

        # Generate a test embedding
        test_embedding = np.random.randn(512).tolist()
        norm = np.linalg.norm(test_embedding)
        test_embedding = (np.array(test_embedding) / norm).tolist()

        # Try to find matches (should work even with no stored images)
        matches = await service.find_similar_foods_by_embedding(
            user_id=test_user_id,
            query_embedding=test_embedding,
            limit=5
        )

        # Should return empty list or matches if any exist
        assert isinstance(matches, list)

    @pytest.mark.asyncio
    async def test_get_user_image_count(
        self,
        clean_database,
        test_user_id,
        create_test_image,
        mock_embedding_service
    ):
        """Test getting count of indexed images for user"""
        service = VisualFoodSearchService()

        # Initially should be 0
        count = await service.get_user_image_count(test_user_id)
        assert count == 0

        # Store some images
        for i in range(3):
            img = create_test_image(f"food_{i}.jpg")
            await service.store_image_embedding(
                food_entry_id=str(uuid4()),
                user_id=test_user_id,
                photo_path=str(img)
            )

        # Count should be 3
        count = await service.get_user_image_count(test_user_id)
        assert count == 3

    @pytest.mark.asyncio
    async def test_confidence_levels(
        self,
        clean_database,
        test_user_id,
        create_test_image,
        mock_embedding_service
    ):
        """Test confidence level assignment"""
        service = VisualFoodSearchService()

        # Create a match object manually to test confidence assignment
        match = SimilarFoodMatch(
            food_entry_id="test",
            photo_path="/test/path.jpg",
            similarity_score=0.90,  # High similarity
            created_at=datetime.now(),
            confidence_level=""
        )

        match_with_confidence = service._add_confidence_level(match)
        assert match_with_confidence.confidence_level == "high"

        # Test medium confidence
        match.similarity_score = 0.75
        match_with_confidence = service._add_confidence_level(match)
        assert match_with_confidence.confidence_level == "medium"

        # Test low confidence
        match.similarity_score = 0.60
        match_with_confidence = service._add_confidence_level(match)
        assert match_with_confidence.confidence_level == "low"

    @pytest.mark.asyncio
    async def test_invalid_parameters(self, test_user_id):
        """Test error handling for invalid parameters"""
        service = VisualFoodSearchService()

        # Invalid limit
        with pytest.raises(VisualSearchError, match="Limit must be"):
            await service.find_similar_foods_by_embedding(
                user_id=test_user_id,
                query_embedding=[0.1] * 512,
                limit=0
            )

        # Invalid embedding dimension
        with pytest.raises(VisualSearchError, match="Expected 512-dimensional"):
            await service.find_similar_foods_by_embedding(
                user_id=test_user_id,
                query_embedding=[0.1] * 256,  # Wrong dimension
                limit=5
            )

        # Invalid similarity threshold
        with pytest.raises(VisualSearchError, match="must be between 0.0 and 1.0"):
            from pathlib import Path
            await service.find_similar_foods(
                user_id=test_user_id,
                query_image_path=Path("/tmp/test.jpg"),
                min_similarity=1.5  # > 1.0
            )

    @pytest.mark.asyncio
    async def test_similar_food_match_serialization(self):
        """Test SimilarFoodMatch to_dict method"""
        match = SimilarFoodMatch(
            food_entry_id="123e4567-e89b-12d3-a456-426614174000",
            photo_path="/data/users/123/photo.jpg",
            similarity_score=0.8765,
            created_at=datetime(2024, 1, 15, 10, 30, 0),
            confidence_level="high"
        )

        result = match.to_dict()

        assert result["food_entry_id"] == "123e4567-e89b-12d3-a456-426614174000"
        assert result["photo_path"] == "/data/users/123/photo.jpg"
        assert result["similarity_score"] == 0.877  # Rounded to 3 decimals
        assert result["created_at"] == "2024-01-15T10:30:00"
        assert result["confidence_level"] == "high"

    def test_get_visual_search_service_singleton(self):
        """Test that get_visual_search_service returns singleton"""
        service1 = get_visual_search_service()
        service2 = get_visual_search_service()

        assert service1 is service2


class TestDatabaseFunctions:
    """Test PostgreSQL database functions"""

    @pytest.mark.asyncio
    async def test_find_similar_food_images_function(
        self,
        clean_database,
        test_user_id
    ):
        """Test the find_similar_food_images PostgreSQL function"""

        # Create a test embedding
        test_embedding = np.random.randn(512).tolist()
        norm = np.linalg.norm(test_embedding)
        test_embedding = (np.array(test_embedding) / norm).tolist()
        embedding_str = f"[{','.join(str(x) for x in test_embedding)}]"

        async with db.connection() as conn:
            async with conn.cursor() as cur:
                # Call the database function directly
                await cur.execute(
                    """
                    SELECT * FROM find_similar_food_images(
                        %s::TEXT,
                        %s::vector,
                        %s::INTEGER,
                        %s::FLOAT
                    )
                    """,
                    (test_user_id, embedding_str, 5, 0.3)
                )

                results = await cur.fetchall()

                # Should return results (empty list if no matches)
                assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_cache_hit_function(self, clean_database):
        """Test the update_cache_hit PostgreSQL function"""

        test_path = "/tmp/test_cache_hit.jpg"

        async with db.connection() as conn:
            async with conn.cursor() as cur:
                # Insert test cache entry
                test_embedding = [0.1] * 512
                embedding_str = f"[{','.join(str(x) for x in test_embedding)}]"

                await cur.execute(
                    """
                    INSERT INTO image_analysis_cache (photo_path, embedding)
                    VALUES (%s, %s::vector)
                    """,
                    (test_path, embedding_str)
                )

                # Call update_cache_hit
                await cur.execute(
                    "SELECT update_cache_hit(%s)",
                    (test_path,)
                )

                # Check that cache_hits incremented
                await cur.execute(
                    "SELECT cache_hits FROM image_analysis_cache WHERE photo_path = %s",
                    (test_path,)
                )

                row = await cur.fetchone()
                assert row["cache_hits"] == 1

                await conn.commit()
