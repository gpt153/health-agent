"""Onboarding state models"""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class OnboardingState(BaseModel):
    """User's current onboarding state"""

    user_id: str
    onboarding_path: Optional[Literal["quick", "full", "chat"]] = None
    current_step: str = "welcome"
    step_data: dict = Field(default_factory=dict)
    completed_steps: List[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_interaction_at: Optional[datetime] = None

    @property
    def is_complete(self) -> bool:
        """Check if onboarding is complete"""
        return self.completed_at is not None or self.current_step == "completed"

    @property
    def is_active(self) -> bool:
        """Check if onboarding is in progress"""
        return self.started_at is not None and not self.is_complete


class OnboardingPath(BaseModel):
    """Configuration for an onboarding path"""

    name: Literal["quick", "full", "chat"]
    display_name: str
    description: str
    estimated_time: str
    steps: List[str]


class FeatureDiscovery(BaseModel):
    """Feature discovery tracking"""

    user_id: str
    feature_name: str
    discovery_method: str
    discovered_at: datetime
    first_used_at: Optional[datetime] = None
    usage_count: int = 0
    last_used_at: Optional[datetime] = None

    @property
    def has_been_used(self) -> bool:
        """Check if feature has been used at least once"""
        return self.first_used_at is not None


# Onboarding path configurations
ONBOARDING_PATHS = {
    "quick": OnboardingPath(
        name="quick",
        display_name="Quick Start",
        description="Jump right in (30 sec)",
        estimated_time="30-45 seconds",
        steps=["path_selection", "timezone_setup", "focus_selection", "feature_demo", "completed"]
    ),
    "full": OnboardingPath(
        name="full",
        display_name="Show Me Around",
        description="Full tour (2 min)",
        estimated_time="90-120 seconds",
        steps=[
            "path_selection", "timezone_setup", "profile_setup",
            "food_demo", "voice_demo", "tracking_demo", "reminders_demo",
            "personality_demo", "learning_explanation", "completed"
        ]
    ),
    "chat": OnboardingPath(
        name="chat",
        display_name="Just Chat",
        description="I'll learn as we go",
        estimated_time="Ongoing",
        steps=["path_selection", "completed"]  # Minimal steps, features revealed contextually
    )
}

# Feature names for discovery tracking
TRACKABLE_FEATURES = [
    "food_tracking",
    "voice_notes",
    "custom_tracking",
    "reminders",
    "personality_customization",
    "visual_patterns",
    "transparency_view",
    "pep_talks",
    "daily_summaries"
]
