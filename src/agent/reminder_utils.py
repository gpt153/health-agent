"""Reminder utility functions for smart detection and tracking"""
import re
from typing import Tuple

# Health-related keywords that should have tracking enabled by default
HEALTH_KEYWORDS = {
    # Medication
    'medication', 'medicine', 'pill', 'pills', 'tablet', 'capsule',
    'supplement', 'vitamin', 'insulin', 'inhaler', 'injection',
    'dose', 'prescription', 'meds',

    # Fitness
    'exercise', 'workout', 'walk', 'run', 'gym', 'yoga', 'stretch',
    'jog', 'swim', 'cycle', 'train', 'cardio', 'weights',

    # Wellness
    'water', 'hydration', 'hydrate', 'drink', 'meditation', 'meditate',
    'journal', 'sleep', 'bedtime', 'rest',

    # Medical
    'blood pressure', 'glucose', 'temperature', 'weight', 'bp',
    'sugar', 'check', 'monitor', 'track', 'log'
}


def should_enable_tracking(message: str) -> Tuple[bool, str]:
    """
    Determine if a reminder should have completion tracking enabled
    based on message content.

    Args:
        message: Reminder message text

    Returns:
        Tuple of (should_enable: bool, reason: str)
    """
    message_lower = message.lower()

    # Check for health keywords
    for keyword in HEALTH_KEYWORDS:
        if keyword in message_lower:
            return (
                True,
                f"Detected health-related keyword: '{keyword}'. "
                "Completion tracking will help you stay consistent."
            )

    # Default: No tracking for general reminders
    return (False, "")


def format_tracking_suggestion(message: str, keyword: str = None) -> str:
    """
    Format a suggestion message for enabling tracking.

    Args:
        message: Reminder message
        keyword: The detected health keyword (optional)

    Returns:
        Formatted suggestion text
    """
    suggestion = "💊 I noticed this is a health-related reminder.\n\n"

    if keyword:
        suggestion += f"Detected: **{keyword}**\n\n"

    suggestion += (
        "**Completion tracking enabled:**\n"
        "✅ 'Done' button on reminders\n"
        "📊 Track completion times and patterns\n"
        "🔥 Build streaks for motivation\n"
        "📈 View statistics and insights\n\n"
        "This helps you build healthy habits!"
    )

    return suggestion
