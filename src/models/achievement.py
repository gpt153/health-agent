"""Achievement models for gamification"""
from enum import Enum
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class AchievementCategory(str, Enum):
    """Achievement categories"""
    CONSISTENCY = "consistency"
    MILESTONES = "milestones"
    RECOVERY = "recovery"
    EXPLORATION = "exploration"


class AchievementTier(str, Enum):
    """Achievement tiers/difficulty levels"""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class Achievement(BaseModel):
    """Achievement definition"""
    id: str
    name: str
    description: str
    icon: str
    category: AchievementCategory
    criteria: dict[str, Any]
    tier: AchievementTier


class UserAchievement(BaseModel):
    """User's unlocked achievement"""
    user_id: str
    achievement_id: str
    unlocked_at: datetime
    metadata: Optional[dict] = None
