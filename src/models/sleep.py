"""Pydantic models for sleep tracking"""
from pydantic import BaseModel, Field
from datetime import datetime, time
from typing import Optional, List


class SleepEntry(BaseModel):
    """Sleep entry model for quiz data"""

    id: str
    user_id: str
    logged_at: datetime
    bedtime: time
    sleep_latency_minutes: int = Field(ge=0, le=300)  # 0-5 hours max
    wake_time: time
    total_sleep_hours: float = Field(ge=0, le=24)
    night_wakings: int = Field(ge=0, le=20)
    sleep_quality_rating: int = Field(ge=1, le=10)
    disruptions: List[str] = Field(default_factory=list)
    phone_usage: bool
    phone_duration_minutes: Optional[int] = Field(None, ge=0, le=480)  # 0-8 hours max
    alertness_rating: int = Field(ge=1, le=10)
