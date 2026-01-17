"""
Plate Calibration Utilities

Utilities for calibrating plate sizes and estimating portions from calibrated plates.
Epic 009 - Phase 2: Plate Recognition & Calibration
"""
import logging
import math
from typing import Optional, Tuple
from src.models.plate import CalibrationInput, CalibrationResult, PortionEstimate

logger = logging.getLogger(__name__)


class PlateCalibrationError(Exception):
    """Raised when plate calibration fails"""
    pass


def calibrate_from_reference_portion(
    portion_grams: float,
    fill_percentage: float
) -> float:
    """
    Calculate total capacity from a known portion

    Given a known portion weight and how much of the container it fills,
    estimate the total capacity.

    Args:
        portion_grams: Weight of food in grams
        fill_percentage: How full the container is (0.0 to 1.0)
                        Example: 0.5 = 50% full

    Returns:
        Estimated total capacity in grams

    Example:
        >>> calibrate_from_reference_portion(170.0, 0.5)
        340.0  # 170g fills 50% → total capacity = 340g

    Raises:
        PlateCalibrationError: If inputs are invalid
    """
    if portion_grams <= 0:
        raise PlateCalibrationError(
            f"portion_grams must be positive, got {portion_grams}"
        )

    if not 0.0 < fill_percentage <= 1.0:
        raise PlateCalibrationError(
            f"fill_percentage must be between 0.0 and 1.0, got {fill_percentage}"
        )

    # Calculate total capacity
    total_capacity = portion_grams / fill_percentage

    logger.info(
        f"Calibrated capacity: {portion_grams}g fills {fill_percentage*100}% "
        f"→ total capacity {total_capacity:.1f}g"
    )

    return total_capacity


def estimate_portion_from_capacity(
    total_capacity_ml: float,
    fill_percentage: float,
    density_g_per_ml: float = 1.0
) -> float:
    """
    Estimate portion size from calibrated capacity

    Args:
        total_capacity_ml: Total capacity of container in milliliters
        fill_percentage: How full the container is (0.0 to 1.0)
        density_g_per_ml: Density of food (default 1.0 for water-like foods)
                         Common: 1.0 (yogurt, soup), 0.6 (salad), 1.05 (cottage cheese)

    Returns:
        Estimated portion weight in grams

    Example:
        >>> estimate_portion_from_capacity(340.0, 0.5)
        170.0  # 340ml bowl, 50% full → 170g
    """
    if total_capacity_ml <= 0:
        raise PlateCalibrationError(
            f"total_capacity_ml must be positive, got {total_capacity_ml}"
        )

    if not 0.0 < fill_percentage <= 1.0:
        raise PlateCalibrationError(
            f"fill_percentage must be between 0.0 and 1.0, got {fill_percentage}"
        )

    if density_g_per_ml <= 0:
        raise PlateCalibrationError(
            f"density_g_per_ml must be positive, got {density_g_per_ml}"
        )

    # Calculate portion weight
    volume_ml = total_capacity_ml * fill_percentage
    weight_grams = volume_ml * density_g_per_ml

    logger.debug(
        f"Portion estimate: {total_capacity_ml}ml capacity × {fill_percentage*100}% "
        f"× {density_g_per_ml} g/ml = {weight_grams:.1f}g"
    )

    return weight_grams


def estimate_diameter_from_capacity(
    capacity_ml: float,
    container_type: str = "bowl"
) -> Optional[float]:
    """
    Estimate diameter from capacity for round containers

    Uses geometric formulas for common container shapes.

    Args:
        capacity_ml: Total capacity in milliliters
        container_type: Type of container ("bowl", "cup", "plate")

    Returns:
        Estimated diameter in centimeters, or None if not applicable

    Note:
        This is a rough estimate based on typical proportions.
        Real containers vary significantly.
    """
    if capacity_ml <= 0:
        return None

    # Typical depth-to-diameter ratios for common containers
    depth_ratio = {
        "bowl": 0.4,     # Bowls are typically wider than deep
        "cup": 1.0,      # Cups are typically as tall as wide
        "plate": 0.1,    # Plates are shallow
    }

    ratio = depth_ratio.get(container_type, 0.5)

    # For a cylinder: V = π * r² * h
    # For a hemisphere bowl: V ≈ (2/3) * π * r³
    # We'll use cylinder as approximation

    # Assuming h = ratio * d (where d = 2r)
    # V = π * r² * (ratio * 2r) = 2 * π * ratio * r³
    # Solve for r: r³ = V / (2 * π * ratio)

    volume_cm3 = capacity_ml  # 1 ml = 1 cm³

    try:
        radius_cubed = volume_cm3 / (2 * math.pi * ratio)
        radius_cm = radius_cubed ** (1/3)
        diameter_cm = 2 * radius_cm

        logger.debug(
            f"Estimated diameter for {container_type} with {capacity_ml}ml: "
            f"{diameter_cm:.1f}cm"
        )

        return diameter_cm

    except Exception as e:
        logger.warning(f"Failed to estimate diameter: {e}")
        return None


def estimate_capacity_from_diameter(
    diameter_cm: float,
    container_type: str = "bowl"
) -> Optional[float]:
    """
    Estimate capacity from diameter for round containers

    Reverse of estimate_diameter_from_capacity.

    Args:
        diameter_cm: Diameter in centimeters
        container_type: Type of container ("bowl", "cup", "plate")

    Returns:
        Estimated capacity in milliliters, or None if not applicable
    """
    if diameter_cm <= 0:
        return None

    # Typical depth-to-diameter ratios
    depth_ratio = {
        "bowl": 0.4,
        "cup": 1.0,
        "plate": 0.1,
    }

    ratio = depth_ratio.get(container_type, 0.5)

    radius_cm = diameter_cm / 2

    # V = 2 * π * ratio * r³
    volume_cm3 = 2 * math.pi * ratio * (radius_cm ** 3)

    logger.debug(
        f"Estimated capacity for {container_type} with {diameter_cm}cm diameter: "
        f"{volume_cm3:.1f}ml"
    )

    return volume_cm3


def infer_fill_percentage_from_vision_description(
    description: str
) -> Tuple[float, float]:
    """
    Infer fill percentage from vision AI description

    Parses common phrases to estimate how full a container is.

    Args:
        description: Text description from vision AI

    Returns:
        Tuple of (fill_percentage, confidence)

    Example:
        >>> infer_fill_percentage_from_vision_description("bowl is half full")
        (0.5, 0.8)
    """
    description_lower = description.lower()

    # Common fill level phrases
    patterns = {
        "empty": (0.05, 0.9),
        "nearly empty": (0.1, 0.7),
        "quarter full": (0.25, 0.8),
        "one quarter": (0.25, 0.8),
        "1/4 full": (0.25, 0.8),
        "half full": (0.5, 0.9),
        "halfway": (0.5, 0.9),
        "1/2 full": (0.5, 0.9),
        "three quarters": (0.75, 0.8),
        "3/4 full": (0.75, 0.8),
        "mostly full": (0.85, 0.7),
        "nearly full": (0.9, 0.7),
        "full": (1.0, 0.9),
        "heaping": (1.2, 0.6),  # Over-filled
        "overflowing": (1.3, 0.6),
    }

    for pattern, (percentage, confidence) in patterns.items():
        if pattern in description_lower:
            logger.info(
                f"Inferred fill percentage {percentage*100}% "
                f"(confidence {confidence}) from: '{pattern}'"
            )
            return (percentage, confidence)

    # Default: assume moderately full if no specific mention
    logger.debug(
        f"Could not infer fill percentage from description, "
        f"using default 0.5 with low confidence"
    )
    return (0.5, 0.3)


def validate_calibration_result(
    result: CalibrationResult,
    container_type: str
) -> Tuple[bool, str]:
    """
    Validate calibration result for reasonableness

    Checks if estimated dimensions are within reasonable bounds.

    Args:
        result: Calibration result to validate
        container_type: Type of container

    Returns:
        Tuple of (is_valid, message)
    """
    # Reasonable bounds for common containers
    diameter_bounds = {
        "plate": (15.0, 35.0),   # Dinner plates: 15-35cm
        "bowl": (10.0, 30.0),    # Bowls: 10-30cm
        "cup": (6.0, 12.0),      # Cups: 6-12cm
        "container": (5.0, 40.0) # Generic: wider range
    }

    capacity_bounds = {
        "plate": (None, None),       # Plates don't have meaningful capacity
        "bowl": (200.0, 2000.0),     # Bowls: 200ml - 2L
        "cup": (150.0, 600.0),       # Cups: 150-600ml
        "container": (100.0, 5000.0) # Containers: 100ml - 5L
    }

    # Check diameter
    if result.estimated_diameter_cm is not None:
        min_d, max_d = diameter_bounds.get(container_type, (5.0, 50.0))
        if not (min_d <= result.estimated_diameter_cm <= max_d):
            return (
                False,
                f"Diameter {result.estimated_diameter_cm:.1f}cm is outside "
                f"reasonable range [{min_d}-{max_d}cm] for {container_type}"
            )

    # Check capacity
    if result.estimated_capacity_ml is not None:
        bounds = capacity_bounds.get(container_type, (50.0, 10000.0))
        if bounds[0] is not None and bounds[1] is not None:
            min_c, max_c = bounds
            if not (min_c <= result.estimated_capacity_ml <= max_c):
                return (
                    False,
                    f"Capacity {result.estimated_capacity_ml:.1f}ml is outside "
                    f"reasonable range [{min_c}-{max_c}ml] for {container_type}"
                )

    return (True, "Calibration result is within reasonable bounds")


def calculate_confidence_from_method(
    method: str,
    data_quality: str = "good"
) -> float:
    """
    Calculate confidence score based on calibration method and data quality

    Args:
        method: Calibration method (reference_portion, user_input, auto_inferred)
        data_quality: Quality of input data (excellent, good, fair, poor)

    Returns:
        Confidence score (0.0 to 1.0)
    """
    # Base confidence by method
    base_confidence = {
        "reference_portion": 0.8,  # High confidence from actual portions
        "user_input": 0.9,          # Very high confidence from explicit user input
        "auto_inferred": 0.5        # Medium confidence from patterns
    }

    # Quality modifiers
    quality_modifier = {
        "excellent": 1.0,
        "good": 0.9,
        "fair": 0.7,
        "poor": 0.5
    }

    base = base_confidence.get(method, 0.6)
    modifier = quality_modifier.get(data_quality, 0.8)

    confidence = min(1.0, base * modifier)

    logger.debug(
        f"Confidence: {method} ({data_quality} quality) → {confidence:.2f}"
    )

    return confidence


def merge_calibrations(
    existing_capacity: Optional[float],
    new_capacity: float,
    existing_confidence: float,
    new_confidence: float
) -> Tuple[float, float]:
    """
    Merge multiple calibration measurements using weighted average

    Args:
        existing_capacity: Previous capacity estimate (or None)
        new_capacity: New capacity estimate
        existing_confidence: Confidence in existing estimate
        new_confidence: Confidence in new estimate

    Returns:
        Tuple of (merged_capacity, merged_confidence)
    """
    if existing_capacity is None:
        return (new_capacity, new_confidence)

    # Weight by confidence
    total_weight = existing_confidence + new_confidence
    merged_capacity = (
        (existing_capacity * existing_confidence + new_capacity * new_confidence)
        / total_weight
    )

    # Confidence increases with more data (but not linearly)
    merged_confidence = min(
        0.95,  # Cap at 0.95
        (existing_confidence + new_confidence) / 2 + 0.1
    )

    logger.info(
        f"Merged calibrations: {existing_capacity:.1f}ml (conf {existing_confidence:.2f}) "
        f"+ {new_capacity:.1f}ml (conf {new_confidence:.2f}) "
        f"→ {merged_capacity:.1f}ml (conf {merged_confidence:.2f})"
    )

    return (merged_capacity, merged_confidence)
