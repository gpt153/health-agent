"""
Plate Recognition Service

Service for detecting, matching, and calibrating plates/containers from food images.
Epic 009 - Phase 2: Plate Recognition & Calibration
"""
import logging
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime

from src.db.connection import db
from src.services.image_embedding import get_embedding_service, ImageEmbeddingError
from src.models.plate import (
    DetectedPlate,
    RecognizedPlate,
    PlateMetadata,
    PlateRegion,
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
    validate_calibration_result,
    calculate_confidence_from_method,
    merge_calibrations,
    PlateCalibrationError
)
from src.exceptions import ServiceError

logger = logging.getLogger(__name__)


class PlateRecognitionError(ServiceError):
    """Raised when plate recognition fails"""
    pass


class PlateRecognitionService:
    """
    Service for plate/container recognition and calibration

    Features:
    - Detect plates from food images
    - Match plates using CLIP embeddings
    - Register new plates automatically
    - Calibrate plate sizes from reference portions
    - Estimate portions using calibrated plates

    Architecture:
    - Reuses ImageEmbeddingService from Phase 1
    - Uses pgvector similarity search for matching
    - Stores plate data in recognized_plates table
    """

    # Matching configuration
    HIGH_MATCH_THRESHOLD = 0.90  # Very confident match
    MEDIUM_MATCH_THRESHOLD = 0.85  # Confident match
    LOW_MATCH_THRESHOLD = 0.75  # Possible match
    DEFAULT_MATCH_THRESHOLD = MEDIUM_MATCH_THRESHOLD

    # Calibration confidence thresholds
    HIGH_CALIBRATION_CONFIDENCE = 0.85
    MEDIUM_CALIBRATION_CONFIDENCE = 0.70

    def __init__(self) -> None:
        """Initialize the plate recognition service"""
        self.embedding_service = get_embedding_service()

    async def detect_plate_from_image(
        self,
        image_path: str | Path,
        user_id: str,
        auto_match: bool = True
    ) -> Optional[DetectedPlate]:
        """
        Detect and extract plate from food image

        Steps:
        1. Generate CLIP embedding for full image
        2. Extract plate metadata (type, color, shape) - simplified for MVP
        3. Optionally match against user's existing plates

        Args:
            image_path: Path to food photo
            user_id: Telegram user ID
            auto_match: Whether to automatically match against existing plates

        Returns:
            DetectedPlate or None if no plate detected

        Raises:
            PlateRecognitionError: If detection fails

        Note:
            MVP implementation uses full image embedding.
            Future enhancement: Segment plate region before embedding.
        """
        try:
            logger.info(f"Detecting plate from image: {image_path}")

            # Generate embedding for image (reuses Phase 1 infrastructure)
            embedding = await self.embedding_service.generate_embedding(
                image_path,
                use_cache=True
            )

            # MVP: Extract basic metadata from image
            # Future: Use Vision AI to detect plate characteristics
            metadata = await self._extract_plate_metadata_mvp(image_path)

            if metadata is None:
                logger.info(f"No plate detected in {image_path}")
                return None

            detected_plate = DetectedPlate(
                embedding=embedding,
                metadata=metadata,
                confidence=0.8,  # MVP confidence
                region=None  # MVP: No region detection yet
            )

            logger.info(
                f"Detected {metadata.plate_type} "
                f"(confidence {detected_plate.confidence:.2f})"
            )

            return detected_plate

        except ImageEmbeddingError as e:
            raise PlateRecognitionError(f"Failed to generate embedding: {e}")
        except Exception as e:
            logger.error(f"Plate detection failed: {e}", exc_info=True)
            raise PlateRecognitionError(f"Detection failed: {e}")

    async def match_plate(
        self,
        plate_embedding: list[float],
        user_id: str,
        threshold: float = DEFAULT_MATCH_THRESHOLD
    ) -> Optional[RecognizedPlate]:
        """
        Match plate embedding against user's recognized plates

        Uses pgvector similarity search with configurable threshold.

        Args:
            plate_embedding: 512-dimensional CLIP embedding
            user_id: Telegram user ID
            threshold: Minimum similarity score (0.0 to 1.0)

        Returns:
            RecognizedPlate if match found, None otherwise

        Raises:
            PlateRecognitionError: If matching fails
        """
        try:
            # Validate embedding
            if len(plate_embedding) != 512:
                raise PlateRecognitionError(
                    f"Invalid embedding dimension: {len(plate_embedding)}"
                )

            logger.info(
                f"Matching plate for user {user_id} "
                f"(threshold {threshold:.2f})"
            )

            # Search for similar plates
            matches = await self._search_similar_plates(
                user_id=user_id,
                query_embedding=plate_embedding,
                limit=1,
                distance_threshold=1.0 - threshold
            )

            if not matches:
                logger.info("No matching plates found")
                return None

            # Return best match
            best_match = matches[0]
            logger.info(
                f"Matched plate: {best_match.plate_name} "
                f"(similarity {1.0 - (1.0 - threshold):.2f}, "
                f"seen {best_match.times_recognized} times)"
            )

            return best_match

        except Exception as e:
            logger.error(f"Plate matching failed: {e}", exc_info=True)
            raise PlateRecognitionError(f"Matching failed: {e}")

    async def register_new_plate(
        self,
        user_id: str,
        embedding: list[float],
        metadata: PlateMetadata
    ) -> RecognizedPlate:
        """
        Register a new plate in the user's database

        Creates a new entry in recognized_plates table with auto-generated name.

        Args:
            user_id: Telegram user ID
            embedding: 512-dimensional CLIP embedding
            metadata: Plate characteristics

        Returns:
            RecognizedPlate with database ID

        Raises:
            PlateRecognitionError: If registration fails
        """
        try:
            # Validate embedding
            if len(embedding) != 512:
                raise PlateRecognitionError(
                    f"Invalid embedding dimension: {len(embedding)}"
                )

            # Generate auto name
            plate_name = await self._generate_plate_name(user_id, metadata)

            logger.info(f"Registering new plate for user {user_id}: {plate_name}")

            # Insert into database
            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    # Convert embedding to pgvector format
                    embedding_str = f"[{','.join(str(x) for x in embedding)}]"

                    await cur.execute(
                        """
                        INSERT INTO recognized_plates
                        (user_id, plate_name, embedding, plate_type, color, shape,
                         estimated_diameter_cm, estimated_capacity_ml, model_version)
                        VALUES (%s, %s, %s::vector, %s, %s, %s, %s, %s, %s)
                        RETURNING id, created_at, updated_at
                        """,
                        (
                            user_id,
                            plate_name,
                            embedding_str,
                            metadata.plate_type,
                            metadata.color,
                            metadata.shape,
                            metadata.estimated_diameter_cm,
                            metadata.estimated_capacity_ml,
                            "clip-vit-base-patch32"
                        )
                    )

                    row = await cur.fetchone()
                    plate_id = str(row["id"])
                    created_at = row["created_at"]
                    updated_at = row["updated_at"]

                    await conn.commit()

            # Build RecognizedPlate object
            recognized_plate = RecognizedPlate(
                id=plate_id,
                user_id=user_id,
                plate_name=plate_name,
                embedding=embedding,
                plate_type=metadata.plate_type,
                color=metadata.color,
                shape=metadata.shape,
                estimated_diameter_cm=metadata.estimated_diameter_cm,
                estimated_capacity_ml=metadata.estimated_capacity_ml,
                times_recognized=1,
                first_seen_at=created_at,
                last_seen_at=created_at,
                is_calibrated=False,
                calibration_confidence=None,
                calibration_method=None,
                model_version="clip-vit-base-patch32",
                created_at=created_at,
                updated_at=updated_at
            )

            logger.info(f"Registered new plate: {plate_id} ({plate_name})")

            return recognized_plate

        except Exception as e:
            logger.error(f"Plate registration failed: {e}", exc_info=True)
            raise PlateRecognitionError(f"Registration failed: {e}")

    async def calibrate_plate(
        self,
        calibration_input: CalibrationInput
    ) -> CalibrationResult:
        """
        Calibrate plate size from various input methods

        Supports:
        - reference_portion: Calibrate from known portion weight
        - user_input: Calibrate from user-provided dimensions
        - auto_inferred: Calibrate from usage patterns (future)

        Args:
            calibration_input: Calibration method and data

        Returns:
            CalibrationResult with success status and new dimensions

        Raises:
            PlateRecognitionError: If calibration fails
        """
        try:
            # Validate inputs
            calibration_input.validate_inputs()

            logger.info(
                f"Calibrating plate {calibration_input.plate_id} "
                f"using method: {calibration_input.method}"
            )

            # Get existing plate data
            plate = await self.get_plate_by_id(calibration_input.plate_id)
            if plate is None:
                raise PlateRecognitionError(
                    f"Plate {calibration_input.plate_id} not found"
                )

            # Perform calibration based on method
            if calibration_input.method == "reference_portion":
                result = await self._calibrate_from_reference_portion(
                    plate, calibration_input
                )
            elif calibration_input.method == "user_input":
                result = await self._calibrate_from_user_input(
                    plate, calibration_input
                )
            elif calibration_input.method == "auto_inferred":
                result = await self._calibrate_auto_inferred(
                    plate, calibration_input
                )
            else:
                raise PlateRecognitionError(
                    f"Unknown calibration method: {calibration_input.method}"
                )

            # Validate result
            is_valid, message = validate_calibration_result(result, plate.plate_type)
            if not is_valid:
                logger.warning(f"Calibration validation failed: {message}")
                result.success = False
                result.message = f"Validation failed: {message}"
                return result

            # Update database
            if result.success:
                await self._update_plate_calibration(result)

            logger.info(f"Calibration {'succeeded' if result.success else 'failed'}: {result.message}")

            return result

        except PlateCalibrationError as e:
            return CalibrationResult(
                plate_id=calibration_input.plate_id,
                calibration_method=calibration_input.method,
                estimated_capacity_ml=None,
                estimated_diameter_cm=None,
                confidence=0.0,
                success=False,
                message=f"Calibration error: {e}"
            )
        except Exception as e:
            logger.error(f"Calibration failed: {e}", exc_info=True)
            raise PlateRecognitionError(f"Calibration failed: {e}")

    async def estimate_portion_from_plate(
        self,
        plate_id: str,
        fill_percentage: float,
        food_density_g_per_ml: float = 1.0
    ) -> PortionEstimate:
        """
        Estimate portion size based on calibrated plate

        Args:
            plate_id: UUID of calibrated plate
            fill_percentage: How full the container is (0.0 to 1.0)
            food_density_g_per_ml: Density of food (default 1.0 for water-like)

        Returns:
            PortionEstimate with estimated weight and confidence

        Raises:
            PlateRecognitionError: If estimation fails
        """
        try:
            # Get plate data
            plate = await self.get_plate_by_id(plate_id)
            if plate is None:
                raise PlateRecognitionError(f"Plate {plate_id} not found")

            if not plate.is_calibrated or plate.estimated_capacity_ml is None:
                # Plate not calibrated - return low-confidence estimate
                return PortionEstimate(
                    estimated_grams=200.0,  # Generic fallback
                    confidence=0.3,
                    method="visual_estimation",
                    plate_id=plate_id,
                    notes="Plate not calibrated"
                )

            # Calculate portion from calibrated capacity
            estimated_grams = estimate_portion_from_capacity(
                total_capacity_ml=plate.estimated_capacity_ml,
                fill_percentage=fill_percentage,
                density_g_per_ml=food_density_g_per_ml
            )

            # Calculate confidence
            base_confidence = plate.calibration_confidence or 0.7
            fill_confidence = 0.9 if 0.3 <= fill_percentage <= 0.9 else 0.7
            overall_confidence = min(1.0, base_confidence * fill_confidence)

            logger.info(
                f"Portion estimate: {plate.estimated_capacity_ml}ml × {fill_percentage*100}% "
                f"× {food_density_g_per_ml} g/ml = {estimated_grams:.1f}g "
                f"(confidence {overall_confidence:.2f})"
            )

            return PortionEstimate(
                estimated_grams=estimated_grams,
                confidence=overall_confidence,
                method="calibrated_plate",
                plate_id=plate_id,
                notes=f"Based on calibrated {plate.plate_name}"
            )

        except Exception as e:
            logger.error(f"Portion estimation failed: {e}", exc_info=True)
            raise PlateRecognitionError(f"Estimation failed: {e}")

    async def link_food_entry_to_plate(
        self,
        food_entry_id: str,
        recognized_plate_id: str,
        user_id: str,
        confidence_score: float,
        detection_method: str = "auto_detected",
        plate_region: Optional[dict] = None
    ) -> FoodEntryPlateLink:
        """
        Link a food entry to a recognized plate

        Args:
            food_entry_id: UUID of food entry
            recognized_plate_id: UUID of recognized plate
            user_id: Telegram user ID
            confidence_score: Matching confidence (0.0 to 1.0)
            detection_method: How plate was linked
            plate_region: Optional bounding box data

        Returns:
            FoodEntryPlateLink

        Raises:
            PlateRecognitionError: If linking fails
        """
        try:
            logger.info(
                f"Linking food entry {food_entry_id} to plate {recognized_plate_id} "
                f"(confidence {confidence_score:.2f})"
            )

            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    # Insert link
                    await cur.execute(
                        """
                        INSERT INTO food_entry_plates
                        (food_entry_id, recognized_plate_id, user_id, confidence_score,
                         detection_method, plate_region)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (food_entry_id, recognized_plate_id) DO UPDATE
                        SET confidence_score = EXCLUDED.confidence_score,
                            detection_method = EXCLUDED.detection_method
                        RETURNING id, created_at
                        """,
                        (
                            food_entry_id,
                            recognized_plate_id,
                            user_id,
                            confidence_score,
                            detection_method,
                            plate_region
                        )
                    )

                    row = await cur.fetchone()
                    link_id = str(row["id"])
                    created_at = row["created_at"]

                    # Update plate usage statistics
                    await cur.execute(
                        "SELECT update_plate_usage(%s)",
                        (recognized_plate_id,)
                    )

                    await conn.commit()

            link = FoodEntryPlateLink(
                id=link_id,
                food_entry_id=food_entry_id,
                recognized_plate_id=recognized_plate_id,
                user_id=user_id,
                confidence_score=confidence_score,
                detection_method=detection_method,
                plate_region=plate_region,
                created_at=created_at
            )

            logger.info(f"Linked food entry to plate: {link_id}")

            return link

        except Exception as e:
            logger.error(f"Linking failed: {e}", exc_info=True)
            raise PlateRecognitionError(f"Linking failed: {e}")

    async def get_plate_by_id(self, plate_id: str) -> Optional[RecognizedPlate]:
        """Get plate by ID"""
        try:
            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT id, user_id, plate_name, embedding, plate_type,
                               color, shape, estimated_diameter_cm, estimated_capacity_ml,
                               times_recognized, first_seen_at, last_seen_at,
                               is_calibrated, calibration_confidence, calibration_method,
                               model_version, created_at, updated_at
                        FROM recognized_plates
                        WHERE id = %s
                        """,
                        (plate_id,)
                    )

                    row = await cur.fetchone()
                    if not row:
                        return None

                    # Parse embedding
                    embedding = row["embedding"]
                    if isinstance(embedding, str):
                        embedding = [float(x) for x in embedding.strip("[]").split(",")]

                    return RecognizedPlate(
                        id=str(row["id"]),
                        user_id=row["user_id"],
                        plate_name=row["plate_name"],
                        embedding=embedding,
                        plate_type=row["plate_type"],
                        color=row["color"],
                        shape=row["shape"],
                        estimated_diameter_cm=row["estimated_diameter_cm"],
                        estimated_capacity_ml=row["estimated_capacity_ml"],
                        times_recognized=row["times_recognized"],
                        first_seen_at=row["first_seen_at"],
                        last_seen_at=row["last_seen_at"],
                        is_calibrated=row["is_calibrated"],
                        calibration_confidence=row["calibration_confidence"],
                        calibration_method=row["calibration_method"],
                        model_version=row["model_version"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"]
                    )

        except Exception as e:
            logger.error(f"Failed to get plate: {e}", exc_info=True)
            return None

    async def get_user_plate_statistics(self, user_id: str) -> PlateStatistics:
        """Get summary statistics for user's plates"""
        try:
            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT * FROM get_user_plate_statistics(%s)",
                        (user_id,)
                    )

                    row = await cur.fetchone()
                    if not row:
                        return PlateStatistics(
                            total_plates=0,
                            calibrated_plates=0,
                            total_recognitions=0
                        )

                    return PlateStatistics(
                        total_plates=row["total_plates"],
                        calibrated_plates=row["calibrated_plates"],
                        total_recognitions=row["total_recognitions"],
                        most_used_plate_id=str(row["most_used_plate_id"]) if row["most_used_plate_id"] else None,
                        most_used_plate_name=row["most_used_plate_name"],
                        most_used_count=row["most_used_count"]
                    )

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}", exc_info=True)
            raise PlateRecognitionError(f"Statistics retrieval failed: {e}")

    # Private helper methods

    async def _extract_plate_metadata_mvp(
        self,
        image_path: str | Path
    ) -> Optional[PlateMetadata]:
        """
        MVP: Extract basic plate metadata

        For MVP, we assume all images have plates and use generic metadata.
        Future enhancement: Use Vision AI to detect plate characteristics.
        """
        # MVP: Always return generic plate metadata
        return PlateMetadata(
            plate_type="plate",  # Default assumption
            color="white",       # Most common
            shape="round",       # Most common
            estimated_diameter_cm=None,  # Unknown
            estimated_capacity_ml=None   # Unknown
        )

    async def _search_similar_plates(
        self,
        user_id: str,
        query_embedding: list[float],
        limit: int,
        distance_threshold: float
    ) -> list[RecognizedPlate]:
        """Search for similar plates using pgvector"""
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                # Convert embedding to pgvector format
                embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

                await cur.execute(
                    """
                    SELECT plate_id, plate_name, plate_type, similarity_score,
                           times_recognized, is_calibrated, estimated_diameter_cm,
                           estimated_capacity_ml
                    FROM find_similar_plates(%s, %s::vector, %s, %s)
                    """,
                    (user_id, embedding_str, limit, distance_threshold)
                )

                rows = await cur.fetchall()

                matches = []
                for row in rows:
                    # Get full plate data
                    plate = await self.get_plate_by_id(str(row["plate_id"]))
                    if plate:
                        matches.append(plate)

                return matches

    async def _generate_plate_name(
        self,
        user_id: str,
        metadata: PlateMetadata
    ) -> str:
        """Generate auto name for new plate"""
        # Count existing plates of this type
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM recognized_plates
                    WHERE user_id = %s AND plate_type = %s
                    """,
                    (user_id, metadata.plate_type)
                )

                row = await cur.fetchone()
                count = row["count"] if row else 0

        # Generate name
        color_str = f"{metadata.color} " if metadata.color else ""
        number = count + 1

        name = f"{color_str}{metadata.plate_type} #{number}".title()

        return name

    async def _calibrate_from_reference_portion(
        self,
        plate: RecognizedPlate,
        calibration_input: CalibrationInput
    ) -> CalibrationResult:
        """Calibrate from known portion weight"""
        try:
            # Calculate capacity
            capacity_ml = calibrate_from_reference_portion(
                portion_grams=calibration_input.reference_portion_grams,
                fill_percentage=calibration_input.visual_fill_percentage
            )

            # Estimate diameter if applicable
            diameter_cm = None
            if plate.plate_type in ["bowl", "cup"]:
                diameter_cm = estimate_diameter_from_capacity(
                    capacity_ml, plate.plate_type
                )

            # Merge with existing calibration if exists
            if plate.is_calibrated and plate.estimated_capacity_ml:
                capacity_ml, confidence = merge_calibrations(
                    existing_capacity=plate.estimated_capacity_ml,
                    new_capacity=capacity_ml,
                    existing_confidence=plate.calibration_confidence or 0.7,
                    new_confidence=calibration_input.confidence
                )
            else:
                confidence = calibration_input.confidence

            return CalibrationResult(
                plate_id=plate.id,
                calibration_method="reference_portion",
                estimated_capacity_ml=capacity_ml,
                estimated_diameter_cm=diameter_cm,
                confidence=confidence,
                success=True,
                message=f"Calibrated from {calibration_input.reference_portion_grams}g portion"
            )

        except PlateCalibrationError as e:
            raise e

    async def _calibrate_from_user_input(
        self,
        plate: RecognizedPlate,
        calibration_input: CalibrationInput
    ) -> CalibrationResult:
        """Calibrate from explicit user input"""
        diameter_cm = calibration_input.user_provided_diameter_cm
        capacity_ml = calibration_input.user_provided_capacity_ml

        # Calculate missing dimension if possible
        if diameter_cm and not capacity_ml:
            capacity_ml = estimate_capacity_from_diameter(
                diameter_cm, plate.plate_type
            )
        elif capacity_ml and not diameter_cm:
            diameter_cm = estimate_diameter_from_capacity(
                capacity_ml, plate.plate_type
            )

        return CalibrationResult(
            plate_id=plate.id,
            calibration_method="user_input",
            estimated_capacity_ml=capacity_ml,
            estimated_diameter_cm=diameter_cm,
            confidence=calibration_input.confidence,
            success=True,
            message="Calibrated from user input"
        )

    async def _calibrate_auto_inferred(
        self,
        plate: RecognizedPlate,
        calibration_input: CalibrationInput
    ) -> CalibrationResult:
        """Auto-infer calibration from usage patterns (future implementation)"""
        # Future: Analyze historical food entries to infer plate size
        return CalibrationResult(
            plate_id=plate.id,
            calibration_method="auto_inferred",
            estimated_capacity_ml=None,
            estimated_diameter_cm=None,
            confidence=0.0,
            success=False,
            message="Auto-inference not yet implemented"
        )

    async def _update_plate_calibration(
        self,
        result: CalibrationResult
    ) -> None:
        """Update plate calibration in database"""
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE recognized_plates
                    SET estimated_capacity_ml = %s,
                        estimated_diameter_cm = %s,
                        is_calibrated = TRUE,
                        calibration_confidence = %s,
                        calibration_method = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (
                        result.estimated_capacity_ml,
                        result.estimated_diameter_cm,
                        result.confidence,
                        result.calibration_method,
                        result.plate_id
                    )
                )

                await conn.commit()


# Global service instance
_plate_recognition_service: Optional[PlateRecognitionService] = None


def get_plate_recognition_service() -> PlateRecognitionService:
    """Get or create the global plate recognition service instance"""
    global _plate_recognition_service

    if _plate_recognition_service is None:
        _plate_recognition_service = PlateRecognitionService()

    return _plate_recognition_service
