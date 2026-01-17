"""
Plate Recognition Data Models

Models for plate/container detection, recognition, and calibration.
Epic 009 - Phase 2: Plate Recognition & Calibration
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class PlateMetadata(BaseModel):
    """Metadata extracted from plate detection"""

    plate_type: str = Field(
        ...,
        description="Type of container: plate, bowl, cup, container"
    )
    color: Optional[str] = Field(
        None,
        description="Dominant color or pattern (e.g., 'white', 'blue ceramic', 'floral pattern')"
    )
    shape: Optional[str] = Field(
        None,
        description="Shape: round, square, oval, rectangular"
    )
    estimated_diameter_cm: Optional[float] = Field(
        None,
        ge=5.0,
        le=50.0,
        description="Estimated diameter in centimeters (5-50cm range)"
    )
    estimated_capacity_ml: Optional[float] = Field(
        None,
        ge=50.0,
        le=5000.0,
        description="Estimated capacity in milliliters (50-5000ml range)"
    )

    @field_validator('plate_type')
    @classmethod
    def validate_plate_type(cls, v: str) -> str:
        """Validate plate type is one of allowed values"""
        allowed_types = {"plate", "bowl", "cup", "container"}
        if v.lower() not in allowed_types:
            raise ValueError(f"plate_type must be one of {allowed_types}")
        return v.lower()

    @field_validator('shape')
    @classmethod
    def validate_shape(cls, v: Optional[str]) -> Optional[str]:
        """Validate shape is one of allowed values"""
        if v is None:
            return None
        allowed_shapes = {"round", "square", "oval", "rectangular"}
        if v.lower() not in allowed_shapes:
            raise ValueError(f"shape must be one of {allowed_shapes}")
        return v.lower()


class PlateRegion(BaseModel):
    """Bounding box or region information for detected plate"""

    x: float = Field(..., ge=0.0, le=1.0, description="X coordinate (normalized 0-1)")
    y: float = Field(..., ge=0.0, le=1.0, description="Y coordinate (normalized 0-1)")
    width: float = Field(..., ge=0.0, le=1.0, description="Width (normalized 0-1)")
    height: float = Field(..., ge=0.0, le=1.0, description="Height (normalized 0-1)")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage"""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height
        }


class DetectedPlate(BaseModel):
    """Plate detected from an image"""

    embedding: list[float] = Field(
        ...,
        min_length=512,
        max_length=512,
        description="512-dimensional CLIP embedding"
    )
    metadata: PlateMetadata = Field(..., description="Plate characteristics")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Detection confidence (0.0 to 1.0)"
    )
    region: Optional[PlateRegion] = Field(
        None,
        description="Bounding box or segmentation region"
    )

    @field_validator('embedding')
    @classmethod
    def validate_embedding_dimension(cls, v: list[float]) -> list[float]:
        """Validate embedding is exactly 512 dimensions"""
        if len(v) != 512:
            raise ValueError(f"Embedding must be 512 dimensions, got {len(v)}")
        return v


class RecognizedPlate(BaseModel):
    """Plate from database with full history"""

    id: str = Field(..., description="UUID of the recognized plate")
    user_id: str = Field(..., description="Telegram user ID")
    plate_name: str = Field(..., description="Human-readable plate name")
    embedding: list[float] = Field(
        ...,
        min_length=512,
        max_length=512,
        description="512-dimensional CLIP embedding"
    )

    # Physical characteristics
    plate_type: str = Field(..., description="Type: plate, bowl, cup, container")
    color: Optional[str] = None
    shape: Optional[str] = None
    estimated_diameter_cm: Optional[float] = Field(None, ge=0.0)
    estimated_capacity_ml: Optional[float] = Field(None, ge=0.0)

    # Usage tracking
    times_recognized: int = Field(..., ge=1, description="Number of times detected")
    first_seen_at: datetime
    last_seen_at: datetime

    # Calibration
    is_calibrated: bool = Field(
        default=False,
        description="Whether plate has been calibrated with accurate dimensions"
    )
    calibration_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    calibration_method: Optional[str] = None

    # Metadata
    model_version: str = Field(default="clip-vit-base-patch32")
    created_at: datetime
    updated_at: datetime

    @property
    def metadata(self) -> PlateMetadata:
        """Convert to PlateMetadata for compatibility"""
        return PlateMetadata(
            plate_type=self.plate_type,
            color=self.color,
            shape=self.shape,
            estimated_diameter_cm=self.estimated_diameter_cm,
            estimated_capacity_ml=self.estimated_capacity_ml
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "plate_name": self.plate_name,
            "plate_type": self.plate_type,
            "color": self.color,
            "shape": self.shape,
            "estimated_diameter_cm": self.estimated_diameter_cm,
            "estimated_capacity_ml": self.estimated_capacity_ml,
            "times_recognized": self.times_recognized,
            "is_calibrated": self.is_calibrated,
            "calibration_confidence": self.calibration_confidence,
            "calibration_method": self.calibration_method,
            "first_seen_at": self.first_seen_at.isoformat(),
            "last_seen_at": self.last_seen_at.isoformat()
        }


class CalibrationInput(BaseModel):
    """Input for plate calibration"""

    plate_id: str = Field(..., description="UUID of plate to calibrate")
    method: str = Field(..., description="Calibration method: reference_portion, user_input, auto_inferred")

    # For reference_portion method
    reference_portion_grams: Optional[float] = Field(None, gt=0.0)
    visual_fill_percentage: Optional[float] = Field(None, gt=0.0, le=1.0)

    # For user_input method
    user_provided_diameter_cm: Optional[float] = Field(None, gt=0.0)
    user_provided_capacity_ml: Optional[float] = Field(None, gt=0.0)

    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence in calibration (0.0 to 1.0)"
    )

    @field_validator('method')
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate calibration method"""
        allowed_methods = {"reference_portion", "user_input", "auto_inferred"}
        if v not in allowed_methods:
            raise ValueError(f"method must be one of {allowed_methods}")
        return v

    def validate_inputs(self) -> None:
        """Validate that required inputs are provided for the chosen method"""
        if self.method == "reference_portion":
            if self.reference_portion_grams is None or self.visual_fill_percentage is None:
                raise ValueError(
                    "reference_portion method requires reference_portion_grams and visual_fill_percentage"
                )
        elif self.method == "user_input":
            if self.user_provided_diameter_cm is None and self.user_provided_capacity_ml is None:
                raise ValueError(
                    "user_input method requires either user_provided_diameter_cm or user_provided_capacity_ml"
                )


class CalibrationResult(BaseModel):
    """Result of plate calibration"""

    plate_id: str = Field(..., description="UUID of calibrated plate")
    calibration_method: str
    estimated_capacity_ml: Optional[float] = Field(None, gt=0.0)
    estimated_diameter_cm: Optional[float] = Field(None, gt=0.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    success: bool
    message: str = Field(..., description="Human-readable result message")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "plate_id": self.plate_id,
            "calibration_method": self.calibration_method,
            "estimated_capacity_ml": self.estimated_capacity_ml,
            "estimated_diameter_cm": self.estimated_diameter_cm,
            "confidence": self.confidence,
            "success": self.success,
            "message": self.message
        }


class PortionEstimate(BaseModel):
    """Portion size estimate based on plate calibration"""

    estimated_grams: float = Field(..., gt=0.0, description="Estimated portion weight in grams")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in estimate")
    method: str = Field(
        ...,
        description="Estimation method: calibrated_plate, visual_estimation, hybrid"
    )
    plate_id: Optional[str] = Field(None, description="UUID of plate used for estimation")
    notes: Optional[str] = Field(None, description="Additional notes about estimation")

    @field_validator('method')
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate estimation method"""
        allowed_methods = {"calibrated_plate", "visual_estimation", "hybrid"}
        if v not in allowed_methods:
            raise ValueError(f"method must be one of {allowed_methods}")
        return v

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "estimated_grams": round(self.estimated_grams, 1),
            "confidence": round(self.confidence, 2),
            "method": self.method,
            "plate_id": self.plate_id,
            "notes": self.notes
        }


class FoodEntryPlateLink(BaseModel):
    """Link between a food entry and a recognized plate"""

    id: str = Field(..., description="UUID of the link")
    food_entry_id: str = Field(..., description="UUID of the food entry")
    recognized_plate_id: str = Field(..., description="UUID of the recognized plate")
    user_id: str = Field(..., description="Telegram user ID")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Matching confidence")
    detection_method: str = Field(
        default="auto_detected",
        description="How the plate was linked: auto_detected, user_confirmed, manual_link"
    )
    plate_region: Optional[dict] = Field(None, description="Bounding box or region data")
    created_at: datetime

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "food_entry_id": self.food_entry_id,
            "recognized_plate_id": self.recognized_plate_id,
            "user_id": self.user_id,
            "confidence_score": round(self.confidence_score, 3),
            "detection_method": self.detection_method,
            "plate_region": self.plate_region,
            "created_at": self.created_at.isoformat()
        }


class PlateStatistics(BaseModel):
    """Summary statistics for a user's plate collection"""

    total_plates: int = Field(..., ge=0)
    calibrated_plates: int = Field(..., ge=0)
    total_recognitions: int = Field(..., ge=0)
    most_used_plate_id: Optional[str] = None
    most_used_plate_name: Optional[str] = None
    most_used_count: Optional[int] = Field(None, ge=0)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "total_plates": self.total_plates,
            "calibrated_plates": self.calibrated_plates,
            "total_recognitions": self.total_recognitions,
            "most_used_plate": {
                "id": self.most_used_plate_id,
                "name": self.most_used_plate_name,
                "count": self.most_used_count
            } if self.most_used_plate_id else None
        }
