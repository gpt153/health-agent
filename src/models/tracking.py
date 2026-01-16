"""
Dynamic tracking models with comprehensive field type support.
Supports 8 field types: text, number, rating, boolean, date, time, duration, multiselect, single_select
"""
from typing import Optional, Any, Union, Literal
from datetime import datetime, date, time as time_type
from pydantic import BaseModel, Field, field_validator, model_validator
from uuid import UUID, uuid4
from enum import Enum


class FieldType(str, Enum):
    """Supported field types for custom trackers"""
    TEXT = "text"
    NUMBER = "number"
    RATING = "rating"
    BOOLEAN = "boolean"
    DATE = "date"
    TIME = "time"
    DURATION = "duration"
    MULTISELECT = "multiselect"
    SINGLE_SELECT = "single_select"


# Field Configuration Models
# Each field type has its own config class with specific validation

class TextFieldConfig(BaseModel):
    """Text field configuration"""
    type: Literal[FieldType.TEXT] = FieldType.TEXT
    label: str
    required: bool = True
    description: Optional[str] = None
    max_length: Optional[int] = None


class NumberFieldConfig(BaseModel):
    """Number field configuration"""
    type: Literal[FieldType.NUMBER] = FieldType.NUMBER
    label: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: Optional[str] = None  # e.g., "ml", "kg", "mg"
    required: bool = True
    description: Optional[str] = None

    @model_validator(mode='after')
    def validate_range(self):
        if self.min_value is not None and self.max_value is not None:
            if self.min_value > self.max_value:
                raise ValueError("min_value must be <= max_value")
        return self


class RatingFieldConfig(BaseModel):
    """Rating field configuration (like 1-10 scale)"""
    type: Literal[FieldType.RATING] = FieldType.RATING
    label: str
    min_value: int = 1
    max_value: int = 10
    required: bool = True
    description: Optional[str] = None

    @model_validator(mode='after')
    def validate_range(self):
        if self.min_value >= self.max_value:
            raise ValueError("min_value must be < max_value")
        if self.min_value < 0:
            raise ValueError("min_value must be >= 0")
        return self


class BooleanFieldConfig(BaseModel):
    """Boolean field configuration"""
    type: Literal[FieldType.BOOLEAN] = FieldType.BOOLEAN
    label: str
    required: bool = True
    description: Optional[str] = None


class DateFieldConfig(BaseModel):
    """Date field configuration"""
    type: Literal[FieldType.DATE] = FieldType.DATE
    label: str
    required: bool = True
    description: Optional[str] = None


class TimeFieldConfig(BaseModel):
    """Time field configuration"""
    type: Literal[FieldType.TIME] = FieldType.TIME
    label: str
    required: bool = True
    description: Optional[str] = None


class DurationFieldConfig(BaseModel):
    """Duration field configuration (e.g., '30min', '2h')"""
    type: Literal[FieldType.DURATION] = FieldType.DURATION
    label: str
    required: bool = True
    description: Optional[str] = None


class MultiselectFieldConfig(BaseModel):
    """Multiselect field configuration (user can select multiple options)"""
    type: Literal[FieldType.MULTISELECT] = FieldType.MULTISELECT
    label: str
    options: list[str]
    required: bool = False  # Multiselect often optional
    description: Optional[str] = None

    @field_validator('options')
    @classmethod
    def validate_options(cls, v):
        if not v:
            raise ValueError("options list cannot be empty")
        if len(v) != len(set(v)):
            raise ValueError("options must be unique")
        return v


class SingleSelectFieldConfig(BaseModel):
    """Single select field configuration (user selects one option)"""
    type: Literal[FieldType.SINGLE_SELECT] = FieldType.SINGLE_SELECT
    label: str
    options: list[str]
    required: bool = True
    description: Optional[str] = None

    @field_validator('options')
    @classmethod
    def validate_options(cls, v):
        if not v:
            raise ValueError("options list cannot be empty")
        if len(v) != len(set(v)):
            raise ValueError("options must be unique")
        return v


# Union type for any field config
FieldConfig = Union[
    TextFieldConfig,
    NumberFieldConfig,
    RatingFieldConfig,
    BooleanFieldConfig,
    DateFieldConfig,
    TimeFieldConfig,
    DurationFieldConfig,
    MultiselectFieldConfig,
    SingleSelectFieldConfig
]


class TrackingSchedule(BaseModel):
    """Schedule for prompting user"""
    type: str  # daily, weekly, monthly, custom
    time: str  # "08:00", "21:00"
    days: list[int] = Field(default_factory=lambda: list(range(7)))  # 0=Monday
    message: str

    @field_validator('time')
    @classmethod
    def validate_time_format(cls, v):
        """Validate time is in HH:MM format"""
        try:
            hours, minutes = v.split(':')
            h, m = int(hours), int(minutes)
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
        except (ValueError, AttributeError):
            raise ValueError("time must be in HH:MM format (e.g., '09:00')")
        return v

    @field_validator('days')
    @classmethod
    def validate_days(cls, v):
        """Validate days are 0-6 (Monday-Sunday)"""
        if not all(0 <= day <= 6 for day in v):
            raise ValueError("days must be integers 0-6 (0=Monday, 6=Sunday)")
        return v


class TrackerDefinition(BaseModel):
    """
    Enhanced tracker definition with comprehensive field type support.
    This replaces the old TrackingCategory model with better validation.
    """
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    fields: dict[str, FieldConfig]
    schedule: Optional[TrackingSchedule] = None
    category_type: str = "custom"  # custom, system, template
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)

    @field_validator('fields')
    @classmethod
    def validate_field_definitions(cls, v):
        """Ensure at least one field exists and field names are valid"""
        if not v:
            raise ValueError("Tracker must have at least one field")

        # Validate field names (must be valid Python identifiers)
        for field_name in v.keys():
            if not field_name.isidentifier():
                raise ValueError(
                    f"Invalid field name '{field_name}'. "
                    "Field names must be valid identifiers (letters, numbers, underscores, no spaces)"
                )

        return v

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Ensure tracker name is not empty"""
        if not v or not v.strip():
            raise ValueError("Tracker name cannot be empty")
        return v.strip()

    @field_validator('category_type')
    @classmethod
    def validate_category_type(cls, v):
        """Ensure valid category type"""
        if v not in ('custom', 'system', 'template'):
            raise ValueError("category_type must be 'custom', 'system', or 'template'")
        return v


class TrackerEntry(BaseModel):
    """
    Entry in a tracking category.
    Data is validated against the tracker's field definitions.
    """
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    category_id: UUID
    timestamp: datetime = Field(default_factory=datetime.now)
    data: dict[str, Any]  # Flexible data storage - validated at runtime
    notes: Optional[str] = None
    validation_status: str = "valid"  # valid, warning, error
    validation_errors: Optional[dict[str, str]] = None

    @field_validator('validation_status')
    @classmethod
    def validate_status(cls, v):
        """Ensure valid validation status"""
        if v not in ('valid', 'warning', 'error'):
            raise ValueError("validation_status must be 'valid', 'warning', or 'error'")
        return v


# Legacy compatibility - keep old models but mark as deprecated
class TrackingField(BaseModel):
    """
    DEPRECATED: Use FieldConfig types instead.
    Kept for backward compatibility with existing code.
    """
    type: str  # time, number, text, rating
    label: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    required: bool = True


class TrackingCategory(BaseModel):
    """
    DEPRECATED: Use TrackerDefinition instead.
    Kept for backward compatibility with existing code.
    """
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    name: str
    fields: dict[str, TrackingField]
    schedule: Optional[TrackingSchedule] = None
    active: bool = True
