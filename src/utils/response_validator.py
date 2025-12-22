"""
Response Validation Layer

Detects potential hallucinations when agent states data without calling tools.

This module provides validation to ensure the agent queries the database
before stating factual data, preventing hallucinations based on conversation
history that may have been cleared.
"""

import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

# Keywords that suggest agent is stating data
DATA_KEYWORDS = [
    "calories", "kcal", "protein", "carbs", "fat",
    "xp", "level", "streak", "days", "reminder",
    "meal", "food", "entry", "logged"
]

# Tool names that provide data
DATA_TOOLS = [
    "get_daily_food_summary",
    "get_user_xp_and_level",
    "get_streak_summary",
    "get_reminders",
    "get_food_history",
    "get_active_reminders",
    "get_user_achievements",
    "get_tracking_entries",
    "get_sleep_entries"
]


def validate_response_against_tools(
    response_text: str,
    tools_called: List[str]
) -> Optional[str]:
    """
    Check if response contains data claims without tool calls

    Args:
        response_text: Agent's response text
        tools_called: List of tool names that were called

    Returns:
        Warning message if validation fails, None if OK

    Examples:
        >>> validate_response_against_tools("You've logged 1234 calories", [])
        "⚠️ Internal warning: Response may contain unverified data"

        >>> validate_response_against_tools("You've logged 1234 calories", ["get_daily_food_summary"])
        None  # OK - tool was called
    """
    # Check if response mentions data keywords
    contains_data = any(keyword in response_text.lower() for keyword in DATA_KEYWORDS)

    if not contains_data:
        return None  # No data mentioned, OK

    # Check if any data-providing tools were called
    called_data_tools = [tool for tool in tools_called if tool in DATA_TOOLS]

    if not called_data_tools:
        # Agent mentioned data but didn't call tools - potential hallucination
        logger.warning(
            f"Agent response mentions data without tool calls. "
            f"Response: {response_text[:100]}... "
            f"Tools called: {tools_called}"
        )
        return "⚠️ Internal warning: Response may contain unverified data"

    return None  # Tools were called, OK


def extract_numeric_claims(text: str) -> List[tuple]:
    """
    Extract numeric claims from text (e.g., "1,234 calories", "14-day streak")

    Args:
        text: Text to extract claims from

    Returns:
        List of (number, context) tuples

    Examples:
        >>> extract_numeric_claims("You've logged 1,234 calories today")
        [('1234', 'calories')]

        >>> extract_numeric_claims("Your streak is 14 days")
        [('14', 'days')]
    """
    # Pattern: number followed by unit/context
    pattern = r"(\d+[,\d]*)\s+(calories|kcal|days?|xp|level|grams?|streak)"
    matches = re.findall(pattern, text.lower())
    return [(num.replace(",", ""), unit) for num, unit in matches]


def is_conversational_phrase(text: str) -> bool:
    """
    Check if text is conversational (vs stating facts)

    Args:
        text: Text to check

    Returns:
        True if conversational, False if stating facts

    Examples:
        >>> is_conversational_phrase("Would you like to log your food?")
        True

        >>> is_conversational_phrase("You've logged 1234 calories")
        False
    """
    conversational_indicators = [
        "would you like",
        "do you want",
        "shall i",
        "let me",
        "i can",
        "would you prefer",
        "should i",
        "?",  # Question mark indicates conversation
    ]

    text_lower = text.lower()
    return any(indicator in text_lower for indicator in conversational_indicators)
