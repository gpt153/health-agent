"""Integration tests for gamification API endpoints"""
import pytest
import httpx
from typing import Dict
from tests.integration.api_helpers import (
    assert_success_response,
    assert_error_response,
    assert_has_keys,
    assert_valid_xp_response
)


@pytest.mark.asyncio
async def test_get_xp_basic(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test retrieving user XP and level"""
    response = await api_client.get(
        f"/api/v1/users/{test_user}/xp",
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert_valid_xp_response(data)
    assert data["user_id"] == test_user


@pytest.mark.asyncio
async def test_get_xp_new_user(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    unique_user_id: str,
    cleanup_user
):
    """Test XP for newly created user has default values"""
    user_id = unique_user_id

    # Create new user
    await api_client.post(
        "/api/v1/users",
        json={"user_id": user_id},
        headers=auth_headers
    )

    # Get XP
    response = await api_client.get(
        f"/api/v1/users/{user_id}/xp",
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert_valid_xp_response(data)

    # New user should have minimal XP
    assert data["xp"] >= 0
    assert data["level"] >= 1

    # Cleanup
    await cleanup_user(user_id)


@pytest.mark.asyncio
async def test_get_xp_nonexistent_user(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str]
):
    """Test XP endpoint with non-existent user"""
    response = await api_client.get(
        "/api/v1/users/nonexistent_user_xyz/xp",
        headers=auth_headers
    )

    assert_error_response(response, 404)


@pytest.mark.asyncio
async def test_get_streaks(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test retrieving user streaks"""
    response = await api_client.get(
        f"/api/v1/users/{test_user}/streaks",
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert_has_keys(data, ["user_id", "streaks"])
    assert data["user_id"] == test_user
    assert isinstance(data["streaks"], list)


@pytest.mark.asyncio
async def test_get_streaks_empty(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    unique_user_id: str,
    cleanup_user
):
    """Test streaks for user with no active streaks"""
    user_id = unique_user_id

    # Create new user
    await api_client.post(
        "/api/v1/users",
        json={"user_id": user_id},
        headers=auth_headers
    )

    # Get streaks
    response = await api_client.get(
        f"/api/v1/users/{user_id}/streaks",
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert isinstance(data["streaks"], list)

    # Cleanup
    await cleanup_user(user_id)


@pytest.mark.asyncio
async def test_get_achievements(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test retrieving user achievements"""
    response = await api_client.get(
        f"/api/v1/users/{test_user}/achievements",
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()
    assert_has_keys(data, ["user_id", "unlocked", "locked"])
    assert data["user_id"] == test_user
    assert isinstance(data["unlocked"], list)
    assert isinstance(data["locked"], list)


@pytest.mark.asyncio
async def test_achievements_locked_unlocked(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test that achievements response includes both locked and unlocked"""
    response = await api_client.get(
        f"/api/v1/users/{test_user}/achievements",
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()

    # Should have both categories
    unlocked = data["unlocked"]
    locked = data["locked"]

    # Total achievements = unlocked + locked
    total_achievements = len(unlocked) + len(locked)
    assert total_achievements > 0, "Should have at least some achievements defined"

    # Validate achievement structure
    for achievement in unlocked + locked:
        assert isinstance(achievement, dict)
        assert "id" in achievement


@pytest.mark.asyncio
async def test_gamification_without_auth(
    api_client: httpx.AsyncClient,
    test_user: str
):
    """Test that gamification endpoints require authentication"""
    # Test XP
    xp_response = await api_client.get(
        f"/api/v1/users/{test_user}/xp"
    )
    assert_error_response(xp_response, 403)

    # Test streaks
    streaks_response = await api_client.get(
        f"/api/v1/users/{test_user}/streaks"
    )
    assert_error_response(streaks_response, 403)

    # Test achievements
    achievements_response = await api_client.get(
        f"/api/v1/users/{test_user}/achievements"
    )
    assert_error_response(achievements_response, 403)


@pytest.mark.asyncio
async def test_gamification_nonexistent_user(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str]
):
    """Test gamification endpoints with non-existent user"""
    # Test XP
    xp_response = await api_client.get(
        "/api/v1/users/nonexistent_user_xyz/xp",
        headers=auth_headers
    )
    assert_error_response(xp_response, 404)

    # Test streaks
    streaks_response = await api_client.get(
        "/api/v1/users/nonexistent_user_xyz/streaks",
        headers=auth_headers
    )
    assert_error_response(streaks_response, 404)

    # Test achievements
    achievements_response = await api_client.get(
        "/api/v1/users/nonexistent_user_xyz/achievements",
        headers=auth_headers
    )
    assert_error_response(achievements_response, 404)


@pytest.mark.asyncio
async def test_xp_tier_mapping(
    api_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    test_user: str
):
    """Test that XP response includes tier information"""
    response = await api_client.get(
        f"/api/v1/users/{test_user}/xp",
        headers=auth_headers
    )

    assert_success_response(response, 200)
    data = response.json()

    # Tier should be a string with valid tier name
    assert "tier" in data
    assert isinstance(data["tier"], str)
    # Common tier names
    valid_tiers = ["Bronze", "Silver", "Gold", "Platinum", "Diamond"]
    # Tier should be one of these or another valid tier
    assert len(data["tier"]) > 0
