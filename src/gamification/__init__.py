"""
Gamification system for Health Agent

This module implements a comprehensive motivation platform with:
- XP and leveling system
- Multi-domain streak tracking
- Achievement system
- Adaptive intelligence
- Challenges and reports

Phase 1: Foundation (XP, Streaks, Achievements)
"""

from src.gamification.xp_system import award_xp, get_user_xp, calculate_level_from_xp
from src.gamification.streak_system import update_streak, get_user_streaks, use_streak_freeze
from src.gamification.achievement_system import check_and_award_achievements, get_user_achievements

__all__ = [
    "award_xp",
    "get_user_xp",
    "calculate_level_from_xp",
    "update_streak",
    "get_user_streaks",
    "use_streak_freeze",
    "check_and_award_achievements",
    "get_user_achievements",
]
