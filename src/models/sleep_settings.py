"""Pydantic models for sleep quiz settings and patterns"""
from pydantic import BaseModel, Field
from datetime import datetime, time
from typing import Optional


class SleepQuizSettings(BaseModel):
    """User settings for automated sleep quiz"""

    user_id: str
    enabled: bool = True
    preferred_time: time = Field(default=time(7, 0))  # 7:00 AM
    timezone: str = "UTC"
    language_code: str = "en"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class SleepQuizSubmission(BaseModel):
    """Record of when user submitted quiz vs scheduled time"""

    id: str
    user_id: str
    scheduled_time: datetime
    submitted_at: datetime
    response_delay_minutes: int  # submitted_at - scheduled_time in minutes
    created_at: datetime = Field(default_factory=datetime.now)


class SubmissionPattern(BaseModel):
    """Analyzed pattern of user's submission behavior"""

    user_id: str
    average_delay_minutes: float
    suggested_time: time
    confidence_score: float = Field(ge=0.0, le=1.0)  # 0.0-1.0
    sample_size: int  # Number of submissions analyzed
