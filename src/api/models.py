"""Pydantic models for API request/response validation"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    user_id: str = Field(..., description="User identifier")
    message: str = Field(..., description="User message text")
    message_history: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Optional message history for context"
    )


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    response: str = Field(..., description="Agent's response")
    timestamp: datetime = Field(..., description="Response timestamp")
    user_id: str = Field(..., description="User identifier")


class UserProfileRequest(BaseModel):
    """Request to create or update user profile"""
    user_id: str = Field(..., description="User identifier")
    profile: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Profile fields (age, height_cm, weight_kg, etc.)"
    )


class UserProfileResponse(BaseModel):
    """Response with user profile data"""
    user_id: str
    profile: Dict[str, Any]
    preferences: Optional[Dict[str, Any]] = None


class ProfileUpdateRequest(BaseModel):
    """Request to update a profile field"""
    field: str = Field(..., description="Profile field name")
    value: Any = Field(..., description="New value for field")


class PreferencesUpdateRequest(BaseModel):
    """Request to update user preferences"""
    preference: str = Field(..., description="Preference name")
    value: Any = Field(..., description="New preference value")


class FoodLogRequest(BaseModel):
    """Request to log food"""
    description: str = Field(..., description="Food description")
    timestamp: Optional[datetime] = Field(
        default=None,
        description="When food was eaten (defaults to now)"
    )


class FoodSummaryResponse(BaseModel):
    """Response with food summary"""
    date: str
    entries: List[Dict[str, Any]]
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float


class ReminderRequest(BaseModel):
    """Request to create a reminder"""
    type: str = Field(..., description="Reminder type: one_time or daily")
    message: str = Field(..., description="Reminder message")
    trigger_time: Optional[str] = Field(
        default=None,
        description="ISO8601 datetime for one_time reminders"
    )
    daily_time: Optional[str] = Field(
        default=None,
        description="HH:MM time for daily reminders"
    )
    timezone: Optional[str] = Field(
        default="UTC",
        description="User's timezone"
    )


class ReminderResponse(BaseModel):
    """Response with reminder details"""
    id: str
    user_id: str
    type: str
    message: str
    schedule: Dict[str, Any]
    active: bool


class ReminderListResponse(BaseModel):
    """Response with list of reminders"""
    reminders: List[ReminderResponse]


class ReminderStatusResponse(BaseModel):
    """Response with reminder status"""
    id: str
    triggered: bool
    completed: bool = False
    completed_at: Optional[datetime] = None


class XPResponse(BaseModel):
    """Response with XP and level info"""
    user_id: str
    xp: int
    level: int
    tier: str
    xp_to_next_level: int


class StreakResponse(BaseModel):
    """Response with streak info"""
    user_id: str
    streaks: List[Dict[str, Any]]


class AchievementResponse(BaseModel):
    """Response with achievement info"""
    user_id: str
    unlocked: List[Dict[str, Any]]
    locked: List[Dict[str, Any]]


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    database: str = Field(..., description="Database connection status")
    timestamp: datetime = Field(..., description="Check timestamp")


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================================
# Formula API Models (Epic 009 - Phase 3)
# ============================================================================

class FormulaCreateRequest(BaseModel):
    """Request to create a new formula"""
    name: str = Field(..., description="Formula name", min_length=1, max_length=200)
    keywords: List[str] = Field(default_factory=list, description="Search keywords")
    description: Optional[str] = Field(None, description="Formula description")
    foods: List[Dict[str, Any]] = Field(..., description="Food items in formula")
    total_calories: int = Field(..., description="Total calories", ge=0)
    total_macros: Dict[str, float] = Field(..., description="Macros: protein, carbs, fat")
    reference_photo_path: Optional[str] = Field(None, description="Reference photo path")
    created_from_entry_id: Optional[str] = Field(None, description="Original food entry UUID")


class FormulaUpdateRequest(BaseModel):
    """Request to update a formula"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    keywords: Optional[List[str]] = None
    description: Optional[str] = None
    foods: Optional[List[Dict[str, Any]]] = None
    total_calories: Optional[int] = Field(None, ge=0)
    total_macros: Optional[Dict[str, float]] = None


class FormulaResponse(BaseModel):
    """Formula response model"""
    id: str
    name: str
    keywords: List[str]
    description: Optional[str]
    foods: List[Dict[str, Any]]
    total_calories: int
    total_macros: Dict[str, float]
    reference_photo_path: Optional[str]
    is_auto_detected: bool
    confidence_score: Optional[float]
    times_used: int
    last_used_at: datetime
    created_at: datetime


class FormulaListResponse(BaseModel):
    """List of formulas response"""
    formulas: List[FormulaResponse]
    total_count: int


class FormulaSearchRequest(BaseModel):
    """Formula search request"""
    keyword: str = Field(..., description="Search keyword", min_length=1)
    limit: int = Field(5, description="Max results", ge=1, le=20)


class FormulaSearchResponse(BaseModel):
    """Formula search results"""
    formulas: List[Dict[str, Any]]
    query: str
    match_count: int


class FormulaUseRequest(BaseModel):
    """Request to log formula usage"""
    food_entry_id: str = Field(..., description="Food entry UUID where formula was used")
    match_method: str = Field(..., description="How matched: keyword, visual, combined, manual")
    match_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_exact_match: bool = Field(True, description="Whether it was an exact match")
    variations: Optional[Dict[str, Any]] = Field(None, description="Any deviations from formula")


class FormulaSuggestionRequest(BaseModel):
    """Request for formula suggestions"""
    text: Optional[str] = Field(None, description="Text input from user")
    image_path: Optional[str] = Field(None, description="Image path if available")
    max_suggestions: int = Field(3, ge=1, le=10)


class FormulaSuggestionResponse(BaseModel):
    """Formula suggestion response"""
    suggestions: List[Dict[str, Any]]
    suggestion_count: int
