"""
Portion Comparison Service

Service for comparing food portions between current and reference images
using visual analysis and plate calibration data.

Epic 009 - Phase 4: Portion Comparison
"""
import logging
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime

from src.db.connection import db
from src.services.visual_food_search import get_visual_search_service, VisualSearchError
from src.services.plate_recognition import get_plate_recognition_service, PlateRecognitionError
from src.models.portion import (
    BoundingBox,
    FoodItemDetection,
    PortionComparison,
    PortionEstimateAccuracy,
    ComparisonContext,
    PortionAccuracyStats
)
from src.exceptions import ServiceError

logger = logging.getLogger(__name__)


class PortionComparisonError(ServiceError):
    """Raised when portion comparison fails"""
    pass


class PortionComparisonService:
    """
    Service for comparing food portions between images

    Features:
    - Detect food items using Vision AI bounding boxes (MVP: heuristics)
    - Compare areas between current and reference images
    - Calculate portion estimates using plate calibration
    - Generate comparison context for Vision AI enhancement
    - Track accuracy over time for learning

    Architecture:
    - Leverages Phase 1 (VisualFoodSearchService) for finding similar images
    - Leverages Phase 2 (PlateRecognitionService) for plate calibration
    - Enhances existing Vision AI with comparison context
    """

    # Similarity threshold for reference image matching
    SIMILAR_IMAGE_THRESHOLD = 0.80  # 80% similarity to be considered "same meal"

    # Area difference thresholds
    MIN_AREA_DIFFERENCE = 0.05  # Ignore <5% differences (noise)
    SIGNIFICANT_DIFFERENCE = 0.15  # >15% is significant

    # Confidence thresholds
    HIGH_CONFIDENCE = 0.80
    MEDIUM_CONFIDENCE = 0.60

    # Default density (g/ml)
    DEFAULT_DENSITY_G_PER_ML = 1.0  # Water-like density

    # Food type densities (estimated g/ml)
    FOOD_DENSITIES = {
        "rice": 0.75,
        "chicken": 1.1,
        "fish": 1.0,
        "vegetables": 0.6,
        "pasta": 0.7,
        "soup": 1.0,
        "salad": 0.5,
        "meat": 1.1,
        "beans": 0.8,
        "bread": 0.4
    }

    def __init__(self) -> None:
        """Initialize the portion comparison service"""
        self.visual_search_service = get_visual_search_service()
        self.plate_service = get_plate_recognition_service()

    async def detect_food_items(
        self,
        photo_path: str,
        user_id: str,
        food_entry_id: str,
        food_names: Optional[list[str]] = None
    ) -> list[FoodItemDetection]:
        """
        Detect individual food items and their bounding boxes

        MVP Implementation: Uses simple heuristic (single centered item)
        Future: Use Vision AI or object detection API for proper bounding boxes

        Args:
            photo_path: Path to food photo
            user_id: Telegram user ID
            food_entry_id: UUID of food entry
            food_names: Optional list of food names from Vision AI

        Returns:
            List of detected food items with bounding boxes

        Raises:
            PortionComparisonError: If detection fails
        """
        try:
            logger.info(f"Detecting food items in {photo_path}")

            detections = []

            if not food_names:
                # No food names provided - create generic detection
                food_names = ["food"]

            # MVP: Simple heuristic - single centered bounding box per food item
            # For multiple items, divide the image into regions
            for idx, food_name in enumerate(food_names):
                # Create bounding box (MVP: centered box covering most of image)
                bbox = self._create_heuristic_bbox(idx, len(food_names))

                # Calculate pixel area (normalized area * image dimensions)
                # For MVP, use normalized area directly
                pixel_area = bbox.area

                detection = FoodItemDetection(
                    id=f"temp_{idx}",  # Will be replaced with UUID from DB
                    food_entry_id=food_entry_id,
                    user_id=user_id,
                    photo_path=photo_path,
                    item_name=food_name.lower(),
                    bbox=bbox,
                    pixel_area=pixel_area,
                    detection_confidence=0.7,  # MVP confidence
                    detection_method="heuristic"
                )

                detections.append(detection)

            logger.info(f"Detected {len(detections)} food items")
            return detections

        except Exception as e:
            logger.error(f"Food item detection failed: {e}", exc_info=True)
            raise PortionComparisonError(f"Detection failed: {e}")

    async def compare_portions(
        self,
        current_photo_path: str,
        reference_photo_path: str,
        user_id: str,
        current_food_entry_id: str,
        reference_food_entry_id: str,
        current_food_names: Optional[list[str]] = None,
        reference_food_names: Optional[list[str]] = None,
        plate_id: Optional[str] = None
    ) -> list[PortionComparison]:
        """
        Compare portions between current and reference images

        Steps:
        1. Detect food items in both images
        2. Match items by name/type
        3. Calculate area differences
        4. Convert to weight estimates using plate calibration
        5. Generate comparison records

        Args:
            current_photo_path: Current food photo
            reference_photo_path: Reference food photo
            user_id: Telegram user ID
            current_food_entry_id: UUID of current entry
            reference_food_entry_id: UUID of reference entry
            current_food_names: Food names from current image
            reference_food_names: Food names from reference image
            plate_id: Optional plate ID for calibration

        Returns:
            List of portion comparisons per matched food item

        Raises:
            PortionComparisonError: If comparison fails
        """
        try:
            logger.info(
                f"Comparing portions: {current_photo_path} vs {reference_photo_path}"
            )

            # 1. Detect food items in both images
            current_detections = await self.detect_food_items(
                current_photo_path, user_id, current_food_entry_id,
                current_food_names
            )

            reference_detections = await self.detect_food_items(
                reference_photo_path, user_id, reference_food_entry_id,
                reference_food_names
            )

            # 2. Match food items between images
            matched_pairs = self._match_food_items(
                current_detections, reference_detections
            )

            if not matched_pairs:
                logger.warning("No matching food items found between images")
                return []

            # 3. Get plate info for calibration (if available)
            plate = None
            if plate_id:
                plate = await self.plate_service.get_plate_by_id(plate_id)

            # 4. Calculate comparisons
            comparisons = []
            for current, reference in matched_pairs:
                comparison = await self._calculate_portion_comparison(
                    current, reference,
                    user_id, current_food_entry_id, reference_food_entry_id,
                    plate
                )
                comparisons.append(comparison)

            logger.info(f"Created {len(comparisons)} portion comparisons")
            return comparisons

        except Exception as e:
            logger.error(f"Portion comparison failed: {e}", exc_info=True)
            raise PortionComparisonError(f"Comparison failed: {e}")

    async def calculate_portion_estimate(
        self,
        area_difference_ratio: float,
        reference_grams: float,
        plate_capacity_ml: Optional[float] = None,
        food_density: float = DEFAULT_DENSITY_G_PER_ML
    ) -> tuple[float, float]:
        """
        Calculate portion estimate from area difference

        Assumptions:
        - 2D area difference approximates 3D volume difference
        - Consistent camera angles between photos
        - Food density is relatively uniform

        Args:
            area_difference_ratio: (current - ref) / ref
            reference_grams: Known weight of reference portion
            plate_capacity_ml: Optional plate capacity for calibration
            food_density: Density of food in g/ml

        Returns:
            (estimated_grams_difference, confidence)
        """
        try:
            # Simple linear approximation: area ratio ≈ volume ratio
            # estimated_difference = reference_grams * area_ratio
            estimated_diff = reference_grams * area_difference_ratio

            # Calculate confidence based on multiple factors
            confidence = self._calculate_estimate_confidence(
                abs(area_difference_ratio),
                plate_capacity_ml is not None,
                abs(estimated_diff)
            )

            logger.debug(
                f"Portion estimate: {area_difference_ratio*100:.1f}% area change "
                f"→ {estimated_diff:+.1f}g (confidence {confidence:.2f})"
            )

            return estimated_diff, confidence

        except Exception as e:
            logger.error(f"Portion estimation failed: {e}", exc_info=True)
            return 0.0, 0.3  # Return neutral estimate with low confidence

    async def generate_comparison_context(
        self,
        comparisons: list[PortionComparison],
        plate_name: Optional[str] = None,
        reference_date: Optional[datetime] = None
    ) -> ComparisonContext:
        """
        Generate context for Vision AI enhancement

        Creates natural language descriptions like:
        "This looks like your meal from yesterday, but with:
        - More rice (estimated +30g)
        - Less chicken (estimated -50g)
        Using your blue plate #1 (calibrated)"

        Args:
            comparisons: List of portion comparisons
            plate_name: Optional plate name for context
            reference_date: Optional reference image date

        Returns:
            ComparisonContext for Vision AI
        """
        try:
            # Build portion differences list
            portion_differences = []
            for comp in comparisons:
                if abs(comp.area_difference_ratio) < self.MIN_AREA_DIFFERENCE:
                    # Skip insignificant differences
                    continue

                # Format difference
                item_name = comp.item_name.capitalize()
                pct = abs(comp.percentage_difference)

                if comp.estimated_grams_difference:
                    grams = abs(comp.estimated_grams_difference)
                    if comp.is_larger:
                        diff_text = f"More {item_name} (~+{pct:.0f}%, ~+{grams:.0f}g)"
                    else:
                        diff_text = f"Less {item_name} (~-{pct:.0f}%, ~-{grams:.0f}g)"
                else:
                    if comp.is_larger:
                        diff_text = f"More {item_name} (~+{pct:.0f}%)"
                    else:
                        diff_text = f"Less {item_name} (~-{pct:.0f}%)"

                portion_differences.append(diff_text)

            # Build plate info
            plate_info = None
            if plate_name:
                plate_info = f"Using your {plate_name}"

            # Build confidence notes
            avg_confidence = sum(c.confidence for c in comparisons) / len(comparisons)
            if avg_confidence >= self.HIGH_CONFIDENCE:
                confidence_notes = "High confidence estimate (calibrated plate)"
            elif avg_confidence >= self.MEDIUM_CONFIDENCE:
                confidence_notes = "Medium confidence estimate"
            else:
                confidence_notes = "Low confidence estimate (consider manual adjustment)"

            # Build summary
            if portion_differences:
                summary = "Similar to a previous meal, with some portion differences"
            else:
                summary = "Very similar portions to a previous meal"

            context = ComparisonContext(
                reference_date=reference_date,
                portion_differences=portion_differences,
                plate_info=plate_info,
                confidence_notes=confidence_notes,
                summary=summary
            )

            logger.info(f"Generated comparison context with {len(portion_differences)} differences")
            return context

        except Exception as e:
            logger.error(f"Context generation failed: {e}", exc_info=True)
            # Return minimal context on error
            return ComparisonContext(
                confidence_notes="Unable to generate detailed comparison"
            )

    async def track_estimate_accuracy(
        self,
        portion_comparison_id: str,
        user_id: str,
        estimated_grams: float,
        user_confirmed_grams: float,
        plate_id: Optional[str] = None,
        food_item_type: str = "unknown",
        visual_fill_percentage: Optional[float] = None
    ) -> PortionEstimateAccuracy:
        """
        Track accuracy of portion estimate for learning

        Stores estimate vs actual for system improvement.

        Args:
            portion_comparison_id: UUID of comparison
            user_id: Telegram user ID
            estimated_grams: What we estimated
            user_confirmed_grams: What user confirmed
            plate_id: Optional plate used
            food_item_type: Type of food
            visual_fill_percentage: Optional fill percentage

        Returns:
            Accuracy record

        Raises:
            PortionComparisonError: If tracking fails
        """
        try:
            # Calculate variance
            variance_pct = abs(estimated_grams - user_confirmed_grams) / abs(user_confirmed_grams) * 100

            logger.info(
                f"Tracking accuracy: estimated {estimated_grams}g, "
                f"actual {user_confirmed_grams}g (variance {variance_pct:.1f}%)"
            )

            # Store in database
            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO portion_estimate_accuracy
                        (user_id, portion_comparison_id, estimated_grams,
                         user_confirmed_grams, variance_percentage, plate_id,
                         food_item_type, visual_fill_percentage)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id, created_at
                        """,
                        (
                            user_id, portion_comparison_id, estimated_grams,
                            user_confirmed_grams, variance_pct, plate_id,
                            food_item_type, visual_fill_percentage
                        )
                    )

                    row = await cur.fetchone()
                    accuracy_id = str(row["id"])
                    created_at = row["created_at"]

                    await conn.commit()

            accuracy = PortionEstimateAccuracy(
                id=accuracy_id,
                user_id=user_id,
                portion_comparison_id=portion_comparison_id,
                estimated_grams=estimated_grams,
                user_confirmed_grams=user_confirmed_grams,
                variance_percentage=variance_pct,
                plate_id=plate_id,
                food_item_type=food_item_type,
                visual_fill_percentage=visual_fill_percentage,
                created_at=created_at
            )

            logger.info(f"Stored accuracy record: {accuracy_id} (grade: {accuracy.accuracy_grade})")
            return accuracy

        except Exception as e:
            logger.error(f"Accuracy tracking failed: {e}", exc_info=True)
            raise PortionComparisonError(f"Tracking failed: {e}")

    async def find_reference_image(
        self,
        current_photo_path: str,
        user_id: str,
        food_item_name: Optional[str] = None
    ) -> Optional[tuple[str, str, datetime]]:
        """
        Find best reference image for comparison using Phase 1 visual similarity

        Args:
            current_photo_path: Current food photo
            user_id: Telegram user ID
            food_item_name: Optional food item name for filtering

        Returns:
            (reference_photo_path, reference_food_entry_id, created_at) or None

        Raises:
            PortionComparisonError: If search fails
        """
        try:
            logger.info(f"Finding reference image for {current_photo_path}")

            # Use Phase 1 visual similarity search
            matches = await self.visual_search_service.find_similar_foods(
                user_id=user_id,
                query_image_path=current_photo_path,
                limit=5,  # Get top 5 matches
                min_similarity=self.SIMILAR_IMAGE_THRESHOLD
            )

            if not matches:
                logger.info("No similar reference images found")
                return None

            # Get best match (highest similarity)
            best_match = matches[0]

            logger.info(
                f"Found reference image: {best_match.photo_path} "
                f"(similarity {best_match.similarity_score:.2f})"
            )

            return (
                best_match.photo_path,
                best_match.food_entry_id,
                best_match.created_at
            )

        except VisualSearchError as e:
            logger.error(f"Reference image search failed: {e}")
            return None  # Don't fail entire flow, just skip comparison
        except Exception as e:
            logger.error(f"Reference search failed: {e}", exc_info=True)
            raise PortionComparisonError(f"Reference search failed: {e}")

    async def get_user_accuracy_stats(
        self,
        user_id: str
    ) -> PortionAccuracyStats:
        """
        Get accuracy statistics for a user

        Returns:
            PortionAccuracyStats with metrics

        Raises:
            PortionComparisonError: If query fails
        """
        try:
            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT * FROM get_user_portion_accuracy(%s)",
                        (user_id,)
                    )

                    row = await cur.fetchone()

                    if not row or row["total_estimates"] == 0:
                        # No data yet - return zeros
                        return PortionAccuracyStats(
                            total_estimates=0,
                            avg_variance_percentage=0.0,
                            within_20_percent=0,
                            within_10_percent=0,
                            accuracy_rate=0.0
                        )

                    return PortionAccuracyStats(
                        total_estimates=row["total_estimates"],
                        avg_variance_percentage=row["avg_variance_percentage"] or 0.0,
                        within_20_percent=row["within_20_percent"],
                        within_10_percent=row["within_10_percent"],
                        accuracy_rate=row["accuracy_rate"] or 0.0
                    )

        except Exception as e:
            logger.error(f"Failed to get accuracy stats: {e}", exc_info=True)
            raise PortionComparisonError(f"Stats retrieval failed: {e}")

    # Private helper methods

    def _create_heuristic_bbox(
        self,
        item_index: int,
        total_items: int
    ) -> BoundingBox:
        """
        Create heuristic bounding box for food item

        MVP: Simple centered boxes, divided if multiple items

        Args:
            item_index: Index of current item (0-based)
            total_items: Total number of items

        Returns:
            BoundingBox
        """
        if total_items == 1:
            # Single item: large centered box
            return BoundingBox(x=0.15, y=0.15, width=0.7, height=0.7)

        elif total_items == 2:
            # Two items: split horizontally
            if item_index == 0:
                return BoundingBox(x=0.1, y=0.2, width=0.35, height=0.6)
            else:
                return BoundingBox(x=0.55, y=0.2, width=0.35, height=0.6)

        else:
            # Three or more: divide into grid
            # Simple grid layout
            cols = 2
            row = item_index // cols
            col = item_index % cols

            box_width = 0.4
            box_height = 0.4
            x = 0.1 + (col * 0.5)
            y = 0.1 + (row * 0.45)

            return BoundingBox(x=x, y=y, width=box_width, height=box_height)

    def _match_food_items(
        self,
        current_detections: list[FoodItemDetection],
        reference_detections: list[FoodItemDetection]
    ) -> list[tuple[FoodItemDetection, FoodItemDetection]]:
        """
        Match food items between current and reference images

        Uses name matching for now. Future: Use embeddings or visual similarity.

        Args:
            current_detections: Detections from current image
            reference_detections: Detections from reference image

        Returns:
            List of matched pairs: [(current, reference), ...]
        """
        matched_pairs = []

        for current in current_detections:
            # Find matching item in reference by name
            for reference in reference_detections:
                if self._items_match(current.item_name, reference.item_name):
                    matched_pairs.append((current, reference))
                    break  # Match found, move to next current item

        return matched_pairs

    def _items_match(self, name1: str, name2: str) -> bool:
        """
        Check if two food item names match

        Uses simple string matching for MVP.
        Future: Use embeddings or NLP for fuzzy matching.

        Args:
            name1: First food name
            name2: Second food name

        Returns:
            True if names match
        """
        # Normalize names
        n1 = name1.lower().strip()
        n2 = name2.lower().strip()

        # Exact match
        if n1 == n2:
            return True

        # Substring match (e.g., "rice" matches "fried rice")
        if n1 in n2 or n2 in n1:
            return True

        return False

    async def _calculate_portion_comparison(
        self,
        current: FoodItemDetection,
        reference: FoodItemDetection,
        user_id: str,
        current_food_entry_id: str,
        reference_food_entry_id: str,
        plate = None
    ) -> PortionComparison:
        """
        Calculate portion comparison for a matched pair

        Args:
            current: Current food item detection
            reference: Reference food item detection
            user_id: Telegram user ID
            current_food_entry_id: Current entry ID
            reference_food_entry_id: Reference entry ID
            plate: Optional RecognizedPlate for calibration

        Returns:
            PortionComparison
        """
        # Calculate area difference ratio
        current_area = current.pixel_area
        reference_area = reference.pixel_area
        area_ratio = (current_area - reference_area) / reference_area

        # Get food density for this food type
        food_density = self._get_food_density(current.item_name)

        # Estimate weight difference (assuming reference is ~100g for MVP)
        # In production, this would come from the actual food entry
        reference_grams = 100.0  # MVP assumption
        plate_capacity = plate.estimated_capacity_ml if plate and plate.is_calibrated else None

        estimated_diff, confidence = await self.calculate_portion_estimate(
            area_difference_ratio=area_ratio,
            reference_grams=reference_grams,
            plate_capacity_ml=plate_capacity,
            food_density=food_density
        )

        # Create comparison record
        comparison = PortionComparison(
            id="temp",  # Will be replaced with UUID from DB
            user_id=user_id,
            current_food_entry_id=current_food_entry_id,
            reference_food_entry_id=reference_food_entry_id,
            item_name=current.item_name,
            current_area=current_area,
            reference_area=reference_area,
            area_difference_ratio=area_ratio,
            estimated_grams_difference=estimated_diff,
            confidence=confidence,
            plate_id=plate.id if plate else None
        )

        return comparison

    def _get_food_density(self, food_name: str) -> float:
        """
        Get estimated density for a food type

        Args:
            food_name: Food item name

        Returns:
            Estimated density in g/ml
        """
        # Normalize name
        name_lower = food_name.lower()

        # Check known densities
        for food_type, density in self.FOOD_DENSITIES.items():
            if food_type in name_lower:
                return density

        # Default density
        return self.DEFAULT_DENSITY_G_PER_ML

    def _calculate_estimate_confidence(
        self,
        abs_area_ratio: float,
        has_calibrated_plate: bool,
        abs_grams_diff: float
    ) -> float:
        """
        Calculate confidence for portion estimate

        Factors:
        - Smaller differences → higher confidence
        - Calibrated plate → higher confidence
        - Extreme differences → lower confidence

        Args:
            abs_area_ratio: Absolute area difference ratio
            has_calibrated_plate: Whether plate is calibrated
            abs_grams_diff: Absolute grams difference

        Returns:
            Confidence (0.0 to 1.0)
        """
        # Start with base confidence
        confidence = 0.7

        # Adjust for area difference magnitude
        if abs_area_ratio < 0.1:
            confidence += 0.2  # Small difference → more confident
        elif abs_area_ratio > 0.5:
            confidence -= 0.2  # Large difference → less confident

        # Adjust for calibrated plate
        if has_calibrated_plate:
            confidence += 0.15
        else:
            confidence -= 0.1

        # Adjust for extreme estimates
        if abs_grams_diff > 200:
            confidence -= 0.15  # Very large difference → less confident

        # Clamp to valid range
        return max(0.0, min(1.0, confidence))


# Global service instance
_portion_comparison_service: Optional[PortionComparisonService] = None


def get_portion_comparison_service() -> PortionComparisonService:
    """Get or create the global portion comparison service instance"""
    global _portion_comparison_service

    if _portion_comparison_service is None:
        _portion_comparison_service = PortionComparisonService()

    return _portion_comparison_service
