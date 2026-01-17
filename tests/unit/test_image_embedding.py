"""
Unit tests for Image Embedding Service

Tests the CLIP embedding generation without making actual API calls.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from PIL import Image
import io

from src.services.image_embedding import (
    ImageEmbeddingService,
    ImageEmbeddingError,
    get_embedding_service
)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    client = AsyncMock()

    # Mock embeddings response
    mock_response = Mock()
    mock_data = Mock()
    mock_data.embedding = [0.1] * 512  # 512-dim embedding
    mock_response.data = [mock_data]

    client.embeddings.create = AsyncMock(return_value=mock_response)

    return client


@pytest.fixture
def temp_test_image(tmp_path):
    """Create a temporary test image"""
    image_path = tmp_path / "test_food.jpg"

    # Create a simple test image
    img = Image.new("RGB", (800, 600), color="red")
    img.save(image_path, "JPEG")

    return image_path


@pytest.fixture
def service_with_mock_client(mock_openai_client):
    """Create service with mocked OpenAI client"""
    with patch("src.services.image_embedding.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"

        service = ImageEmbeddingService()
        service.client = mock_openai_client

        return service


class TestImageEmbeddingService:
    """Test suite for ImageEmbeddingService"""

    def test_initialization_without_api_key(self):
        """Test that service raises error without API key"""
        with patch("src.services.image_embedding.settings") as mock_settings:
            mock_settings.openai_api_key = ""

            with pytest.raises(ImageEmbeddingError, match="OpenAI API key is required"):
                ImageEmbeddingService()

    @pytest.mark.asyncio
    async def test_generate_embedding_success(
        self,
        service_with_mock_client,
        temp_test_image
    ):
        """Test successful embedding generation"""
        service = service_with_mock_client

        # Mock database operations
        with patch.object(service, "_get_cached_embedding", return_value=None), \
             patch.object(service, "_cache_embedding"):

            embedding = await service.generate_embedding(temp_test_image)

            assert len(embedding) == 512
            assert all(isinstance(x, float) for x in embedding)
            assert embedding == [0.1] * 512

    @pytest.mark.asyncio
    async def test_generate_embedding_uses_cache(
        self,
        service_with_mock_client,
        temp_test_image
    ):
        """Test that cached embeddings are used when available"""
        service = service_with_mock_client

        cached_embedding = [0.5] * 512

        with patch.object(
            service,
            "_get_cached_embedding",
            return_value=cached_embedding
        ):
            embedding = await service.generate_embedding(temp_test_image)

            assert embedding == cached_embedding
            # OpenAI client should not be called
            service.client.embeddings.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_embedding_file_not_found(self, service_with_mock_client):
        """Test error handling for missing image file"""
        service = service_with_mock_client

        with pytest.raises(ImageEmbeddingError, match="Image file not found"):
            await service.generate_embedding("/nonexistent/image.jpg")

    @pytest.mark.asyncio
    async def test_generate_embedding_invalid_dimension(
        self,
        service_with_mock_client,
        temp_test_image
    ):
        """Test error handling for wrong embedding dimension"""
        service = service_with_mock_client

        # Mock incorrect dimension
        mock_response = Mock()
        mock_data = Mock()
        mock_data.embedding = [0.1] * 256  # Wrong dimension
        mock_response.data = [mock_data]
        service.client.embeddings.create = AsyncMock(return_value=mock_response)

        with patch.object(service, "_get_cached_embedding", return_value=None):
            with pytest.raises(ImageEmbeddingError, match="Expected 512-dimensional"):
                await service.generate_embedding(temp_test_image)

    @pytest.mark.asyncio
    async def test_generate_embedding_with_retry(
        self,
        service_with_mock_client,
        temp_test_image
    ):
        """Test retry logic for transient failures"""
        service = service_with_mock_client

        # First two calls fail, third succeeds
        mock_response = Mock()
        mock_data = Mock()
        mock_data.embedding = [0.1] * 512
        mock_response.data = [mock_data]

        service.client.embeddings.create = AsyncMock(
            side_effect=[
                Exception("Network error"),
                Exception("Timeout"),
                mock_response
            ]
        )

        with patch.object(service, "_get_cached_embedding", return_value=None), \
             patch.object(service, "_cache_embedding"), \
             patch("asyncio.sleep"):  # Mock sleep to speed up test

            embedding = await service.generate_embedding(temp_test_image)

            assert len(embedding) == 512
            assert service.client.embeddings.create.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_embedding_all_retries_fail(
        self,
        service_with_mock_client,
        temp_test_image
    ):
        """Test failure when all retries are exhausted"""
        service = service_with_mock_client

        service.client.embeddings.create = AsyncMock(
            side_effect=Exception("Persistent error")
        )

        with patch.object(service, "_get_cached_embedding", return_value=None), \
             patch("asyncio.sleep"):

            with pytest.raises(ImageEmbeddingError, match="Failed to generate embedding"):
                await service.generate_embedding(temp_test_image)

            # Should retry 3 times
            assert service.client.embeddings.create.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_embeddings_batch(
        self,
        service_with_mock_client,
        tmp_path
    ):
        """Test batch embedding generation"""
        service = service_with_mock_client

        # Create multiple test images
        images = []
        for i in range(3):
            img_path = tmp_path / f"test_{i}.jpg"
            img = Image.new("RGB", (100, 100), color="blue")
            img.save(img_path, "JPEG")
            images.append(img_path)

        with patch.object(service, "_get_cached_embedding", return_value=None), \
             patch.object(service, "_cache_embedding"):

            embeddings = await service.generate_embeddings_batch(images)

            assert len(embeddings) == 3
            assert all(len(emb) == 512 for emb in embeddings)

    @pytest.mark.asyncio
    async def test_preprocess_image_rgb_conversion(self, service_with_mock_client, tmp_path):
        """Test image preprocessing converts non-RGB images"""
        service = service_with_mock_client

        # Create grayscale image
        img_path = tmp_path / "gray.jpg"
        img = Image.new("L", (100, 100), color=128)
        img.save(img_path, "JPEG")

        # This should convert to RGB automatically
        image_data = await service._preprocess_image(img_path)

        assert isinstance(image_data, str)
        assert len(image_data) > 0  # Base64 encoded data

    @pytest.mark.asyncio
    async def test_preprocess_image_resize_large(
        self,
        service_with_mock_client,
        tmp_path
    ):
        """Test that large images are resized"""
        service = service_with_mock_client

        # Create oversized image
        img_path = tmp_path / "large.jpg"
        img = Image.new("RGB", (3000, 3000), color="green")
        img.save(img_path, "JPEG")

        image_data = await service._preprocess_image(img_path)

        # Image should be resized and base64 encoded
        assert isinstance(image_data, str)
        assert len(image_data) > 0

    @pytest.mark.asyncio
    async def test_cache_operations(self, service_with_mock_client):
        """Test cache storage and retrieval"""
        service = service_with_mock_client

        test_embedding = [0.2] * 512
        test_path = "/test/image.jpg"

        # Mock database operations
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.execute = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_cursor),
            __aexit__=AsyncMock()
        ))

        with patch("src.services.image_embedding.db.connection", return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock()
        )):
            # Test caching
            await service._cache_embedding(test_path, test_embedding)

            # Verify INSERT was called
            assert mock_cursor.execute.called

    def test_get_embedding_service_singleton(self):
        """Test that get_embedding_service returns singleton"""
        with patch("src.services.image_embedding.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"

            service1 = get_embedding_service()
            service2 = get_embedding_service()

            assert service1 is service2  # Same instance


class TestImageValidation:
    """Test image validation and error handling"""

    @pytest.mark.asyncio
    async def test_invalid_image_file(self, service_with_mock_client, tmp_path):
        """Test handling of corrupted image files"""
        service = service_with_mock_client

        # Create invalid image file
        invalid_path = tmp_path / "corrupt.jpg"
        invalid_path.write_bytes(b"not an image")

        with pytest.raises(ImageEmbeddingError, match="Image preprocessing failed"):
            await service._preprocess_image(invalid_path)

    @pytest.mark.asyncio
    async def test_empty_image_file(self, service_with_mock_client, tmp_path):
        """Test handling of empty image files"""
        service = service_with_mock_client

        empty_path = tmp_path / "empty.jpg"
        empty_path.write_bytes(b"")

        with pytest.raises(ImageEmbeddingError):
            await service._preprocess_image(empty_path)


class TestPerformance:
    """Performance-related tests"""

    @pytest.mark.asyncio
    async def test_concurrent_embedding_generation(
        self,
        service_with_mock_client,
        tmp_path
    ):
        """Test that concurrent embedding generation works correctly"""
        service = service_with_mock_client

        # Create test images
        images = []
        for i in range(5):
            img_path = tmp_path / f"concurrent_{i}.jpg"
            img = Image.new("RGB", (100, 100), color="red")
            img.save(img_path, "JPEG")
            images.append(img_path)

        with patch.object(service, "_get_cached_embedding", return_value=None), \
             patch.object(service, "_cache_embedding"):

            # Generate embeddings concurrently
            import asyncio
            tasks = [service.generate_embedding(img) for img in images]
            embeddings = await asyncio.gather(*tasks)

            assert len(embeddings) == 5
            assert all(len(emb) == 512 for emb in embeddings)
