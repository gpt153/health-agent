"""Tests for memory retention (profile, preferences, conversation clearing)"""
import pytest
import httpx


@pytest.mark.asyncio
async def test_memory_retention_after_clear():
    """
    Test that agent remembers profile info after clearing conversation

    This is the critical test case from issue #22:
    1. Create user
    2. Send message with info
    3. Clear conversation
    4. Query info - should recall from DB/memory
    """
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        headers = {"Authorization": "Bearer test_key_123"}
        user_id = "memory_test_user"

        # 1. Create test user
        response = await client.post(
            "/api/v1/users",
            json={
                "user_id": user_id,
                "profile": {"age": 30, "weight_kg": 75}
            },
            headers=headers
        )
        assert response.status_code == 201

        # 2. Tell agent some info
        response = await client.post(
            "/api/v1/chat",
            json={
                "user_id": user_id,
                "message": "I love pizza and my goal is to lose 5kg"
            },
            headers=headers
        )
        assert response.status_code == 200
        first_response = response.json()["response"]
        print(f"Agent initial response: {first_response}")

        # 3. Clear conversation
        response = await client.delete(
            f"/api/v1/users/{user_id}/conversation",
            headers=headers
        )
        assert response.status_code == 204

        # 4. Ask agent to recall
        response = await client.post(
            "/api/v1/chat",
            json={
                "user_id": user_id,
                "message": "What's my favorite food and my goal?"
            },
            headers=headers
        )
        assert response.status_code == 200
        recall_response = response.json()["response"]
        print(f"Agent recall response: {recall_response}")

        # Verify agent remembered from persistent memory
        assert "pizza" in recall_response.lower(), "Agent should remember favorite food"
        assert "5" in recall_response and "kg" in recall_response.lower(), "Agent should remember goal"

        # Cleanup
        await client.delete(f"/api/v1/users/{user_id}", headers=headers)


@pytest.mark.asyncio
async def test_profile_updates_persist():
    """Test that profile updates are saved and persist"""
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        headers = {"Authorization": "Bearer test_key_123"}
        user_id = "profile_test_user"

        # Create user
        await client.post(
            "/api/v1/users",
            json={"user_id": user_id},
            headers=headers
        )

        # Update profile
        await client.patch(
            f"/api/v1/users/{user_id}/profile",
            json={"field": "weight_kg", "value": "80"},
            headers=headers
        )

        # Verify profile was updated
        response = await client.get(
            f"/api/v1/users/{user_id}/profile",
            headers=headers
        )
        assert response.status_code == 200
        profile = response.json()
        assert profile.get("weight_kg") == "80"

        # Cleanup
        await client.delete(f"/api/v1/users/{user_id}", headers=headers)


@pytest.mark.asyncio
async def test_preferences_persist():
    """Test that preference changes persist"""
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        headers = {"Authorization": "Bearer test_key_123"}
        user_id = "prefs_test_user"

        # Create user
        await client.post(
            "/api/v1/users",
            json={"user_id": user_id},
            headers=headers
        )

        # Update preferences
        await client.patch(
            f"/api/v1/users/{user_id}/preferences",
            json={"preference": "tone", "value": "casual"},
            headers=headers
        )

        # Verify preferences were updated
        response = await client.get(
            f"/api/v1/users/{user_id}/preferences",
            headers=headers
        )
        assert response.status_code == 200
        prefs = response.json()
        assert prefs.get("tone") == "casual"

        # Cleanup
        await client.delete(f"/api/v1/users/{user_id}", headers=headers)
