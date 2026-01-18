"""
Portion Comparison Data Models

Models for portion comparison, bounding box detection, and accuracy tracking.
Epic 009 - Phase 4: Portion Comparison
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class BoundingBox(BaseModel):
    """Bounding box for a detected food item (normalized 0-1 coordinates)"""

    x: float = Field(ge=0.0, le=1.0, description="X coordinate (normalized 0-1)")
    y: float = Field(ge=0.0, le=1.0, description="Y coordinate (normalized 0-1)")
    width: float = Field(ge=0.0, le=1.0, description="Width (normalized 0-1)")
    height: float = Field(ge=0.0, le=1.0, description="Height (normalized 0-1)")

    @property
    def area(self) -> float:
        """Calculate normalized area of bounding box"""
        return self.width * self.height

    @property
    def center_x(self) -> float:
        """Get X coordinate of center"""
        return self.x + (self.width / 2)

    @property
    def center_y(self) -> float:
        """Get Y coordinate of center"""
        return self.y + (self.height / 2)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage"""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BoundingBox":
        """Create from dictionary"""
        return cls(
            x=data["x"],
            y=data["y"],
            width=data["width"],
            height=data["height"]
        )


class FoodItemDetection(BaseModel):
    """Detected food item in an image with bounding box"""

    id: str = Field(..., description="UUID of the detection")
    food_entry_id: str = Field(..., description="UUID of the food entry")
    user_id: str = Field(..., description="Telegram user ID")
    photo_path: str = Field(..., description="Path to the food photo")

    # Food item details
    item_name: str = Field(..., description="Name of detected food item")

    # Bounding box
    bbox: BoundingBox = Field(..., description="Bounding box coordinates")
    pixel_area: float = Field(..., ge=0.0, description="Calculated pixel area")

    # Detection metadata
    detection_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Detection confidence (0-1)"
    )
    detection_method: str = Field(
        default="vision_ai",
        description="Detection method: vision_ai, manual, heuristic"
    )

    created_at: datetime = Field(default_factory=datetime.now)

    @field_validator('detection_method')
    @classmethod
    def validate_detection_method(cls, v: str) -> str:
        """Validate detection method is one of allowed values"""
        allowed_methods = {"vision_ai", "manual", "heuristic"}
        if v not in allowed_methods:
            raise ValueError(f"detection_method must be one of {allowed_methods}")
        return v

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "food_entry_id": self.food_entry_id,
            "user_id": self.user_id,
            "photo_path": self.photo_path,
            "item_name": self.item_name,
            "bbox": self.bbox.to_dict(),
            "pixel_area": self.pixel_area,
            "detection_confidence": round(self.detection_confidence, 3),
            "detection_method": self.detection_method,
            "created_at": self.created_at.isoformat()
        }


class PortionComparison(BaseModel):
    """Comparison between current and reference food portions"""

    id: str = Field(..., description="UUID of the comparison")
    user_id: str = Field(..., description="Telegram user ID")
    current_food_entry_id: str = Field(..., description="UUID of current food entry")
    reference_food_entry_id: str = Field(..., description="UUID of reference food entry")

    # Food item being compared
    item_name: str = Field(..., description="Name of food item")

    # Area measurements
    current_area: float = Field(..., ge=0.0, description="Current portion area")
    reference_area: float = Field(..., ge=0.0, description="Reference portion area")
    area_difference_ratio: float = Field(
        ..., description="Area difference ratio: (current - ref) / ref"
    )

    # Portion estimates
    estimated_grams_difference: Optional[float] = Field(
        None, description="Estimated weight difference in grams (can be negative)"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in estimate (0-1)"
    )

    # Context used for Vision AI
    comparison_context: Optional[str] = Field(
        None, description="Natural language comparison context"
    )

    # Optional plate reference
    plate_id: Optional[str] = Field(None, description="UUID of recognized plate")

    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def percentage_difference(self) -> float:
        """Convert ratio to percentage (e.g., 0.3 -> 30.0%)"""
        return self.area_difference_ratio * 100

    @property
    def is_larger(self) -> bool:
        """Is current portion larger than reference?"""
        return self.area_difference_ratio > 0

    @property
    def is_smaller(self) -> bool:
        """Is current portion smaller than reference?"""
        return self.area_difference_ratio < 0

    @property
    def is_similar(self, threshold: float = 0.05) -> bool:
        """Is current portion similar to reference? (within threshold)"""
        return abs(self.area_difference_ratio) <= threshold

    def get_human_readable_difference(self) -> str:
        """Get human-readable difference description"""
        pct = abs(self.percentage_difference)

        if self.is_similar():
            return f"Similar portion (~{pct:.0f}% difference)"
        elif self.is_larger:
            return f"Larger portion (+{pct:.0f}%)"
        else:
            return f"Smaller portion (-{pct:.0f}%)"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "current_food_entry_id": self.current_food_entry_id,
            "reference_food_entry_id": self.reference_food_entry_id,
            "item_name": self.item_name,
            "current_area": self.current_area,
            "reference_area": self.reference_area,
            "area_difference_ratio": round(self.area_difference_ratio, 3),
            "percentage_difference": round(self.percentage_difference, 1),
            "estimated_grams_difference": self.estimated_grams_difference,
            "confidence": round(self.confidence, 2),
            "comparison_context": self.comparison_context,
            "plate_id": self.plate_id,
            "created_at": self.created_at.isoformat()
        }


class PortionEstimateAccuracy(BaseModel):
    """Accuracy tracking for portion estimates (for learning)"""

    id: str = Field(..., description="UUID of the accuracy record")
    user_id: str = Field(..., description="Telegram user ID")
    portion_comparison_id: str = Field(..., description="UUID of the portion comparison")

    # Estimate vs reality
    estimated_grams: float = Field(..., description="What we estimated")
    user_confirmed_grams: float = Field(..., description="What user confirmed")
    variance_percentage: float = Field(
        ..., ge=0.0, description="Percentage variance from actual"
    )

    # Learning data
    plate_id: Optional[str] = Field(None, description="UUID of plate used")
    food_item_type: str = Field(..., description="Type of food")
    visual_fill_percentage: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="How full the container was"
    )

    # Optional context for learning
    camera_angle_notes: Optional[str] = None
    lighting_notes: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def is_within_target(self) -> bool:
        """Is estimate within ±20% target accuracy?"""
        return self.variance_percentage <= 20.0

    @property
    def is_within_excellent(self) -> bool:
        """Is estimate within ±10% (excellent accuracy)?"""
        return self.variance_percentage <= 10.0

    @property
    def accuracy_grade(self) -> str:
        """Get accuracy grade: excellent, good, fair, poor"""
        if self.variance_percentage <= 10:
            return "excellent"
        elif self.variance_percentage <= 20:
            return "good"
        elif self.variance_percentage <= 30:
            return "fair"
        else:
            return "poor"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "portion_comparison_id": self.portion_comparison_id,
            "estimated_grams": self.estimated_grams,
            "user_confirmed_grams": self.user_confirmed_grams,
            "variance_percentage": round(self.variance_percentage, 1),
            "is_within_target": self.is_within_target,
            "accuracy_grade": self.accuracy_grade,
            "plate_id": self.plate_id,
            "food_item_type": self.food_item_type,
            "visual_fill_percentage": self.visual_fill_percentage,
            "created_at": self.created_at.isoformat()
        }


class ComparisonContext(BaseModel):
    """Context to enhance Vision AI prompts with portion comparison data"""

    # Reference information
    reference_image_path: Optional[str] = Field(
        None, description="Path to reference image"
    )
    reference_date: Optional[datetime] = Field(
        None, description="When reference image was taken"
    )

    # Portion differences (natural language)
    portion_differences: list[str] = Field(
        default_factory=list,
        description="List of differences: ['More rice (+30g)', 'Less chicken (-50g)']"
    )

    # Plate information
    plate_info: Optional[str] = Field(
        None, description="Plate context: 'Using your blue plate #1 (calibrated)'"
    )

    # Confidence notes
    confidence_notes: str = Field(
        ..., description="Confidence level explanation"
    )

    # Overall comparison summary
    summary: Optional[str] = Field(
        None, description="Overall comparison summary"
    )

    def to_prompt_text(self) -> str:
        """
        Convert to natural language prompt text for Vision AI

        Returns formatted text suitable for including in Vision AI prompts.
        """
        parts = []

        if self.summary:
            parts.append(f"PORTION COMPARISON:\n{self.summary}\n")

        if self.portion_differences:
            parts.append("DETECTED DIFFERENCES:")
            for diff in self.portion_differences:
                parts.append(f"  • {diff}")
            parts.append("")

        if self.plate_info:
            parts.append(f"PLATE: {self.plate_info}\n")

        if self.reference_date:
            time_ago = self._format_time_ago(self.reference_date)
            parts.append(f"REFERENCE: Photo from {time_ago}\n")

        parts.append(f"CONFIDENCE: {self.confidence_notes}")

        return "\n".join(parts)

    def _format_time_ago(self, dt: datetime) -> str:
        """Format datetime as 'X days ago' or 'yesterday' etc."""
        from datetime import datetime, timedelta

        now = datetime.now()
        delta = now - dt

        if delta.days == 0:
            return "today"
        elif delta.days == 1:
            return "yesterday"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        elif delta.days < 30:
            weeks = delta.days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        else:
            months = delta.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "reference_image_path": self.reference_image_path,
            "reference_date": self.reference_date.isoformat() if self.reference_date else None,
            "portion_differences": self.portion_differences,
            "plate_info": self.plate_info,
            "confidence_notes": self.confidence_notes,
            "summary": self.summary
        }


class PortionAccuracyStats(BaseModel):
    """Summary statistics for portion estimate accuracy"""

    total_estimates: int = Field(..., ge=0)
    avg_variance_percentage: float = Field(..., ge=0.0)
    within_20_percent: int = Field(..., ge=0)
    within_10_percent: int = Field(..., ge=0)
    accuracy_rate: float = Field(..., ge=0.0, le=100.0)

    @property
    def excellent_rate(self) -> float:
        """Percentage of estimates within ±10%"""
        if self.total_estimates == 0:
            return 0.0
        return (self.within_10_percent / self.total_estimates) * 100

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "total_estimates": self.total_estimates,
            "avg_variance_percentage": round(self.avg_variance_percentage, 1),
            "within_20_percent": self.within_20_percent,
            "within_10_percent": self.within_10_percent,
            "accuracy_rate": round(self.accuracy_rate, 1),
            "excellent_rate": round(self.excellent_rate, 1)
        }
