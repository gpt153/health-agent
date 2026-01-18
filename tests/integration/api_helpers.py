"""Helper utilities for API integration tests"""
from typing import Dict, Any, Optional
import httpx
from datetime import datetime


def assert_success_response(response: httpx.Response, expected_status: int = 200):
    """Assert that response is successful with expected status code"""
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, got {response.status_code}. "
        f"Response: {response.text}"
    )


def assert_error_response(
    response: httpx.Response,
    expected_status: int,
    expected_error_key: Optional[str] = None
):
    """Assert that response is an error with expected status code"""
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, got {response.status_code}. "
        f"Response: {response.text}"
    )

    if expected_error_key:
        data = response.json()
        assert expected_error_key in data or "detail" in data, (
            f"Expected error key '{expected_error_key}' or 'detail' in response"
        )


def assert_has_keys(data: Dict[str, Any], required_keys: list):
    """Assert that dictionary contains all required keys"""
    for key in required_keys:
        assert key in data, f"Missing required key: {key}"


def assert_valid_timestamp(timestamp_str: str):
    """Assert that string is a valid ISO8601 timestamp"""
    try:
        datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        raise AssertionError(f"Invalid timestamp format: {timestamp_str}")


def assert_valid_user_profile(profile: Dict[str, Any]):
    """Assert that user profile has expected structure"""
    assert isinstance(profile, dict), "Profile should be a dictionary"
    # Profile can be empty or have various fields, just check it's a dict


def assert_valid_food_entry(entry: Dict[str, Any]):
    """Assert that food entry has expected structure"""
    assert_has_keys(entry, ["total_calories"])
    assert isinstance(entry.get("total_calories"), (int, float)), (
        "total_calories should be numeric"
    )


def assert_valid_reminder(reminder: Dict[str, Any]):
    """Assert that reminder has expected structure"""
    required_keys = ["id", "user_id", "type", "message", "schedule", "active"]
    assert_has_keys(reminder, required_keys)
    assert reminder["type"] in ["daily", "one_time"], (
        f"Invalid reminder type: {reminder['type']}"
    )


def assert_valid_xp_response(xp_data: Dict[str, Any]):
    """Assert that XP response has expected structure"""
    required_keys = ["user_id", "xp", "level", "tier", "xp_to_next_level"]
    assert_has_keys(xp_data, required_keys)
    assert isinstance(xp_data["xp"], int), "XP should be an integer"
    assert isinstance(xp_data["level"], int), "Level should be an integer"
    assert xp_data["xp"] >= 0, "XP should be non-negative"
    assert xp_data["level"] >= 1, "Level should be at least 1"


def generate_test_profile() -> Dict[str, Any]:
    """Generate test profile data"""
    return {
        "name": "Test User",
        "age": "30",
        "height_cm": "175",
        "weight_kg": "70",
        "goal_type": "maintain"
    }


def generate_test_food_log() -> Dict[str, str]:
    """Generate test food log entry"""
    return {
        "description": "Grilled chicken breast with brown rice and vegetables"
    }


def generate_daily_reminder() -> Dict[str, Any]:
    """Generate daily reminder request data"""
    return {
        "type": "daily",
        "message": "Time to log your dinner!",
        "daily_time": "18:00",
        "timezone": "UTC"
    }


def generate_onetime_reminder() -> Dict[str, Any]:
    """Generate one-time reminder request data"""
    return {
        "type": "one_time",
        "message": "Don't forget your appointment",
        "trigger_time": "2025-12-31T15:00:00Z",
        "timezone": "UTC"
    }
