"""Tests for gamification endpoints (XP, streaks, achievements)"""
import pytest
import httpx


@pytest.mark.asyncio
async def test_get_xp_status():
    """Test getting XP and level"""
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        headers = {"Authorization": "Bearer test_key_123"}
        user_id = "xp_test_user"

        # Create user
        await client.post(
            "/api/v1/users",
            json={"user_id": user_id},
            headers=headers
        )

        # Get XP status
        response = await client.get(
            f"/api/v1/users/{user_id}/xp",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "xp" in data
        assert "level" in data
        assert "tier" in data
        assert "xp_to_next_level" in data

        # Cleanup
        await client.delete(f"/api/v1/users/{user_id}", headers=headers)


@pytest.mark.asyncio
async def test_get_streaks():
    """Test getting user streaks"""
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        headers = {"Authorization": "Bearer test_key_123"}
        user_id = "streak_test_user"

        # Create user
        await client.post(
            "/api/v1/users",
            json={"user_id": user_id},
            headers=headers
        )

        # Get streaks
        response = await client.get(
            f"/api/v1/users/{user_id}/streaks",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "streaks" in data
        assert isinstance(data["streaks"], list)

        # Cleanup
        await client.delete(f"/api/v1/users/{user_id}", headers=headers)


@pytest.mark.asyncio
async def test_get_achievements():
    """Test getting user achievements"""
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        headers = {"Authorization": "Bearer test_key_123"}
        user_id = "achievement_test_user"

        # Create user
        await client.post(
            "/api/v1/users",
            json={"user_id": user_id},
            headers=headers
        )

        # Get achievements
        response = await client.get(
            f"/api/v1/users/{user_id}/achievements",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "unlocked" in data
        assert "locked" in data
        assert isinstance(data["unlocked"], list)
        assert isinstance(data["locked"], list)

        # Cleanup
        await client.delete(f"/api/v1/users/{user_id}", headers=headers)


@pytest.mark.asyncio
async def test_food_logging_grants_xp():
    """Test that logging food gives XP"""
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        headers = {"Authorization": "Bearer test_key_123"}
        user_id = "food_xp_test_user"

        # Create user
        await client.post(
            "/api/v1/users",
            json={"user_id": user_id},
            headers=headers
        )

        # Get initial XP
        response = await client.get(
            f"/api/v1/users/{user_id}/xp",
            headers=headers
        )
        initial_xp = response.json()["xp"]

        # Log food
        await client.post(
            f"/api/v1/users/{user_id}/food",
            json={
                "description": "Chicken breast with rice"
            },
            headers=headers
        )

        # Get XP after logging food
        response = await client.get(
            f"/api/v1/users/{user_id}/xp",
            headers=headers
        )
        new_xp = response.json()["xp"]

        # XP should have increased
        assert new_xp > initial_xp, "Food logging should grant XP"

        # Cleanup
        await client.delete(f"/api/v1/users/{user_id}", headers=headers)
