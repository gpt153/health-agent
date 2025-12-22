"""Tests for reminder functionality"""
import pytest
import httpx
import asyncio
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_create_daily_reminder():
    """Test creating a daily reminder"""
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        headers = {"Authorization": "Bearer test_key_123"}
        user_id = "reminder_test_user"

        # Create user
        await client.post(
            "/api/v1/users",
            json={"user_id": user_id},
            headers=headers
        )

        # Create daily reminder
        response = await client.post(
            f"/api/v1/users/{user_id}/reminders",
            json={
                "type": "daily",
                "message": "Take medication",
                "daily_time": "09:00",
                "timezone": "UTC"
            },
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "daily"
        assert data["message"] == "Take medication"
        assert data["active"] is True

        # Verify reminder was saved
        response = await client.get(
            f"/api/v1/users/{user_id}/reminders",
            headers=headers
        )
        assert response.status_code == 200
        reminders = response.json()["reminders"]
        assert len(reminders) > 0

        # Cleanup
        await client.delete(f"/api/v1/users/{user_id}", headers=headers)


@pytest.mark.asyncio
async def test_create_one_time_reminder():
    """Test creating a one-time reminder"""
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        headers = {"Authorization": "Bearer test_key_123"}
        user_id = "onetime_test_user"

        # Create user
        await client.post(
            "/api/v1/users",
            json={"user_id": user_id},
            headers=headers
        )

        # Create one-time reminder 2 minutes from now
        trigger_time = (datetime.now() + timedelta(minutes=2)).isoformat()

        response = await client.post(
            f"/api/v1/users/{user_id}/reminders",
            json={
                "type": "one_time",
                "message": "Check something",
                "trigger_time": trigger_time,
                "timezone": "UTC"
            },
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        reminder_id = data["id"]

        # Check status immediately (should not be triggered yet)
        response = await client.get(
            f"/api/v1/users/{user_id}/reminders/{reminder_id}/status",
            headers=headers
        )
        assert response.status_code == 200
        status = response.json()
        assert status["triggered"] is False

        # Cleanup
        await client.delete(f"/api/v1/users/{user_id}", headers=headers)


@pytest.mark.asyncio
async def test_list_reminders():
    """Test listing user reminders"""
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        headers = {"Authorization": "Bearer test_key_123"}
        user_id = "list_reminders_user"

        # Create user
        await client.post(
            "/api/v1/users",
            json={"user_id": user_id},
            headers=headers
        )

        # Create multiple reminders
        for i in range(3):
            await client.post(
                f"/api/v1/users/{user_id}/reminders",
                json={
                    "type": "daily",
                    "message": f"Reminder {i+1}",
                    "daily_time": f"{8+i}:00",
                    "timezone": "UTC"
                },
                headers=headers
            )

        # List reminders
        response = await client.get(
            f"/api/v1/users/{user_id}/reminders",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["reminders"]) == 3

        # Cleanup
        await client.delete(f"/api/v1/users/{user_id}", headers=headers)
