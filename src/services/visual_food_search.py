"""
Visual Food Search Service

Finds visually similar food items using CLIP embeddings and pgvector similarity search.

Epic 009 - Phase 1: Visual Reference Foundation
"""
import logging
from typing import Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

from src.db.connection import db
from src.services.image_embedding import get_embedding_service, ImageEmbeddingError
from src.exceptions import ServiceError

logger = logging.getLogger(__name__)


class VisualSearchError(ServiceError):
    """Raised when visual search fails"""
    pass


@dataclass
class SimilarFoodMatch:
    """Represents a visually similar food match"""

    food_entry_id: str
    photo_path: str
    similarity_score: float  # 0.0 to 1.0, higher is more similar
    created_at: datetime
    confidence_level: str  # "high", "medium", "low"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "food_entry_id": self.food_entry_id,
            "photo_path": self.photo_path,
            "similarity_score": round(self.similarity_score, 3),
            "created_at": self.created_at.isoformat(),
            "confidence_level": self.confidence_level
        }


class VisualFoodSearchService:
    """
    Service for finding visually similar food items

    Uses CLIP embeddings and pgvector cosine similarity to find food items
    that look similar to a query image.

    Features:
    - Configurable similarity thresholds
    - Confidence scoring (high/medium/low)
    - User-scoped search (only searches user's own food history)
    - Handles edge cases (no matches, multiple close matches)
    """

    # Similarity thresholds (cosine similarity: 0.0 to 1.0)
    HIGH_CONFIDENCE_THRESHOLD = 0.85  # Very similar
    MEDIUM_CONFIDENCE_THRESHOLD = 0.70  # Moderately similar
    DEFAULT_DISTANCE_THRESHOLD = 0.30  # Min similarity to return (0.70 similarity)

    # Query limits
    DEFAULT_LIMIT = 5
    MAX_LIMIT = 20

    def __init__(self) -> None:
        """Initialize the visual food search service"""
        self.embedding_service = get_embedding_service()

    async def find_similar_foods(
        self,
        user_id: str,
        query_image_path: str | Path,
        limit: int = DEFAULT_LIMIT,
        min_similarity: Optional[float] = None
    ) -> list[SimilarFoodMatch]:
        """
        Find visually similar food items for a user

        Args:
            user_id: Telegram user ID
            query_image_path: Path to the query image
            limit: Maximum number of results to return
            min_similarity: Minimum similarity score (0.0 to 1.0).
                          If None, uses DEFAULT_DISTANCE_THRESHOLD

        Returns:
            List of similar food matches, ordered by similarity (most similar first)

        Raises:
            VisualSearchError: If search fails
        """
        # Validate limit
        if limit < 1:
            raise VisualSearchError("Limit must be >= 1")
        if limit > self.MAX_LIMIT:
            logger.warning(f"Limit {limit} exceeds max {self.MAX_LIMIT}, capping")
            limit = self.MAX_LIMIT

        # Use default threshold if not specified
        if min_similarity is None:
            min_similarity = 1.0 - self.DEFAULT_DISTANCE_THRESHOLD

        # Validate similarity threshold
        if not 0.0 <= min_similarity <= 1.0:
            raise VisualSearchError(
                f"min_similarity must be between 0.0 and 1.0, got {min_similarity}"
            )

        try:
            # Generate embedding for query image
            logger.info(f"Finding similar foods for {query_image_path}")
            query_embedding = await self.embedding_service.generate_embedding(
                query_image_path
            )

            # Search for similar images in database
            matches = await self._search_similar_images(
                user_id=user_id,
                query_embedding=query_embedding,
                limit=limit,
                distance_threshold=1.0 - min_similarity  # Convert to distance
            )

            # Add confidence levels
            matches_with_confidence = [
                self._add_confidence_level(match) for match in matches
            ]

            logger.info(
                f"Found {len(matches_with_confidence)} similar foods for user {user_id}"
            )

            return matches_with_confidence

        except ImageEmbeddingError as e:
            raise VisualSearchError(f"Failed to generate embedding: {e}")
        except Exception as e:
            logger.error(f"Visual search failed: {e}")
            raise VisualSearchError(f"Search failed: {e}")

    async def find_similar_foods_by_embedding(
        self,
        user_id: str,
        query_embedding: list[float],
        limit: int = DEFAULT_LIMIT,
        min_similarity: Optional[float] = None
    ) -> list[SimilarFoodMatch]:
        """
        Find similar foods using a pre-computed embedding

        Useful when you already have the embedding and want to avoid
        re-generating it.

        Args:
            user_id: Telegram user ID
            query_embedding: 512-dimensional embedding vector
            limit: Maximum number of results to return
            min_similarity: Minimum similarity score (0.0 to 1.0)

        Returns:
            List of similar food matches

        Raises:
            VisualSearchError: If search fails
        """
        # Validate embedding
        if len(query_embedding) != 512:
            raise VisualSearchError(
                f"Expected 512-dimensional embedding, got {len(query_embedding)}"
            )

        # Validate limit
        if limit < 1 or limit > self.MAX_LIMIT:
            raise VisualSearchError(f"Limit must be between 1 and {self.MAX_LIMIT}")

        # Use default threshold if not specified
        if min_similarity is None:
            min_similarity = 1.0 - self.DEFAULT_DISTANCE_THRESHOLD

        try:
            matches = await self._search_similar_images(
                user_id=user_id,
                query_embedding=query_embedding,
                limit=limit,
                distance_threshold=1.0 - min_similarity
            )

            matches_with_confidence = [
                self._add_confidence_level(match) for match in matches
            ]

            return matches_with_confidence

        except Exception as e:
            raise VisualSearchError(f"Search failed: {e}")

    async def store_image_embedding(
        self,
        food_entry_id: str,
        user_id: str,
        photo_path: str,
        embedding: Optional[list[float]] = None
    ) -> None:
        """
        Store image embedding in database

        If embedding is not provided, it will be generated automatically.

        Args:
            food_entry_id: UUID of the food entry
            user_id: Telegram user ID
            photo_path: Path to the food photo
            embedding: Pre-computed embedding (optional)

        Raises:
            VisualSearchError: If storage fails
        """
        try:
            # Generate embedding if not provided
            if embedding is None:
                logger.info(f"Generating embedding for {photo_path}")
                embedding = await self.embedding_service.generate_embedding(photo_path)

            # Validate embedding
            if len(embedding) != 512:
                raise VisualSearchError(
                    f"Invalid embedding dimension: {len(embedding)}"
                )

            # Store in database
            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    # Convert list to pgvector format
                    embedding_str = f"[{','.join(str(x) for x in embedding)}]"

                    await cur.execute(
                        """
                        INSERT INTO food_image_references
                        (food_entry_id, user_id, photo_path, embedding)
                        VALUES (%s, %s, %s, %s::vector)
                        ON CONFLICT (food_entry_id)
                        DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            photo_path = EXCLUDED.photo_path
                        """,
                        (food_entry_id, user_id, photo_path, embedding_str)
                    )

                    await conn.commit()

            logger.info(f"Stored embedding for food entry {food_entry_id}")

        except ImageEmbeddingError as e:
            raise VisualSearchError(f"Failed to generate embedding: {e}")
        except Exception as e:
            logger.error(f"Failed to store embedding: {e}")
            raise VisualSearchError(f"Storage failed: {e}")

    async def _search_similar_images(
        self,
        user_id: str,
        query_embedding: list[float],
        limit: int,
        distance_threshold: float
    ) -> list[SimilarFoodMatch]:
        """
        Search for similar images using pgvector

        Args:
            user_id: Telegram user ID
            query_embedding: 512-dimensional embedding
            limit: Max results
            distance_threshold: Max cosine distance (0.0 to 1.0)

        Returns:
            List of similar food matches
        """
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                # Convert embedding to pgvector format
                embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

                # Use the database function for similarity search
                await cur.execute(
                    """
                    SELECT
                        food_entry_id,
                        photo_path,
                        similarity_score,
                        created_at
                    FROM find_similar_food_images(
                        %s::TEXT,
                        %s::vector,
                        %s::INTEGER,
                        %s::FLOAT
                    )
                    """,
                    (user_id, embedding_str, limit, distance_threshold)
                )

                rows = await cur.fetchall()

                # Convert to SimilarFoodMatch objects
                matches = []
                for row in rows:
                    match = SimilarFoodMatch(
                        food_entry_id=str(row["food_entry_id"]),
                        photo_path=row["photo_path"],
                        similarity_score=float(row["similarity_score"]),
                        created_at=row["created_at"],
                        confidence_level=""  # Will be set by _add_confidence_level
                    )
                    matches.append(match)

                return matches

    def _add_confidence_level(self, match: SimilarFoodMatch) -> SimilarFoodMatch:
        """
        Add confidence level to a match based on similarity score

        Args:
            match: Match without confidence level

        Returns:
            Match with confidence level set
        """
        score = match.similarity_score

        if score >= self.HIGH_CONFIDENCE_THRESHOLD:
            confidence = "high"
        elif score >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            confidence = "medium"
        else:
            confidence = "low"

        match.confidence_level = confidence
        return match

    async def get_user_image_count(self, user_id: str) -> int:
        """
        Get the number of food images indexed for a user

        Args:
            user_id: Telegram user ID

        Returns:
            Number of indexed images
        """
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM food_image_references
                    WHERE user_id = %s
                    """,
                    (user_id,)
                )

                row = await cur.fetchone()
                return row["count"] if row else 0


# Global service instance
_search_service: Optional[VisualFoodSearchService] = None


def get_visual_search_service() -> VisualFoodSearchService:
    """Get or create the global visual search service instance"""
    global _search_service

    if _search_service is None:
        _search_service = VisualFoodSearchService()

    return _search_service
