"""
Challenge System - Phase 4: Challenges & Social

Provides pre-built health challenges, custom challenge creation, and progress tracking.

Challenges motivate users through goal-setting and achievement across health domains.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from src.db import queries
from src.gamification.mock_store import mock_store  # FIXME: Migrate to database

logger = logging.getLogger(__name__)


class ChallengeType(Enum):
    """Challenge type categories"""
    STREAK = "streak"          # Build a streak (e.g., "7-day meditation streak")
    CONSISTENCY = "consistency"  # Complete X activities in Y days
    VARIETY = "variety"        # Try different activity types
    MILESTONE = "milestone"    # Reach a specific goal (e.g., "1000 XP")
    CUSTOM = "custom"          # User-defined challenge


class ChallengeDifficulty(Enum):
    """Challenge difficulty levels"""
    EASY = "easy"           # Beginner-friendly (1-7 days)
    MEDIUM = "medium"       # Moderate commitment (7-14 days)
    HARD = "hard"           # Challenging (14-30 days)
    EXPERT = "expert"       # Advanced (30+ days)


class ChallengeStatus(Enum):
    """User challenge status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


@dataclass
class Challenge:
    """Challenge definition"""
    id: str
    name: str
    description: str
    challenge_type: ChallengeType
    difficulty: ChallengeDifficulty
    duration_days: int
    goal_target: int           # Target number (7 days, 1000 XP, etc.)
    goal_metric: str           # What to count (streak, xp, activities, etc.)
    domain: Optional[str]      # Health domain (medication, nutrition, etc.) or None for any
    xp_reward: int            # XP awarded on completion
    icon: str                 # Emoji icon
    tags: List[str]           # Tags for filtering (beginner, advanced, etc.)


@dataclass
class UserChallenge:
    """User's challenge progress"""
    id: str
    user_id: str
    challenge_id: str
    status: ChallengeStatus
    started_at: datetime
    progress: int              # Current progress toward goal
    goal_target: int          # Target to reach
    completed_at: Optional[datetime]
    failed_at: Optional[datetime]
    days_active: int          # Days user has been working on it
    last_activity: Optional[datetime]


# ============================================
# Pre-Built Challenge Library (10-15 challenges)
# ============================================

CHALLENGE_LIBRARY: List[Challenge] = [
    # ========== EASY CHALLENGES (1-7 days) ==========
    Challenge(
        id="week_warrior",
        name="Week Warrior",
        description="Complete any health activity for 7 consecutive days",
        challenge_type=ChallengeType.STREAK,
        difficulty=ChallengeDifficulty.EASY,
        duration_days=7,
        goal_target=7,
        goal_metric="streak_days",
        domain=None,  # Any domain
        xp_reward=100,
        icon="🏆",
        tags=["beginner", "streak", "consistency"]
    ),

    Challenge(
        id="medication_master",
        name="Medication Master",
        description="Take your medication on time for 7 days straight",
        challenge_type=ChallengeType.STREAK,
        difficulty=ChallengeDifficulty.EASY,
        duration_days=7,
        goal_target=7,
        goal_metric="medication_streak",
        domain="medication",
        xp_reward=100,
        icon="💊",
        tags=["beginner", "medication", "streak"]
    ),

    Challenge(
        id="nutrition_novice",
        name="Nutrition Novice",
        description="Log all your meals for 5 consecutive days",
        challenge_type=ChallengeType.STREAK,
        difficulty=ChallengeDifficulty.EASY,
        duration_days=5,
        goal_target=5,
        goal_metric="nutrition_streak",
        domain="nutrition",
        xp_reward=75,
        icon="🍎",
        tags=["beginner", "nutrition", "streak"]
    ),

    Challenge(
        id="activity_explorer",
        name="Activity Explorer",
        description="Try 3 different health activities in one week",
        challenge_type=ChallengeType.VARIETY,
        difficulty=ChallengeDifficulty.EASY,
        duration_days=7,
        goal_target=3,
        goal_metric="unique_activities",
        domain=None,
        xp_reward=80,
        icon="🔍",
        tags=["beginner", "variety", "exploration"]
    ),

    # ========== MEDIUM CHALLENGES (7-14 days) ==========
    Challenge(
        id="two_week_titan",
        name="Two Week Titan",
        description="Maintain a perfect health streak for 14 consecutive days",
        challenge_type=ChallengeType.STREAK,
        difficulty=ChallengeDifficulty.MEDIUM,
        duration_days=14,
        goal_target=14,
        goal_metric="streak_days",
        domain=None,
        xp_reward=200,
        icon="💪",
        tags=["intermediate", "streak", "consistency"]
    ),

    Challenge(
        id="xp_accumulator",
        name="XP Accumulator",
        description="Earn 500 XP in 10 days",
        challenge_type=ChallengeType.MILESTONE,
        difficulty=ChallengeDifficulty.MEDIUM,
        duration_days=10,
        goal_target=500,
        goal_metric="xp_earned",
        domain=None,
        xp_reward=150,
        icon="⭐",
        tags=["intermediate", "xp", "milestone"]
    ),

    Challenge(
        id="sleep_scholar",
        name="Sleep Scholar",
        description="Track your sleep every day for 10 days",
        challenge_type=ChallengeType.STREAK,
        difficulty=ChallengeDifficulty.MEDIUM,
        duration_days=10,
        goal_target=10,
        goal_metric="sleep_streak",
        domain="sleep",
        xp_reward=120,
        icon="😴",
        tags=["intermediate", "sleep", "streak"]
    ),

    Challenge(
        id="consistency_king",
        name="Consistency King",
        description="Complete at least one health activity every day for 14 days",
        challenge_type=ChallengeType.CONSISTENCY,
        difficulty=ChallengeDifficulty.MEDIUM,
        duration_days=14,
        goal_target=14,
        goal_metric="active_days",
        domain=None,
        xp_reward=180,
        icon="👑",
        tags=["intermediate", "consistency", "daily"]
    ),

    # ========== HARD CHALLENGES (14-30 days) ==========
    Challenge(
        id="monthly_master",
        name="Monthly Master",
        description="Maintain a perfect health streak for 30 consecutive days",
        challenge_type=ChallengeType.STREAK,
        difficulty=ChallengeDifficulty.HARD,
        duration_days=30,
        goal_target=30,
        goal_metric="streak_days",
        domain=None,
        xp_reward=500,
        icon="🌟",
        tags=["advanced", "streak", "consistency", "month"]
    ),

    Challenge(
        id="domain_dominance",
        name="Domain Dominance",
        description="Maintain streaks in 3 different health domains for 21 days",
        challenge_type=ChallengeType.VARIETY,
        difficulty=ChallengeDifficulty.HARD,
        duration_days=21,
        goal_target=3,
        goal_metric="domain_streaks",
        domain=None,
        xp_reward=400,
        icon="🎯",
        tags=["advanced", "variety", "multi-domain"]
    ),

    Challenge(
        id="xp_legend",
        name="XP Legend",
        description="Earn 2000 XP in 30 days",
        challenge_type=ChallengeType.MILESTONE,
        difficulty=ChallengeDifficulty.HARD,
        duration_days=30,
        goal_target=2000,
        goal_metric="xp_earned",
        domain=None,
        xp_reward=600,
        icon="🏅",
        tags=["advanced", "xp", "milestone"]
    ),

    # ========== EXPERT CHALLENGES (30+ days) ==========
    Challenge(
        id="hundred_day_hero",
        name="Hundred Day Hero",
        description="Maintain a perfect health streak for 100 consecutive days",
        challenge_type=ChallengeType.STREAK,
        difficulty=ChallengeDifficulty.EXPERT,
        duration_days=100,
        goal_target=100,
        goal_metric="streak_days",
        domain=None,
        xp_reward=2000,
        icon="🦸",
        tags=["expert", "streak", "consistency", "legendary"]
    ),

    Challenge(
        id="perfect_month",
        name="Perfect Month",
        description="Complete ALL health activities every single day for 30 days",
        challenge_type=ChallengeType.CONSISTENCY,
        difficulty=ChallengeDifficulty.EXPERT,
        duration_days=30,
        goal_target=30,
        goal_metric="perfect_days",
        domain=None,
        xp_reward=1000,
        icon="💎",
        tags=["expert", "consistency", "perfect"]
    ),

    Challenge(
        id="holistic_health",
        name="Holistic Health Champion",
        description="Maintain active streaks in ALL 5 health domains for 30 days",
        challenge_type=ChallengeType.VARIETY,
        difficulty=ChallengeDifficulty.EXPERT,
        duration_days=30,
        goal_target=5,
        goal_metric="domain_streaks",
        domain=None,
        xp_reward=1500,
        icon="🌈",
        tags=["expert", "variety", "holistic", "all-domains"]
    )
]


# ============================================
# Challenge Management Functions
# ============================================

def get_all_challenges() -> List[Challenge]:
    """
    Get all challenges from the library

    Returns:
        List of all challenge definitions
    """
    return CHALLENGE_LIBRARY.copy()


def get_challenge_by_id(challenge_id: str) -> Optional[Challenge]:
    """
    Get a specific challenge by ID

    Args:
        challenge_id: Challenge ID

    Returns:
        Challenge if found, None otherwise
    """
    for challenge in CHALLENGE_LIBRARY:
        if challenge.id == challenge_id:
            return challenge
    return None


def filter_challenges(
    difficulty: Optional[ChallengeDifficulty] = None,
    challenge_type: Optional[ChallengeType] = None,
    domain: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> List[Challenge]:
    """
    Filter challenges by criteria

    Args:
        difficulty: Filter by difficulty level
        challenge_type: Filter by challenge type
        domain: Filter by health domain
        tags: Filter by tags (matches any tag)

    Returns:
        Filtered list of challenges
    """
    filtered = CHALLENGE_LIBRARY.copy()

    if difficulty:
        filtered = [c for c in filtered if c.difficulty == difficulty]

    if challenge_type:
        filtered = [c for c in filtered if c.challenge_type == challenge_type]

    if domain:
        filtered = [c for c in filtered if c.domain == domain or c.domain is None]

    if tags:
        filtered = [
            c for c in filtered
            if any(tag in c.tags for tag in tags)
        ]

    return filtered


async def start_challenge(user_id: str, challenge_id: str) -> Dict:
    """
    Start a challenge for a user

    Args:
        user_id: Telegram user ID
        challenge_id: Challenge ID to start

    Returns:
        {
            'success': bool,
            'user_challenge': UserChallenge or None,
            'message': str
        }
    """
    try:
        # Get challenge definition
        challenge = get_challenge_by_id(challenge_id)
        if not challenge:
            return {
                'success': False,
                'user_challenge': None,
                'message': f"Challenge '{challenge_id}' not found"
            }

        # Check if user already has this challenge active
        existing = mock_store.get_user_challenge(user_id, challenge_id)
        if existing and existing.status == ChallengeStatus.IN_PROGRESS:
            return {
                'success': False,
                'user_challenge': None,
                'message': f"You're already working on '{challenge.name}'"
            }

        # Create user challenge
        user_challenge = UserChallenge(
            id=f"{user_id}_{challenge_id}_{datetime.now().timestamp()}",
            user_id=user_id,
            challenge_id=challenge_id,
            status=ChallengeStatus.IN_PROGRESS,
            started_at=datetime.now(),
            progress=0,
            goal_target=challenge.goal_target,
            completed_at=None,
            failed_at=None,
            days_active=0,
            last_activity=None
        )

        # Save to store
        mock_store.save_user_challenge(user_challenge)

        logger.info(f"User {user_id} started challenge '{challenge_id}'")

        return {
            'success': True,
            'user_challenge': user_challenge,
            'message': (
                f"{challenge.icon} **Challenge Started: {challenge.name}**\n\n"
                f"{challenge.description}\n\n"
                f"**Goal:** {challenge.goal_target} {challenge.goal_metric}\n"
                f"**Duration:** {challenge.duration_days} days\n"
                f"**Reward:** {challenge.xp_reward} XP\n"
                f"**Difficulty:** {challenge.difficulty.value.title()}\n\n"
                f"Good luck! 💪"
            )
        }

    except Exception as e:
        logger.error(f"Error starting challenge: {e}", exc_info=True)
        return {
            'success': False,
            'user_challenge': None,
            'message': f"Failed to start challenge: {str(e)}"
        }


async def update_challenge_progress(
    user_id: str,
    challenge_id: str,
    activity_type: str,
    activity_date: date
) -> Optional[UserChallenge]:
    """
    Update challenge progress based on activity

    Called after health activities to check and update challenge progress.

    Args:
        user_id: Telegram user ID
        challenge_id: Challenge ID
        activity_type: Type of activity (medication, nutrition, etc.)
        activity_date: Date of activity

    Returns:
        Updated UserChallenge if progress was made, None otherwise
    """
    try:
        # Get user challenge
        user_challenge = mock_store.get_user_challenge(user_id, challenge_id)
        if not user_challenge or user_challenge.status != ChallengeStatus.IN_PROGRESS:
            return None

        # Get challenge definition
        challenge = get_challenge_by_id(challenge_id)
        if not challenge:
            return None

        # Update progress based on challenge type
        updated = False

        if challenge.challenge_type == ChallengeType.STREAK:
            # Check if activity matches domain
            if challenge.domain is None or activity_type == challenge.domain:
                # Get current streak
                from src.gamification.streak_system import get_user_streak
                streak = await get_user_streak(user_id, activity_type)
                if streak:
                    user_challenge.progress = streak['current_streak']
                    updated = True

        elif challenge.challenge_type == ChallengeType.CONSISTENCY:
            # Count active days
            # This would check XP transactions across days
            pass  # Implement based on specific challenge

        elif challenge.challenge_type == ChallengeType.MILESTONE:
            # Track milestone progress (XP, activities, etc.)
            if challenge.goal_metric == "xp_earned":
                # Calculate XP earned since challenge start
                from src.gamification import get_user_xp
                xp_data = await get_user_xp(user_id)
                # Would need to track XP at start of challenge
                # For now, just increment
                user_challenge.progress += 10  # Placeholder
                updated = True

        # Update last activity
        user_challenge.last_activity = datetime.now()
        user_challenge.days_active = (datetime.now() - user_challenge.started_at).days

        # Check if challenge is complete
        if user_challenge.progress >= user_challenge.goal_target:
            user_challenge.status = ChallengeStatus.COMPLETED
            user_challenge.completed_at = datetime.now()

            # Award XP
            from src.gamification import award_xp
            await award_xp(
                user_id=user_id,
                amount=challenge.xp_reward,
                source_type="challenge",
                source_id=challenge_id,
                reason=f"Completed challenge: {challenge.name}"
            )

            updated = True

        # Check if challenge has failed (exceeded duration without completion)
        elif user_challenge.days_active > challenge.duration_days:
            user_challenge.status = ChallengeStatus.FAILED
            user_challenge.failed_at = datetime.now()
            updated = True

        if updated:
            mock_store.save_user_challenge(user_challenge)

        return user_challenge if updated else None

    except Exception as e:
        logger.error(f"Error updating challenge progress: {e}", exc_info=True)
        return None


async def get_user_challenges(
    user_id: str,
    status: Optional[ChallengeStatus] = None
) -> List[UserChallenge]:
    """
    Get all challenges for a user

    Args:
        user_id: Telegram user ID
        status: Optional status filter

    Returns:
        List of user challenges
    """
    challenges = mock_store.get_all_user_challenges(user_id)

    if status:
        challenges = [c for c in challenges if c.status == status]

    return challenges


def format_challenge_display(challenge: Challenge) -> str:
    """
    Format challenge for display

    Args:
        challenge: Challenge to format

    Returns:
        Formatted challenge description
    """
    difficulty_emoji = {
        ChallengeDifficulty.EASY: "🟢",
        ChallengeDifficulty.MEDIUM: "🟡",
        ChallengeDifficulty.HARD: "🟠",
        ChallengeDifficulty.EXPERT: "🔴"
    }

    diff_emoji = difficulty_emoji.get(challenge.difficulty, "⚪")

    return (
        f"{challenge.icon} **{challenge.name}** {diff_emoji}\n"
        f"{challenge.description}\n\n"
        f"**Goal:** {challenge.goal_target} {challenge.goal_metric}\n"
        f"**Duration:** {challenge.duration_days} days\n"
        f"**Reward:** {challenge.xp_reward} XP\n"
        f"**Difficulty:** {challenge.difficulty.value.title()}"
    )


def format_user_challenge_progress(user_challenge: UserChallenge, challenge: Challenge) -> str:
    """
    Format user challenge progress for display

    Args:
        user_challenge: User's challenge
        challenge: Challenge definition

    Returns:
        Formatted progress display
    """
    # Progress bar
    progress_pct = min((user_challenge.progress / user_challenge.goal_target) * 100, 100)
    bar_length = int(progress_pct / 5)  # 20 chars total
    bar = "▓" * bar_length + "░" * (20 - bar_length)

    # Status emoji
    status_emoji = {
        ChallengeStatus.IN_PROGRESS: "⏳",
        ChallengeStatus.COMPLETED: "✅",
        ChallengeStatus.FAILED: "❌",
        ChallengeStatus.ABANDONED: "🚫"
    }
    status_icon = status_emoji.get(user_challenge.status, "❓")

    # Time remaining
    if user_challenge.status == ChallengeStatus.IN_PROGRESS:
        time_remaining = challenge.duration_days - user_challenge.days_active
        time_text = f"\n**Time Left:** {time_remaining} days"
    else:
        time_text = ""

    return (
        f"{challenge.icon} **{challenge.name}** {status_icon}\n"
        f"Progress: {bar} {int(progress_pct)}%\n"
        f"**{user_challenge.progress}/{user_challenge.goal_target}** {challenge.goal_metric}"
        f"{time_text}"
    )


# Add mock_store methods (these would be in mock_store.py)
# For now, adding placeholder implementations

def _init_mock_challenge_storage():
    """Initialize mock storage for challenges"""
    if not hasattr(mock_store, '_user_challenges'):
        mock_store._user_challenges = {}
