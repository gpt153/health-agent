"""Integration tests for reminder API endpoints"""
import pytest
import httpx
from typing import Dict
from tests.integration.api_helpers import (
    assert_success_response,
    assert_error_response,
    assert_has_keys,
    assert_valid_reminder,
    generate_daily_reminder,
    generate_onetime_reminder
)


@pytest.mark.asyncio
async def test_create_daily_reminder(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test creating a daily reminder"""
    reminder_data = generate_daily_reminder()

    response = await api_client.post(
        f"/api/v1/users/{test_user}/reminders",
        json=reminder_data,
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert_valid_reminder(data)
    assert data["type"] == "daily"
    assert data["user_id"] == test_user
    assert data["active"] is True


@pytest.mark.asyncio
async def test_create_onetime_reminder(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test creating a one-time reminder"""
    reminder_data = generate_onetime_reminder()

    response = await api_client.post(
        f"/api/v1/users/{test_user}/reminders",
        json=reminder_data,
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert_valid_reminder(data)
    assert data["type"] == "one_time"
    assert data["user_id"] == test_user


@pytest.mark.asyncio
async def test_create_reminder_with_timezone(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test creating reminder with custom timezone"""
    reminder_data = {
        "type": "daily",
        "message": "Timezone test reminder",
        "daily_time": "09:00",
        "timezone": "America/New_York"
    }

    response = await api_client.post(
        f"/api/v1/users/{test_user}/reminders",
        json=reminder_data,
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert_valid_reminder(data)
    assert "timezone" in data["schedule"]


@pytest.mark.asyncio
async def test_list_reminders(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test listing all reminders for a user"""
    # Create a reminder first
    reminder_data = generate_daily_reminder()
    await api_client.post(
        f"/api/v1/users/{test_user}/reminders",
        json=reminder_data,
        headers=auth_headers
    )

    # List reminders
    response = await api_client.get(
        f"/api/v1/users/{test_user}/reminders",
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert_has_keys(data, ["reminders"])
    assert isinstance(data["reminders"], list)
    assert len(data["reminders"]) >= 1

    # Validate reminder structure
    for reminder in data["reminders"]:
        assert_valid_reminder(reminder)


@pytest.mark.asyncio
async def test_list_reminders_empty(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    unique_user_id: str,
    cleanup_user
):
    """Test listing reminders when user has none"""
    user_id = unique_user_id

    # Create user without reminders
    await api_client.post(
        "/api/v1/users",
        json={"user_id": user_id},
        headers=auth_headers
    )

    # List reminders
    response = await api_client.get(
        f"/api/v1/users/{user_id}/reminders",
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert "reminders" in data
    assert isinstance(data["reminders"], list)
    assert len(data["reminders"]) == 0

    # Cleanup
    await cleanup_user(user_id)


@pytest.mark.asyncio
async def test_get_reminder_status(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test checking reminder status"""
    # Create a reminder
    reminder_data = generate_daily_reminder()
    create_response = await api_client.post(
        f"/api/v1/users/{test_user}/reminders",
        json=reminder_data,
        headers=auth_headers
    )
    assert_success_response(create_response, 200)
    reminder = create_response.json()
    reminder_id = reminder["id"]

    # Get reminder status
    response = await api_client.get(
        f"/api/v1/users/{test_user}/reminders/{reminder_id}/status",
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert_has_keys(data, ["id", "triggered", "completed"])
    assert data["id"] == reminder_id


@pytest.mark.asyncio
async def test_get_reminder_status_not_found(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test getting status of non-existent reminder"""
    fake_reminder_id = "00000000-0000-0000-0000-000000000000"

    response = await api_client.get(
        f"/api/v1/users/{test_user}/reminders/{fake_reminder_id}/status",
        headers=auth_headers
    )

    assert_error_response(response, 404)


@pytest.mark.asyncio
async def test_create_reminder_invalid_type(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test creating reminder with invalid type"""
    reminder_data = {
        "type": "invalid_type",
        "message": "Test reminder",
        "daily_time": "18:00"
    }

    response = await api_client.post(
        f"/api/v1/users/{test_user}/reminders",
        json=reminder_data,
        headers=auth_headers
    )

    # Should return validation error
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_create_reminder_missing_time(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test creating reminder without required time configuration"""
    # Daily reminder without daily_time
    reminder_data = {
        "type": "daily",
        "message": "Test reminder"
    }

    response = await api_client.post(
        f"/api/v1/users/{test_user}/reminders",
        json=reminder_data,
        headers=auth_headers
    )

    assert_error_response(response, 400)


@pytest.mark.asyncio
async def test_reminder_user_mismatch(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_users
):
    """Test that user cannot access another user's reminders"""
    user1, user2 = test_users[0], test_users[1]

    # Create reminder for user1
    reminder_data = generate_daily_reminder()
    create_response = await api_client.post(
        f"/api/v1/users/{user1}/reminders",
        json=reminder_data,
        headers=auth_headers
    )
    assert_success_response(create_response, 200)
    reminder = create_response.json()
    reminder_id = reminder["id"]

    # Try to access reminder status as user2
    response = await api_client.get(
        f"/api/v1/users/{user2}/reminders/{reminder_id}/status",
        headers=auth_headers
    )

    # Should return 404 (reminder not found for this user)
    assert_error_response(response, 404)


@pytest.mark.asyncio
async def test_reminders_without_auth(
    api_client: httpx.AsyncClient,
    test_user: str
):
    """Test that reminder endpoints require authentication"""
    # Test create
    create_response = await api_client.post(
        f"/api/v1/users/{test_user}/reminders",
        json=generate_daily_reminder()
    )
    assert_error_response(create_response, 403)

    # Test list
    list_response = await api_client.get(
        f"/api/v1/users/{test_user}/reminders"
    )
    assert_error_response(list_response, 403)


@pytest.mark.asyncio
async def test_reminders_nonexistent_user(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str]
):
    """Test reminder operations with non-existent user"""
    response = await api_client.post(
        "/api/v1/users/nonexistent_user_xyz/reminders",
        json=generate_daily_reminder(),
        headers=auth_headers
    )

    assert_error_response(response, 404)
