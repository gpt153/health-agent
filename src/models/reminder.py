"""Reminder models"""
from typing import Optional
from datetime import time as dt_time, date
from pydantic import BaseModel, Field, field_validator
from uuid import UUID, uuid4
import pytz


class ReminderSchedule(BaseModel):
    """Reminder schedule configuration with validation"""
    type: str  # daily, weekly, once
    time: str  # "21:00"
    timezone: str = "UTC"  # IANA timezone (e.g., "Europe/Stockholm")
    days: list[int] = Field(default_factory=lambda: list(range(7)))  # 0-6
    date: Optional[str] = None  # YYYY-MM-DD format (required for type="once")

    @field_validator('time')
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Ensure HH:MM format and valid time"""
        try:
            dt_time.fromisoformat(v)
        except ValueError:
            raise ValueError(
                f"Invalid time format: '{v}'. Must be HH:MM (e.g., '21:00')"
            )
        return v

    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Ensure valid IANA timezone"""
        try:
            pytz.timezone(v)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(
                f"Invalid timezone: '{v}'. "
                f"Use IANA timezone (e.g., 'Europe/Stockholm', 'America/New_York')"
            )
        return v

    @field_validator('days')
    @classmethod
    def validate_days(cls, v: list[int]) -> list[int]:
        """Ensure days are 0-6 (Monday-Sunday)"""
        for day in v:
            if day < 0 or day > 6:
                raise ValueError(
                    f"Invalid day: {day}. Days must be 0-6 (Monday=0, Sunday=6)"
                )
        return v

    @field_validator('date')
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        """Ensure YYYY-MM-DD format if provided"""
        if v is not None:
            try:
                date.fromisoformat(v)
            except ValueError:
                raise ValueError(
                    f"Invalid date format: '{v}'. Must be YYYY-MM-DD"
                )
        return v

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Ensure valid reminder type"""
        valid_types = ['daily', 'weekly', 'once']
        if v not in valid_types:
            raise ValueError(
                f"Invalid reminder type: '{v}'. Must be one of: {', '.join(valid_types)}"
            )
        return v


class Reminder(BaseModel):
    """Reminder configuration with validation"""
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    reminder_type: str  # simple, tracking_prompt
    message: str = Field(min_length=1, max_length=4000, description="Reminder message")
    schedule: ReminderSchedule
    active: bool = True
    tracking_category_id: Optional[UUID] = None  # If tracking_prompt type
    enable_completion_tracking: bool = True  # Whether to show Done button and track completions
    streak_motivation: bool = True  # Whether to show streak count in notifications
    check_condition: Optional[dict] = None  # Conditional logic for smart reminders (skip if condition met)

    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate reminder message"""
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Reminder message cannot be empty or only whitespace")
        return trimmed

    @field_validator('reminder_type')
    @classmethod
    def validate_reminder_type(cls, v: str) -> str:
        """Ensure valid reminder type"""
        valid_types = ['simple', 'tracking_prompt']
        if v not in valid_types:
            raise ValueError(
                f"Invalid reminder type: '{v}'. Must be one of: {', '.join(valid_types)}"
            )
        return v
