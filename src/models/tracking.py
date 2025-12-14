"""Dynamic tracking models"""
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class TrackingField(BaseModel):
    """Field definition for tracking category"""
    type: str  # time, number, text, rating
    label: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    required: bool = True


class TrackingSchedule(BaseModel):
    """Schedule for prompting user"""
    type: str  # daily, weekly, monthly, custom
    time: str  # "08:00", "21:00"
    days: list[int] = Field(default_factory=lambda: list(range(7)))  # 0=Monday
    message: str


class TrackingCategory(BaseModel):
    """User-defined tracking category"""
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    name: str
    fields: dict[str, TrackingField]
    schedule: Optional[TrackingSchedule] = None
    active: bool = True


class TrackingEntry(BaseModel):
    """Entry in a tracking category"""
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    category_id: UUID
    timestamp: datetime = Field(default_factory=datetime.now)
    data: dict[str, Any]  # Flexible data storage
    notes: Optional[str] = None
