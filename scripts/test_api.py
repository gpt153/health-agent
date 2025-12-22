#!/usr/bin/env python3
"""
Manual API testing script

Usage: python scripts/test_api.py
"""
import asyncio
import httpx
from datetime import datetime


API_BASE = "http://localhost:8080"
API_KEY = "test_key_123"  # Change this to your actual API key


async def test_health_check():
    """Test health check endpoint"""
    print("\n=== Testing Health Check ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/api/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")


async def test_chat():
    """Test chat endpoint"""
    print("\n=== Testing Chat ===")
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}

        response = await client.post(
            f"{API_BASE}/api/v1/chat",
            json={
                "user_id": "manual_test_001",
                "message": "Hello! What's the weather like?"
            },
            headers=headers
        )

        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Agent response: {data['response']}")
        else:
            print(f"Error: {response.text}")


async def test_user_management():
    """Test user creation and profile"""
    print("\n=== Testing User Management ===")
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        user_id = f"test_user_{int(datetime.now().timestamp())}"

        # Create user
        print(f"\n1. Creating user: {user_id}")
        response = await client.post(
            f"{API_BASE}/api/v1/users",
            json={
                "user_id": user_id,
                "profile": {
                    "age": 30,
                    "height_cm": 180,
                    "weight_kg": 75
                }
            },
            headers=headers
        )
        print(f"Status: {response.status_code}")

        # Get user profile
        print(f"\n2. Getting user profile")
        response = await client.get(
            f"{API_BASE}/api/v1/users/{user_id}",
            headers=headers
        )
        print(f"Profile: {response.json()}")

        # Update profile
        print(f"\n3. Updating profile")
        response = await client.patch(
            f"{API_BASE}/api/v1/users/{user_id}/profile",
            json={"field": "weight_kg", "value": "76"},
            headers=headers
        )
        print(f"Update result: {response.json()}")

        # Delete user (cleanup)
        print(f"\n4. Cleaning up - deleting user")
        response = await client.delete(
            f"{API_BASE}/api/v1/users/{user_id}",
            headers=headers
        )
        print(f"Deleted: {response.status_code == 204}")


async def test_memory_retention():
    """Test memory retention after clearing conversation"""
    print("\n=== Testing Memory Retention ===")
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        user_id = f"memory_test_{int(datetime.now().timestamp())}"

        # Create user
        print(f"\n1. Creating user: {user_id}")
        await client.post(
            f"{API_BASE}/api/v1/users",
            json={
                "user_id": user_id,
                "profile": {"age": 25}
            },
            headers=headers
        )

        # Tell agent something important
        print(f"\n2. Telling agent: 'I love pizza and my goal is to lose 5kg'")
        response = await client.post(
            f"{API_BASE}/api/v1/chat",
            json={
                "user_id": user_id,
                "message": "I love pizza and my goal is to lose 5kg"
            },
            headers=headers
        )
        print(f"Agent: {response.json()['response'][:100]}...")

        # Clear conversation
        print(f"\n3. Clearing conversation history")
        await client.delete(
            f"{API_BASE}/api/v1/users/{user_id}/conversation",
            headers=headers
        )
        print("Conversation cleared")

        # Ask agent to recall
        print(f"\n4. Asking: 'What's my favorite food and my goal?'")
        response = await client.post(
            f"{API_BASE}/api/v1/chat",
            json={
                "user_id": user_id,
                "message": "What's my favorite food and my goal?"
            },
            headers=headers
        )
        recall = response.json()['response']
        print(f"Agent recall: {recall}")

        # Verify
        if "pizza" in recall.lower() and ("5" in recall or "5kg" in recall.lower()):
            print("\n✅ SUCCESS: Agent remembered after /clear!")
        else:
            print("\n❌ FAILED: Agent did not remember")

        # Cleanup
        await client.delete(f"{API_BASE}/api/v1/users/{user_id}", headers=headers)


async def test_reminders():
    """Test reminder creation and listing"""
    print("\n=== Testing Reminders ===")
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        user_id = f"reminder_test_{int(datetime.now().timestamp())}"

        # Create user
        print(f"\n1. Creating user: {user_id}")
        await client.post(
            f"{API_BASE}/api/v1/users",
            json={"user_id": user_id},
            headers=headers
        )

        # Create daily reminder
        print(f"\n2. Creating daily reminder at 09:00")
        response = await client.post(
            f"{API_BASE}/api/v1/users/{user_id}/reminders",
            json={
                "type": "daily",
                "message": "Take vitamin D",
                "daily_time": "09:00",
                "timezone": "UTC"
            },
            headers=headers
        )
        reminder_data = response.json()
        print(f"Created reminder: {reminder_data['id']}")

        # List reminders
        print(f"\n3. Listing all reminders")
        response = await client.get(
            f"{API_BASE}/api/v1/users/{user_id}/reminders",
            headers=headers
        )
        reminders = response.json()["reminders"]
        print(f"Found {len(reminders)} reminder(s)")
        for r in reminders:
            print(f"  - {r['message']} at {r['schedule'].get('time')}")

        # Cleanup
        await client.delete(f"{API_BASE}/api/v1/users/{user_id}", headers=headers)


async def test_gamification():
    """Test XP, streaks, and achievements"""
    print("\n=== Testing Gamification ===")
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        user_id = f"gam_test_{int(datetime.now().timestamp())}"

        # Create user
        print(f"\n1. Creating user: {user_id}")
        await client.post(
            f"{API_BASE}/api/v1/users",
            json={"user_id": user_id},
            headers=headers
        )

        # Get XP
        print(f"\n2. Getting XP status")
        response = await client.get(
            f"{API_BASE}/api/v1/users/{user_id}/xp",
            headers=headers
        )
        xp_data = response.json()
        print(f"XP: {xp_data['xp']}, Level: {xp_data['level']}, Tier: {xp_data['tier']}")

        # Get streaks
        print(f"\n3. Getting streaks")
        response = await client.get(
            f"{API_BASE}/api/v1/users/{user_id}/streaks",
            headers=headers
        )
        streaks = response.json()["streaks"]
        print(f"Active streaks: {len(streaks)}")

        # Get achievements
        print(f"\n4. Getting achievements")
        response = await client.get(
            f"{API_BASE}/api/v1/users/{user_id}/achievements",
            headers=headers
        )
        achievements = response.json()
        print(f"Unlocked: {len(achievements['unlocked'])}, Locked: {len(achievements['locked'])}")

        # Cleanup
        await client.delete(f"{API_BASE}/api/v1/users/{user_id}", headers=headers)


async def main():
    """Run all tests"""
    print("=" * 60)
    print("HEALTH AGENT API - MANUAL TEST SUITE")
    print("=" * 60)

    try:
        await test_health_check()
        await test_chat()
        await test_user_management()
        await test_memory_retention()
        await test_reminders()
        await test_gamification()

        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
