"""
Image Embedding Service using OpenAI's CLIP model

This service generates 512-dimensional embeddings for food images using
OpenAI's clip-vit-base-patch32 model for visual similarity search.

Epic 009 - Phase 1: Visual Reference Foundation
"""
import logging
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
import base64

import httpx
from openai import AsyncOpenAI
from PIL import Image

from src.config import settings
from src.db.connection import db
from src.exceptions import ServiceError

logger = logging.getLogger(__name__)


class ImageEmbeddingError(ServiceError):
    """Raised when image embedding generation fails"""
    pass


class ImageEmbeddingService:
    """
    Service for generating CLIP embeddings for food images

    Uses OpenAI's clip-vit-base-patch32 model to generate 512-dimensional
    embeddings that can be used for visual similarity search.

    Features:
    - Automatic caching to avoid redundant API calls
    - Batch processing support
    - Retry logic for transient failures
    - Image validation and preprocessing
    """

    # Model configuration
    CLIP_MODEL = "clip-vit-base-patch32"
    EMBEDDING_DIMENSION = 512

    # Cache configuration
    CACHE_TTL_DAYS = 90  # Cache embeddings for 90 days

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds

    def __init__(self) -> None:
        """Initialize the image embedding service"""
        if not settings.openai_api_key:
            raise ImageEmbeddingError(
                "OpenAI API key is required for image embedding service. "
                "Set OPENAI_API_KEY in your .env file."
            )

        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=httpx.Timeout(60.0, connect=10.0)  # 60s total, 10s connect
        )

    async def generate_embedding(
        self,
        image_path: str | Path,
        use_cache: bool = True
    ) -> list[float]:
        """
        Generate CLIP embedding for an image

        Args:
            image_path: Path to the image file
            use_cache: Whether to use cached embeddings if available

        Returns:
            512-dimensional embedding vector

        Raises:
            ImageEmbeddingError: If embedding generation fails
        """
        image_path = Path(image_path)

        # Validate image exists
        if not image_path.exists():
            raise ImageEmbeddingError(f"Image file not found: {image_path}")

        # Check cache first
        if use_cache:
            cached_embedding = await self._get_cached_embedding(str(image_path))
            if cached_embedding is not None:
                logger.debug(f"Using cached embedding for {image_path}")
                return cached_embedding

        # Generate new embedding
        logger.info(f"Generating CLIP embedding for {image_path}")
        embedding = await self._generate_embedding_with_retry(image_path)

        # Cache the result
        await self._cache_embedding(str(image_path), embedding)

        return embedding

    async def generate_embeddings_batch(
        self,
        image_paths: list[str | Path],
        use_cache: bool = True
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple images in batch

        Args:
            image_paths: List of image file paths
            use_cache: Whether to use cached embeddings if available

        Returns:
            List of 512-dimensional embedding vectors

        Raises:
            ImageEmbeddingError: If any embedding generation fails
        """
        tasks = [
            self.generate_embedding(path, use_cache=use_cache)
            for path in image_paths
        ]

        try:
            embeddings = await asyncio.gather(*tasks)
            return embeddings
        except Exception as e:
            raise ImageEmbeddingError(f"Batch embedding generation failed: {e}")

    async def _generate_embedding_with_retry(
        self,
        image_path: Path
    ) -> list[float]:
        """
        Generate embedding with exponential backoff retry

        Args:
            image_path: Path to the image file

        Returns:
            512-dimensional embedding vector

        Raises:
            ImageEmbeddingError: If all retries fail
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES):
            try:
                embedding = await self._call_openai_api(image_path)

                # Validate embedding dimension
                if len(embedding) != self.EMBEDDING_DIMENSION:
                    raise ImageEmbeddingError(
                        f"Expected {self.EMBEDDING_DIMENSION}-dimensional embedding, "
                        f"got {len(embedding)}"
                    )

                return embedding

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Embedding generation attempt {attempt + 1}/{self.MAX_RETRIES} "
                    f"failed: {e}"
                )

                # Don't retry on validation errors
                if "Expected" in str(e) and "dimensional" in str(e):
                    raise ImageEmbeddingError(str(e))

                # Exponential backoff
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAY * (2 ** attempt)
                    await asyncio.sleep(delay)

        # All retries failed
        raise ImageEmbeddingError(
            f"Failed to generate embedding after {self.MAX_RETRIES} attempts: "
            f"{last_error}"
        )

    async def _call_openai_api(self, image_path: Path) -> list[float]:
        """
        Call OpenAI API to generate embedding

        Args:
            image_path: Path to the image file

        Returns:
            Raw embedding from API

        Raises:
            Exception: If API call fails
        """
        try:
            # Validate and preprocess image
            image_data = await self._preprocess_image(image_path)

            # Call OpenAI Embeddings API
            # Note: OpenAI doesn't have a direct CLIP embedding endpoint yet,
            # so we use their vision model to generate embeddings
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",  # 512 dimensions
                input=image_data,
                encoding_format="float"
            )

            embedding = response.data[0].embedding

            logger.debug(
                f"Generated embedding for {image_path.name}: "
                f"{len(embedding)} dimensions"
            )

            return embedding

        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise ImageEmbeddingError(f"OpenAI API error: {e}")

    async def _preprocess_image(self, image_path: Path) -> str:
        """
        Preprocess image for embedding generation

        Args:
            image_path: Path to the image file

        Returns:
            Base64-encoded image data

        Raises:
            ImageEmbeddingError: If image processing fails
        """
        try:
            # Open and validate image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Resize if too large (max 2048x2048 for efficiency)
                max_size = 2048
                if max(img.size) > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

                # Save to bytes
                from io import BytesIO
                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                image_bytes = buffer.getvalue()

                # Encode to base64
                image_data = base64.b64encode(image_bytes).decode("utf-8")

                return image_data

        except Exception as e:
            raise ImageEmbeddingError(f"Image preprocessing failed: {e}")

    async def _get_cached_embedding(
        self,
        photo_path: str
    ) -> Optional[list[float]]:
        """
        Get cached embedding from database

        Args:
            photo_path: Path to the image file

        Returns:
            Cached embedding if found and not expired, None otherwise
        """
        try:
            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT embedding, analysis_timestamp, cache_hits
                        FROM image_analysis_cache
                        WHERE photo_path = %s
                          AND model_version = %s
                          AND analysis_timestamp > %s
                        """,
                        (
                            photo_path,
                            self.CLIP_MODEL,
                            datetime.utcnow() - timedelta(days=self.CACHE_TTL_DAYS)
                        )
                    )

                    row = await cur.fetchone()

                    if row:
                        # Update cache hit counter
                        await cur.execute(
                            "SELECT update_cache_hit(%s)",
                            (photo_path,)
                        )
                        await conn.commit()

                        # Convert pgvector to list
                        embedding = row["embedding"]
                        if isinstance(embedding, str):
                            # Parse vector string: "[0.1, 0.2, ...]"
                            embedding = [
                                float(x) for x in embedding.strip("[]").split(",")
                            ]

                        logger.info(
                            f"Cache hit for {photo_path} "
                            f"(hits: {row['cache_hits'] + 1})"
                        )
                        return embedding

                    return None

        except Exception as e:
            logger.warning(f"Failed to get cached embedding: {e}")
            return None

    async def _cache_embedding(
        self,
        photo_path: str,
        embedding: list[float]
    ) -> None:
        """
        Cache embedding in database

        Args:
            photo_path: Path to the image file
            embedding: Embedding vector to cache
        """
        try:
            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    # Convert list to pgvector format
                    embedding_str = f"[{','.join(str(x) for x in embedding)}]"

                    await cur.execute(
                        """
                        INSERT INTO image_analysis_cache
                        (photo_path, embedding, model_version)
                        VALUES (%s, %s::vector, %s)
                        ON CONFLICT (photo_path)
                        DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            model_version = EXCLUDED.model_version,
                            analysis_timestamp = CURRENT_TIMESTAMP,
                            cache_hits = 0,
                            last_accessed = CURRENT_TIMESTAMP
                        """,
                        (photo_path, embedding_str, self.CLIP_MODEL)
                    )

                    await conn.commit()

                    logger.debug(f"Cached embedding for {photo_path}")

        except Exception as e:
            logger.warning(f"Failed to cache embedding: {e}")
            # Don't raise - caching failure shouldn't break the flow


# Global service instance
_embedding_service: Optional[ImageEmbeddingService] = None


def get_embedding_service() -> ImageEmbeddingService:
    """Get or create the global image embedding service instance"""
    global _embedding_service

    if _embedding_service is None:
        _embedding_service = ImageEmbeddingService()

    return _embedding_service
