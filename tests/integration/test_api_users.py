"""Integration tests for user profile API endpoints"""
import pytest
import httpx
from typing import Dict
from tests.integration.api_helpers import (
    assert_success_response,
    assert_error_response,
    assert_has_keys,
    assert_valid_user_profile,
    generate_test_profile
)


@pytest.mark.asyncio
async def test_create_user(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    unique_user_id: str,
    cleanup_user
):
    """Test user creation"""
    user_id = unique_user_id

    response = await api_client.post(
        "/api/v1/users",
        json={"user_id": user_id},
        headers=auth_headers
    )

    assert_success_response(response, 201)
    data = response.json()
    assert data["user_id"] == user_id
    assert data["created"] is True

    # Cleanup
    await cleanup_user(user_id)


@pytest.mark.asyncio
async def test_create_duplicate_user(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test creating duplicate user returns error"""
    response = await api_client.post(
        "/api/v1/users",
        json={"user_id": test_user},
        headers=auth_headers
    )

    assert_error_response(response, 400)


@pytest.mark.asyncio
async def test_get_user(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test retrieve user profile and preferences"""
    response = await api_client.get(
        f"/api/v1/users/{test_user}",
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert_has_keys(data, ["user_id", "profile"])
    assert data["user_id"] == test_user
    assert_valid_user_profile(data["profile"])


@pytest.mark.asyncio
async def test_get_nonexistent_user(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str]
):
    """Test retrieving non-existent user returns 404"""
    response = await api_client.get(
        "/api/v1/users/nonexistent_user_xyz",
        headers=auth_headers
    )

    assert_error_response(response, 404)


@pytest.mark.asyncio
async def test_delete_user(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    unique_user_id: str
):
    """Test user deletion"""
    user_id = unique_user_id

    # Create user
    create_response = await api_client.post(
        "/api/v1/users",
        json={"user_id": user_id},
        headers=auth_headers
    )
    assert_success_response(create_response, 201)

    # Delete user
    delete_response = await api_client.delete(
        f"/api/v1/users/{user_id}",
        headers=auth_headers
    )
    assert delete_response.status_code == 204

    # Verify user is deleted
    get_response = await api_client.get(
        f"/api/v1/users/{user_id}",
        headers=auth_headers
    )
    assert_error_response(get_response, 404)


@pytest.mark.asyncio
async def test_delete_nonexistent_user(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str]
):
    """Test deleting non-existent user returns 404"""
    response = await api_client.delete(
        "/api/v1/users/nonexistent_user_xyz",
        headers=auth_headers
    )

    assert_error_response(response, 404)


@pytest.mark.asyncio
async def test_get_user_profile(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test get user profile endpoint"""
    response = await api_client.get(
        f"/api/v1/users/{test_user}/profile",
        headers=auth_headers
    )

    assert_success_response(response, 200)
    profile = response.json()
    assert_valid_user_profile(profile)


@pytest.mark.asyncio
async def test_update_profile_field(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test updating a single profile field"""
    response = await api_client.patch(
        f"/api/v1/users/{test_user}/profile",
        json={
            "field": "name",
            "value": "John Doe"
        },
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert data["success"] is True
    assert data["field"] == "name"
    assert data["value"] == "John Doe"

    # Verify update persisted
    profile_response = await api_client.get(
        f"/api/v1/users/{test_user}/profile",
        headers=auth_headers
    )
    assert_success_response(profile_response, 200)
    profile = profile_response.json()
    assert "John Doe" in str(profile.values())


@pytest.mark.asyncio
async def test_update_multiple_profile_fields(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test updating multiple profile fields"""
    fields = [
        ("name", "Alice Smith"),
        ("age", "28"),
        ("goal_type", "lose_weight")
    ]

    for field, value in fields:
        response = await api_client.patch(
            f"/api/v1/users/{test_user}/profile",
            json={"field": field, "value": value},
            headers=auth_headers
        )
        assert_success_response(response, 200)

    # Verify all updates persisted
    profile_response = await api_client.get(
        f"/api/v1/users/{test_user}/profile",
        headers=auth_headers
    )
    assert_success_response(profile_response, 200)
    profile = profile_response.json()
    profile_str = str(profile.values())
    assert "Alice Smith" in profile_str
    assert "28" in profile_str
    assert "lose_weight" in profile_str


@pytest.mark.asyncio
async def test_get_user_preferences(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test get user preferences"""
    response = await api_client.get(
        f"/api/v1/users/{test_user}/preferences",
        headers=auth_headers
    )

    assert_success_response(response, 200)
    preferences = response.json()
    assert isinstance(preferences, dict)


@pytest.mark.asyncio
async def test_update_preferences(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test updating user preferences"""
    response = await api_client.patch(
        f"/api/v1/users/{test_user}/preferences",
        json={
            "preference": "brevity",
            "value": "detailed"
        },
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert data["success"] is True
    assert data["preference"] == "brevity"
    assert data["value"] == "detailed"

    # Verify update persisted
    prefs_response = await api_client.get(
        f"/api/v1/users/{test_user}/preferences",
        headers=auth_headers
    )
    assert_success_response(prefs_response, 200)


@pytest.mark.asyncio
async def test_clear_conversation(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test clearing conversation history"""
    # First send some messages
    await api_client.post(
        "/api/v1/chat",
        json={
            "user_id": test_user,
            "message": "Hello",
            "message_history": []
        },
        headers=auth_headers
    )

    # Clear conversation
    response = await api_client.delete(
        f"/api/v1/users/{test_user}/conversation",
        headers=auth_headers
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_user_without_auth(
    api_client: httpx.AsyncClient,
    test_user: str
):
    """Test that user endpoints require authentication"""
    # Test GET user
    response = await api_client.get(f"/api/v1/users/{test_user}")
    assert_error_response(response, 403)

    # Test POST user
    response = await api_client.post(
        "/api/v1/users",
        json={"user_id": "new_user"}
    )
    assert_error_response(response, 403)


@pytest.mark.asyncio
async def test_profile_persistence(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    unique_user_id: str,
    cleanup_user
):
    """Test that profile data persists across requests"""
    user_id = unique_user_id

    # Create user
    await api_client.post(
        "/api/v1/users",
        json={"user_id": user_id},
        headers=auth_headers
    )

    # Update profile
    await api_client.patch(
        f"/api/v1/users/{user_id}/profile",
        json={"field": "name", "value": "Persistent User"},
        headers=auth_headers
    )

    # Retrieve profile multiple times
    for _ in range(3):
        response = await api_client.get(
            f"/api/v1/users/{user_id}/profile",
            headers=auth_headers
        )
        assert_success_response(response, 200)
        profile = response.json()
        assert "Persistent User" in str(profile.values())

    # Cleanup
    await cleanup_user(user_id)
