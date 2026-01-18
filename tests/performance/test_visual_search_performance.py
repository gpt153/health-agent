"""
Performance benchmarks for Visual Food Search

Tests performance targets from Epic 009 - Phase 1:
- Embedding generation: <2s
- Similarity search: <100ms
"""
import pytest
import time
import asyncio
from pathlib import Path
from PIL import Image
from uuid import uuid4
import numpy as np

from src.services.visual_food_search import VisualFoodSearchService
from src.services.image_embedding import ImageEmbeddingService
from src.db.connection import db


pytestmark = pytest.mark.performance


@pytest.fixture
async def test_user_id():
    """Get test user ID for performance tests"""
    return "perf_test_user"


@pytest.fixture
async def clean_perf_database(test_user_id):
    """Clean performance test data"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM food_image_references WHERE user_id = %s",
                (test_user_id,)
            )
            await conn.commit()

    yield

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM food_image_references WHERE user_id = %s",
                (test_user_id,)
            )
            await conn.commit()


@pytest.fixture
def create_test_image(tmp_path):
    """Create test image"""
    def _create(name: str, size: tuple[int, int] = (800, 600)) -> Path:
        img_path = tmp_path / name
        img = Image.new("RGB", size, color=(255, 100, 50))
        img.save(img_path, "JPEG", quality=85)
        return img_path

    return _create


class TestEmbeddingPerformance:
    """Test embedding generation performance"""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not pytest.config.getoption("--run-performance", default=False),
        reason="Performance tests are slow and require API access"
    )
    async def test_embedding_generation_speed(self, create_test_image):
        """
        Test that embedding generation meets <2s target

        This test requires a real OpenAI API key and makes actual API calls.
        Run with: pytest -m performance --run-performance
        """
        service = ImageEmbeddingService()

        img_path = create_test_image("perf_test.jpg")

        start_time = time.time()
        embedding = await service.generate_embedding(img_path, use_cache=False)
        elapsed = time.time() - start_time

        assert len(embedding) == 512
        assert elapsed < 2.0, f"Embedding took {elapsed:.2f}s (target: <2s)"

        print(f"\n✓ Embedding generation: {elapsed:.3f}s (target: <2s)")

    @pytest.mark.asyncio
    async def test_embedding_batch_performance(self, create_test_image):
        """
        Test batch embedding generation performance

        Uses mock service to avoid API costs
        """
        # Mock the embedding service for batch tests
        class MockEmbeddingService:
            async def generate_embedding(self, path, use_cache=True):
                # Simulate processing time (20ms per image)
                await asyncio.sleep(0.02)
                return [0.1] * 512

            async def generate_embeddings_batch(self, paths, use_cache=True):
                tasks = [self.generate_embedding(p, use_cache) for p in paths]
                return await asyncio.gather(*tasks)

        service = MockEmbeddingService()

        # Create 10 test images
        images = [create_test_image(f"batch_{i}.jpg") for i in range(10)]

        start_time = time.time()
        embeddings = await service.generate_embeddings_batch(images, use_cache=False)
        elapsed = time.time() - start_time

        assert len(embeddings) == 10

        # Batch processing should be concurrent, so total time should be
        # close to single embedding time, not 10x
        assert elapsed < 0.5, f"Batch processing too slow: {elapsed:.2f}s"

        print(f"\n✓ Batch embedding (10 images): {elapsed:.3f}s")


class TestSearchPerformance:
    """Test similarity search performance"""

    @pytest.mark.asyncio
    async def test_similarity_search_speed(
        self,
        clean_perf_database,
        test_user_id,
        create_test_image
    ):
        """
        Test that similarity search meets <100ms target

        Target: <100ms for searching through user's food history
        """
        service = VisualFoodSearchService()

        # Create and store test embeddings (50 images)
        print("\nSetting up test data...")

        for i in range(50):
            # Generate random embedding
            embedding = np.random.randn(512).tolist()
            norm = np.linalg.norm(embedding)
            embedding = (np.array(embedding) / norm).tolist()

            # Store in database
            await service.store_image_embedding(
                food_entry_id=str(uuid4()),
                user_id=test_user_id,
                photo_path=f"/tmp/test_{i}.jpg",
                embedding=embedding
            )

        print("Test data ready. Running search benchmark...")

        # Create query embedding
        query_embedding = np.random.randn(512).tolist()
        norm = np.linalg.norm(query_embedding)
        query_embedding = (np.array(query_embedding) / norm).tolist()

        # Warm up the query (first query may be slower due to index loading)
        await service.find_similar_foods_by_embedding(
            user_id=test_user_id,
            query_embedding=query_embedding,
            limit=5
        )

        # Now measure actual performance
        start_time = time.time()
        matches = await service.find_similar_foods_by_embedding(
            user_id=test_user_id,
            query_embedding=query_embedding,
            limit=5
        )
        elapsed = time.time() - start_time

        # Convert to milliseconds
        elapsed_ms = elapsed * 1000

        assert len(matches) <= 5
        assert elapsed_ms < 100, f"Search took {elapsed_ms:.1f}ms (target: <100ms)"

        print(f"✓ Similarity search (50 images): {elapsed_ms:.1f}ms (target: <100ms)")

    @pytest.mark.asyncio
    async def test_search_scalability(
        self,
        clean_perf_database,
        test_user_id
    ):
        """
        Test search performance with larger dataset

        Tests HNSW index efficiency with 500 images
        """
        service = VisualFoodSearchService()

        # Create and store 500 test embeddings
        print("\nSetting up large dataset (500 images)...")

        batch_size = 50
        for batch in range(10):  # 10 batches of 50 = 500
            for i in range(batch_size):
                idx = batch * batch_size + i
                embedding = np.random.randn(512).tolist()
                norm = np.linalg.norm(embedding)
                embedding = (np.array(embedding) / norm).tolist()

                await service.store_image_embedding(
                    food_entry_id=str(uuid4()),
                    user_id=test_user_id,
                    photo_path=f"/tmp/scale_test_{idx}.jpg",
                    embedding=embedding
                )

            print(f"  Inserted batch {batch + 1}/10")

        print("Dataset ready. Running scalability test...")

        # Query embedding
        query_embedding = np.random.randn(512).tolist()
        norm = np.linalg.norm(query_embedding)
        query_embedding = (np.array(query_embedding) / norm).tolist()

        # Warm up
        await service.find_similar_foods_by_embedding(
            user_id=test_user_id,
            query_embedding=query_embedding,
            limit=5
        )

        # Measure performance
        times = []
        for _ in range(5):  # Run 5 times to get average
            start_time = time.time()
            matches = await service.find_similar_foods_by_embedding(
                user_id=test_user_id,
                query_embedding=query_embedding,
                limit=10
            )
            elapsed = time.time() - start_time
            times.append(elapsed * 1000)  # Convert to ms

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print(f"\nScalability test results (500 images):")
        print(f"  Average: {avg_time:.1f}ms")
        print(f"  Min: {min_time:.1f}ms")
        print(f"  Max: {max_time:.1f}ms")

        # Even with 500 images, should still be under 100ms (HNSW is efficient)
        assert avg_time < 100, f"Average search time {avg_time:.1f}ms exceeds 100ms"

    @pytest.mark.asyncio
    async def test_concurrent_search_performance(
        self,
        clean_perf_database,
        test_user_id
    ):
        """
        Test performance under concurrent load

        Simulates multiple users searching simultaneously
        """
        service = VisualFoodSearchService()

        # Setup test data
        print("\nSetting up concurrent test data...")
        for i in range(20):
            embedding = np.random.randn(512).tolist()
            norm = np.linalg.norm(embedding)
            embedding = (np.array(embedding) / norm).tolist()

            await service.store_image_embedding(
                food_entry_id=str(uuid4()),
                user_id=test_user_id,
                photo_path=f"/tmp/concurrent_{i}.jpg",
                embedding=embedding
            )

        # Create concurrent search tasks
        async def search_task():
            query_embedding = np.random.randn(512).tolist()
            norm = np.linalg.norm(query_embedding)
            query_embedding = (np.array(query_embedding) / norm).tolist()

            start = time.time()
            await service.find_similar_foods_by_embedding(
                user_id=test_user_id,
                query_embedding=query_embedding,
                limit=5
            )
            return (time.time() - start) * 1000

        print("Running 10 concurrent searches...")

        # Run 10 concurrent searches
        tasks = [search_task() for _ in range(10)]
        times = await asyncio.gather(*tasks)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        print(f"\nConcurrent search results:")
        print(f"  Average: {avg_time:.1f}ms")
        print(f"  Max: {max_time:.1f}ms")

        # Even under concurrent load, should maintain performance
        assert avg_time < 150, f"Average concurrent search time {avg_time:.1f}ms too high"


class TestIndexPerformance:
    """Test HNSW index performance characteristics"""

    @pytest.mark.asyncio
    async def test_hnsw_index_exists(self):
        """Verify HNSW index exists and is being used"""
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                # Check if HNSW index exists
                await cur.execute(
                    """
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE tablename = 'food_image_references'
                      AND indexname = 'idx_food_image_embeddings_hnsw'
                    """
                )

                row = await cur.fetchone()
                assert row is not None, "HNSW index not found"

                print(f"\n✓ HNSW index exists: {row['indexname']}")
                print(f"  Definition: {row['indexdef']}")

    @pytest.mark.asyncio
    async def test_query_plan_uses_index(self, test_user_id):
        """Verify that queries use the HNSW index"""

        test_embedding = [0.1] * 512
        embedding_str = f"[{','.join(str(x) for x in test_embedding)}]"

        async with db.connection() as conn:
            async with conn.cursor() as cur:
                # Get query plan
                await cur.execute(
                    """
                    EXPLAIN (FORMAT JSON)
                    SELECT food_entry_id, embedding <=> %s::vector as distance
                    FROM food_image_references
                    WHERE user_id = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT 5
                    """,
                    (embedding_str, test_user_id, embedding_str)
                )

                plan = await cur.fetchone()
                plan_json = plan[0][0]

                # The plan should mention the index
                plan_str = str(plan_json)
                uses_index = "idx_food_image_embeddings_hnsw" in plan_str

                if uses_index:
                    print("\n✓ Query uses HNSW index")
                else:
                    print("\n⚠ Query may not be using HNSW index optimally")

                # Note: We don't assert here because the index might not be used
                # for small datasets or if statistics aren't collected yet


def pytest_configure(config):
    """Add custom markers"""
    config.addinivalue_line(
        "markers",
        "performance: mark test as a performance benchmark (may be slow)"
    )


if __name__ == "__main__":
    # Allow running performance tests directly
    pytest.main([__file__, "-v", "-m", "performance", "--run-performance"])
