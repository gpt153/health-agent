"""
Mock data store for gamification system

This is a temporary in-memory store that simulates database operations.
When the database is ready, this will be replaced with actual database queries.

Data Structure:
- user_xp: {user_id: {total_xp, current_level, xp_to_next_level, level_tier, ...}}
- xp_transactions: [{id, user_id, amount, source_type, source_id, reason, awarded_at}]
- user_streaks: {user_id: {streak_type: {current, best, last_date, freeze_days, ...}}}
- achievements: [{id, key, name, description, icon, category, criteria, xp_reward, tier}]
- user_achievements: {user_id: [{achievement_id, unlocked_at, progress}]}
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Any
from uuid import uuid4
import json

# In-memory storage (will be replaced with database)
_user_xp_store: Dict[str, Dict[str, Any]] = {}
_xp_transactions_store: List[Dict[str, Any]] = []
_user_streaks_store: Dict[str, Dict[str, Dict[str, Any]]] = {}
_achievements_store: List[Dict[str, Any]] = []
_user_achievements_store: Dict[str, List[Dict[str, Any]]] = {}


def init_achievements():
    """Initialize achievement definitions (simulates seeded database data)"""
    global _achievements_store

    if _achievements_store:
        return  # Already initialized

    _achievements_store = [
        # Consistency Achievements
        {
            "id": str(uuid4()),
            "achievement_key": "first_steps",
            "name": "First Steps",
            "description": "Complete your first tracked activity",
            "icon": "👣",
            "category": "consistency",
            "criteria": {"type": "completion_count", "value": 1, "domain": "any"},
            "xp_reward": 25,
            "tier": "bronze",
        },
        {
            "id": str(uuid4()),
            "achievement_key": "week_warrior",
            "name": "Week Warrior",
            "description": "Maintain a 7-day streak",
            "icon": "🔥",
            "category": "consistency",
            "criteria": {"type": "streak", "value": 7, "domain": "any"},
            "xp_reward": 100,
            "tier": "bronze",
        },
        {
            "id": str(uuid4()),
            "achievement_key": "two_week_titan",
            "name": "Two Week Titan",
            "description": "Maintain a 14-day streak",
            "icon": "⚡",
            "category": "consistency",
            "criteria": {"type": "streak", "value": 14, "domain": "any"},
            "xp_reward": 200,
            "tier": "silver",
        },
        {
            "id": str(uuid4()),
            "achievement_key": "monthly_master",
            "name": "Monthly Master",
            "description": "Maintain a 30-day streak",
            "icon": "🏆",
            "category": "consistency",
            "criteria": {"type": "streak", "value": 30, "domain": "any"},
            "xp_reward": 500,
            "tier": "gold",
        },
        # Domain-Specific Achievements
        {
            "id": str(uuid4()),
            "achievement_key": "pill_pro",
            "name": "Pill Pro",
            "description": "Complete 30 medication reminders",
            "icon": "💊",
            "category": "domain_specific",
            "criteria": {"type": "domain_count", "value": 30, "domain": "medication"},
            "xp_reward": 100,
            "tier": "bronze",
        },
        {
            "id": str(uuid4()),
            "achievement_key": "hydration_hero",
            "name": "Hydration Hero",
            "description": "Maintain 7-day water intake streak",
            "icon": "💧",
            "category": "domain_specific",
            "criteria": {"type": "streak", "value": 7, "domain": "hydration"},
            "xp_reward": 100,
            "tier": "bronze",
        },
        # Milestone Achievements
        {
            "id": str(uuid4()),
            "achievement_key": "bronze_tier",
            "name": "Bronze Tier",
            "description": "Reach level 5",
            "icon": "🥉",
            "category": "milestone",
            "criteria": {"type": "level", "value": 5},
            "xp_reward": 50,
            "tier": "bronze",
        },
        {
            "id": str(uuid4()),
            "achievement_key": "silver_tier",
            "name": "Silver Tier",
            "description": "Reach level 15",
            "icon": "🥈",
            "category": "milestone",
            "criteria": {"type": "level", "value": 15},
            "xp_reward": 150,
            "tier": "silver",
        },
        {
            "id": str(uuid4()),
            "achievement_key": "xp_collector",
            "name": "XP Collector",
            "description": "Earn 1000 total XP",
            "icon": "💰",
            "category": "milestone",
            "criteria": {"type": "total_xp", "value": 1000},
            "xp_reward": 200,
            "tier": "silver",
        },
    ]


# XP Functions
def get_user_xp_data(user_id: str) -> Dict[str, Any]:
    """Get user XP data (creates if doesn't exist)"""
    if user_id not in _user_xp_store:
        _user_xp_store[user_id] = {
            "user_id": user_id,
            "total_xp": 0,
            "current_level": 1,
            "xp_to_next_level": 100,
            "level_tier": "bronze",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
    return _user_xp_store[user_id]


def update_user_xp(user_id: str, xp_data: Dict[str, Any]) -> None:
    """Update user XP data"""
    xp_data["updated_at"] = datetime.now()
    _user_xp_store[user_id] = xp_data


def add_xp_transaction(user_id: str, amount: int, source_type: str, source_id: Optional[str], reason: str) -> str:
    """Add XP transaction"""
    transaction_id = str(uuid4())
    _xp_transactions_store.append({
        "id": transaction_id,
        "user_id": user_id,
        "amount": amount,
        "source_type": source_type,
        "source_id": source_id,
        "reason": reason,
        "awarded_at": datetime.now(),
    })
    return transaction_id


def get_xp_transactions(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent XP transactions for user"""
    user_transactions = [t for t in _xp_transactions_store if t["user_id"] == user_id]
    user_transactions.sort(key=lambda x: x["awarded_at"], reverse=True)
    return user_transactions[:limit]


# Streak Functions
def get_user_streak(user_id: str, streak_type: str, source_id: Optional[str] = None) -> Dict[str, Any]:
    """Get specific streak for user"""
    if user_id not in _user_streaks_store:
        _user_streaks_store[user_id] = {}

    key = f"{streak_type}:{source_id}" if source_id else streak_type

    if key not in _user_streaks_store[user_id]:
        _user_streaks_store[user_id][key] = {
            "id": str(uuid4()),
            "user_id": user_id,
            "streak_type": streak_type,
            "source_id": source_id,
            "current_streak": 0,
            "best_streak": 0,
            "last_activity_date": None,
            "freeze_days_remaining": 2,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

    return _user_streaks_store[user_id][key]


def update_user_streak(user_id: str, streak_type: str, streak_data: Dict[str, Any], source_id: Optional[str] = None) -> None:
    """Update streak data"""
    if user_id not in _user_streaks_store:
        _user_streaks_store[user_id] = {}

    key = f"{streak_type}:{source_id}" if source_id else streak_type
    streak_data["updated_at"] = datetime.now()
    _user_streaks_store[user_id][key] = streak_data


def get_all_user_streaks(user_id: str) -> List[Dict[str, Any]]:
    """Get all streaks for user"""
    if user_id not in _user_streaks_store:
        return []
    return list(_user_streaks_store[user_id].values())


# Achievement Functions
def get_all_achievements() -> List[Dict[str, Any]]:
    """Get all achievement definitions"""
    init_achievements()
    return _achievements_store


def get_achievement_by_key(key: str) -> Optional[Dict[str, Any]]:
    """Get achievement by key"""
    init_achievements()
    for achievement in _achievements_store:
        if achievement["achievement_key"] == key:
            return achievement
    return None


def get_user_achievement_unlocks(user_id: str) -> List[Dict[str, Any]]:
    """Get user's unlocked achievements"""
    if user_id not in _user_achievements_store:
        _user_achievements_store[user_id] = []
    return _user_achievements_store[user_id]


def add_user_achievement(user_id: str, achievement_id: str, progress: Optional[Dict[str, Any]] = None) -> None:
    """Add achievement unlock for user"""
    if user_id not in _user_achievements_store:
        _user_achievements_store[user_id] = []

    # Check if already unlocked
    for unlock in _user_achievements_store[user_id]:
        if unlock["achievement_id"] == achievement_id:
            return  # Already unlocked

    _user_achievements_store[user_id].append({
        "id": str(uuid4()),
        "user_id": user_id,
        "achievement_id": achievement_id,
        "unlocked_at": datetime.now(),
        "progress": progress,
    })


def has_user_unlocked_achievement(user_id: str, achievement_id: str) -> bool:
    """Check if user has unlocked achievement"""
    unlocks = get_user_achievement_unlocks(user_id)
    return any(u["achievement_id"] == achievement_id for u in unlocks)


def get_user_achievements(user_id: str) -> List[Dict[str, Any]]:
    """Get user's achievements (alias for get_user_achievement_unlocks for consistency)"""
    return get_user_achievement_unlocks(user_id)


def unlock_user_achievement(user_id: str, achievement_id: str) -> None:
    """Unlock an achievement for user (alias for add_user_achievement for consistency)"""
    add_user_achievement(user_id, achievement_id)


# Utility Functions
def clear_all_data():
    """Clear all mock data (for testing)"""
    global _user_xp_store, _xp_transactions_store, _user_streaks_store, _achievements_store, _user_achievements_store
    _user_xp_store = {}
    _xp_transactions_store = []
    _user_streaks_store = {}
    _achievements_store = []
    _user_achievements_store = {}
