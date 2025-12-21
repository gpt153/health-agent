"""
XP and Leveling System

Manages XP awards, level calculations, and tier progression.

Leveling Curve:
- Level 1-5 (Bronze): 100 XP per level
- Level 6-15 (Silver): 200 XP per level
- Level 16-30 (Gold): 500 XP per level
- Level 31+ (Platinum): 1000 XP per level

XP Award Rules:
- Reminder completion: 10 XP (base) + streak bonuses
- Meal logging: 5 XP
- Exercise logged: 15 XP
- Sleep quiz: 20 XP
- Tracking entry: 10 XP
- Streak milestones: 50-200 XP
- Achievement unlocks: 25-500 XP
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

from src.db import queries

logger = logging.getLogger(__name__)


def calculate_level_from_xp(total_xp: int) -> Dict[str, any]:
    """
    Calculate level and tier from total XP

    Returns:
        {
            'current_level': int,
            'level_tier': str (bronze/silver/gold/platinum),
            'xp_in_current_level': int,
            'xp_to_next_level': int,
            'total_xp_for_next_level': int
        }
    """
    level = 1
    xp_needed = 0
    xp_remaining = total_xp

    # Bronze tier (Levels 1-5): 100 XP per level
    while level < 5 and xp_remaining >= 100:
        xp_remaining -= 100
        level += 1
        xp_needed += 100

    # Silver tier (Levels 6-15): 200 XP per level
    while level < 15 and xp_remaining >= 200:
        xp_remaining -= 200
        level += 1
        xp_needed += 200

    # Gold tier (Levels 16-30): 500 XP per level
    while level < 30 and xp_remaining >= 500:
        xp_remaining -= 500
        level += 1
        xp_needed += 500

    # Platinum tier (Levels 31+): 1000 XP per level
    while xp_remaining >= 1000:
        xp_remaining -= 1000
        level += 1
        xp_needed += 1000

    # Determine tier
    if level <= 5:
        tier = "bronze"
        xp_for_next_level = 100
    elif level <= 15:
        tier = "silver"
        xp_for_next_level = 200
    elif level <= 30:
        tier = "gold"
        xp_for_next_level = 500
    else:
        tier = "platinum"
        xp_for_next_level = 1000

    return {
        "current_level": level,
        "level_tier": tier,
        "xp_in_current_level": xp_remaining,
        "xp_to_next_level": xp_for_next_level - xp_remaining,
        "total_xp_for_next_level": xp_needed + xp_for_next_level,
    }


async def award_xp(
    user_id: str,
    amount: int,
    source_type: str,
    source_id: Optional[str] = None,
    reason: str = "Health activity completed"
) -> Dict[str, any]:
    """
    Award XP to user and check for level up

    Args:
        user_id: User's Telegram ID
        amount: Amount of XP to award
        source_type: Type of activity (reminder, meal, exercise, sleep, tracking)
        source_id: ID of the source activity (optional)
        reason: Human-readable description

    Returns:
        {
            'xp_awarded': int,
            'new_total_xp': int,
            'leveled_up': bool,
            'new_level': int,
            'old_level': int,
            'new_tier': str,
            'old_tier': str,
            'tier_changed': bool,
            'unlocked_features': list
        }
    """
    # Get current XP data from database
    xp_data = await queries.get_user_xp_data(user_id)
    old_level = xp_data["current_level"]
    old_tier = xp_data["level_tier"]
    old_total_xp = xp_data["total_xp"]

    # Add XP
    new_total_xp = old_total_xp + amount

    # Calculate new level
    level_info = calculate_level_from_xp(new_total_xp)

    new_level = level_info["current_level"]
    new_tier = level_info["level_tier"]
    leveled_up = new_level > old_level
    tier_changed = new_tier != old_tier

    # Update user XP in database
    updated_xp_data = {
        "total_xp": new_total_xp,
        "current_level": new_level,
        "xp_to_next_level": level_info["xp_to_next_level"],
        "level_tier": new_tier,
    }
    await queries.update_user_xp(user_id, updated_xp_data)

    # Log transaction to database
    await queries.add_xp_transaction(user_id, amount, source_type, source_id, reason)

    # Determine unlocked features (if tier changed)
    unlocked_features = []
    if tier_changed:
        if new_tier == "silver":
            unlocked_features.append("Advanced statistics")
        elif new_tier == "gold":
            unlocked_features.append("Custom challenges")
            unlocked_features.append("Detailed analytics")
        elif new_tier == "platinum":
            unlocked_features.append("Avatar customization")
            unlocked_features.append("Data export")

    logger.info(
        f"Awarded {amount} XP to user {user_id} for {source_type}. "
        f"Total: {new_total_xp} XP, Level: {new_level}, Tier: {new_tier}"
    )

    if leveled_up:
        logger.info(f"User {user_id} leveled up from {old_level} to {new_level}!")

    return {
        "xp_awarded": amount,
        "new_total_xp": new_total_xp,
        "old_total_xp": old_total_xp,
        "leveled_up": leveled_up,
        "new_level": new_level,
        "old_level": old_level,
        "new_tier": new_tier,
        "old_tier": old_tier,
        "tier_changed": tier_changed,
        "xp_to_next_level": level_info["xp_to_next_level"],
        "unlocked_features": unlocked_features,
    }


async def get_user_xp(user_id: str) -> Dict[str, any]:
    """
    Get user's current XP and level information

    Returns:
        {
            'user_id': str,
            'total_xp': int,
            'current_level': int,
            'xp_to_next_level': int,
            'level_tier': str,
            'xp_in_current_level': int
        }
    """
    xp_data = await queries.get_user_xp_data(user_id)
    level_info = calculate_level_from_xp(xp_data["total_xp"])

    return {
        "user_id": user_id,
        "total_xp": xp_data["total_xp"],
        "current_level": level_info["current_level"],
        "xp_to_next_level": level_info["xp_to_next_level"],
        "xp_in_current_level": level_info["xp_in_current_level"],
        "level_tier": level_info["level_tier"],
    }


async def get_xp_history(user_id: str, days: int = 7) -> List[Dict[str, any]]:
    """
    Get recent XP transaction history

    Args:
        user_id: User's Telegram ID
        days: Number of days of history to retrieve

    Returns:
        List of XP transactions sorted by date (newest first)
    """
    transactions = await queries.get_xp_transactions(user_id, limit=50)

    # Filter by days
    cutoff_date = datetime.now() - timedelta(days=days)
    filtered = [t for t in transactions if t["awarded_at"] >= cutoff_date]

    return filtered


def get_xp_for_activity(activity_type: str, **kwargs) -> int:
    """
    Calculate XP amount for different activity types

    Args:
        activity_type: Type of activity
        **kwargs: Additional context (has_streak, intensity, etc.)

    Returns:
        XP amount to award
    """
    base_xp = {
        "reminder": 10,
        "meal": 5,
        "exercise": 15,
        "sleep": 20,
        "tracking": 10,
        "achievement": 0,  # Determined by achievement
    }

    amount = base_xp.get(activity_type, 10)

    # Bonuses
    if kwargs.get("on_time"):
        amount += 5
    if kwargs.get("streak_7"):
        amount += 10
    if kwargs.get("streak_14"):
        amount += 20
    if kwargs.get("high_intensity"):
        amount += 10

    return amount
