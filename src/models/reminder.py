"""Reminder models"""
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class ReminderSchedule(BaseModel):
    """Reminder schedule configuration"""
    type: str  # daily, weekly, once
    time: str  # "21:00"
    timezone: str = "UTC"  # IANA timezone (e.g., "Europe/Stockholm")
    days: list[int] = Field(default_factory=lambda: list(range(7)))  # 0-6
    date: Optional[str] = None  # YYYY-MM-DD format (required for type="once")


class Reminder(BaseModel):
    """Reminder configuration"""
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    reminder_type: str  # simple, tracking_prompt
    message: str
    schedule: ReminderSchedule
    active: bool = True
    tracking_category_id: Optional[UUID] = None  # If tracking_prompt type
    enable_completion_tracking: bool = True  # Whether to show Done button and track completions
    streak_motivation: bool = True  # Whether to show streak count in notifications
