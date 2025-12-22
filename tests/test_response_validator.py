"""
Tests for response validator

Verifies that the validator correctly detects data claims without tool calls.
"""

import pytest
from src.utils.response_validator import (
    validate_response_against_tools,
    extract_numeric_claims,
    is_conversational_phrase
)


def test_validate_response_with_data_and_no_tools():
    """Should warn when response contains data but no tools were called"""
    response = "You've logged 1,234 calories today."
    tools_called = []

    warning = validate_response_against_tools(response, tools_called)

    assert warning is not None, "Should return warning"
    assert "unverified data" in warning.lower()


def test_validate_response_with_data_and_tools():
    """Should pass when response contains data and appropriate tool was called"""
    response = "You've logged 1,234 calories today."
    tools_called = ["get_daily_food_summary"]

    warning = validate_response_against_tools(response, tools_called)

    assert warning is None, "Should not return warning when tool was called"


def test_validate_response_with_no_data():
    """Should pass when response doesn't contain data claims"""
    response = "Would you like to log your food?"
    tools_called = []

    warning = validate_response_against_tools(response, tools_called)

    assert warning is None, "Should not warn for conversational responses"


def test_validate_response_streak_without_tool():
    """Should warn when mentioning streaks without calling get_streak_summary"""
    response = "Your streak is 14 days!"
    tools_called = []

    warning = validate_response_against_tools(response, tools_called)

    assert warning is not None, "Should warn when mentioning streaks without tool"


def test_validate_response_streak_with_tool():
    """Should pass when mentioning streaks after calling get_streak_summary"""
    response = "Your streak is 14 days!"
    tools_called = ["get_streak_summary"]

    warning = validate_response_against_tools(response, tools_called)

    assert warning is None, "Should not warn when tool was called"


def test_extract_numeric_claims():
    """Should extract numeric claims from text"""
    text = "You've logged 1,234 calories and have a 14-day streak."

    claims = extract_numeric_claims(text)

    assert len(claims) == 2
    assert ("1234", "calories") in claims
    assert ("14", "days") in claims or ("14", "day") in claims


def test_extract_numeric_claims_no_numbers():
    """Should return empty list when no numbers in text"""
    text = "Would you like to log your food?"

    claims = extract_numeric_claims(text)

    assert len(claims) == 0


def test_is_conversational_phrase_question():
    """Should detect questions as conversational"""
    text = "Would you like to log your food?"

    assert is_conversational_phrase(text) is True


def test_is_conversational_phrase_statement():
    """Should detect factual statements as non-conversational"""
    text = "You've logged 1,234 calories."

    assert is_conversational_phrase(text) is False


def test_is_conversational_phrase_offer():
    """Should detect offers as conversational"""
    text = "I can help you track your meals."

    assert is_conversational_phrase(text) is True
