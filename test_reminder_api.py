#!/usr/bin/env python3
"""Test script for reminder API endpoints"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8080"
API_KEY = "test_key_123"
USER_ID = "test_user_api"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def test_health_check():
    """Test health endpoint"""
    print("\n=== Testing Health Check ===")
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_create_user():
    """Create test user"""
    print("\n=== Creating Test User ===")
    response = requests.post(
        f"{BASE_URL}/api/v1/users",
        headers=headers,
        json={"user_id": USER_ID}
    )
    print(f"Status: {response.status_code}")
    if response.status_code in [200, 201, 409]:  # 409 = already exists
        print("User created or already exists")
        return True
    print(f"Error: {response.text}")
    return False

def test_list_reminders():
    """List all reminders"""
    print("\n=== Listing Reminders ===")
    response = requests.get(
        f"{BASE_URL}/api/v1/users/{USER_ID}/reminders",
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Found {len(data.get('reminders', []))} reminders")
        for r in data.get('reminders', []):
            print(f"  - [{r['id'][:8]}...] {r['message']} @ {r['time']}")
        return data
    print(f"Error: {response.text}")
    return None

def test_create_reminder():
    """Create a new reminder"""
    print("\n=== Creating New Reminder ===")
    reminder_data = {
        "type": "daily",
        "time": "14:30",
        "message": "Test API Reminder - Take afternoon break",
        "timezone": "UTC",
        "days": [0, 1, 2, 3, 4]  # Weekdays only
    }
    print(f"Creating reminder: {json.dumps(reminder_data, indent=2)}")

    response = requests.post(
        f"{BASE_URL}/api/v1/users/{USER_ID}/reminders",
        headers=headers,
        json=reminder_data
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Created reminder: {data['id']}")
        print(f"Message: {data['message']}")
        print(f"Time: {data['time']} {data['timezone']}")
        return data
    print(f"Error: {response.text}")
    return None

def test_reminder_status(reminder_id):
    """Check reminder status"""
    print(f"\n=== Checking Reminder Status: {reminder_id[:8]}... ===")
    response = requests.get(
        f"{BASE_URL}/api/v1/users/{USER_ID}/reminders/{reminder_id}/status",
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Active: {data.get('active', False)}")
        print(f"Completed today: {data.get('completed_today', False)}")
        return data
    print(f"Error: {response.text}")
    return None

def main():
    """Run all tests"""
    print("=" * 80)
    print("REMINDER API TEST SUITE")
    print("=" * 80)

    # Test 1: Health check
    if not test_health_check():
        print("\n❌ Health check failed - is the API running?")
        return

    # Test 2: Create user
    if not test_create_user():
        print("\n❌ Failed to create user")
        return

    # Test 3: List existing reminders
    existing = test_list_reminders()

    # Test 4: Create new reminder
    new_reminder = test_create_reminder()
    if not new_reminder:
        print("\n❌ Failed to create reminder")
        return

    # Test 5: List reminders again to verify
    print("\n=== Verifying Reminder Was Created ===")
    updated = test_list_reminders()

    # Test 6: Check reminder status
    if new_reminder:
        test_reminder_status(new_reminder['id'])

    print("\n" + "=" * 80)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 80)
    print("\nNOTE: The reminder management features (delete, update, cleanup)")
    print("are available through the chat agent. To test those:")
    print("1. Use the /api/v1/chat endpoint")
    print("2. Send messages like:")
    print("   - 'Delete my test reminder'")
    print("   - 'Change my reminder to 3pm'")
    print("   - 'Clean up duplicate reminders'")
    print("=" * 80)

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to API. Make sure the server is running on http://localhost:8080")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
