"""User-related Pydantic models"""
from typing import Optional
from pydantic import BaseModel, Field


class UserPreferences(BaseModel):
    """User preference settings"""
    brevity: str = "medium"  # brief, medium, detailed
    tone: str = "friendly"  # friendly, formal, casual
    humor: bool = True
    coaching_style: str = "supportive"  # supportive, analytical, tough_love
    wants_daily_summary: bool = False
    wants_proactive_checkins: bool = False
    timezone: str = "UTC"  # IANA timezone (e.g., "America/New_York", "Europe/London")


class UserProfile(BaseModel):
    """User profile information"""
    telegram_id: str
    name: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    current_weight_kg: Optional[float] = None
    target_weight_kg: Optional[float] = None
    goal_type: Optional[str] = None  # lose_weight, gain_muscle, maintain
    preferences: UserPreferences = Field(default_factory=UserPreferences)


class UserMemory(BaseModel):
    """Complete user memory (from markdown files)"""
    telegram_id: str
    profile: dict  # Parsed from profile.md
    preferences: dict  # Parsed from preferences.md
    patterns: dict  # Parsed from patterns.md
    recent_foods: list  # Parsed from food_history.md
