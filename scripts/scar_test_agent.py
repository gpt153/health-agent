#!/usr/bin/env python3
"""
SCAR (System Coding Agent Remote) testing script

This script performs comprehensive API testing for SCAR integration.

Usage: python scripts/scar_test_agent.py
"""
import asyncio
import httpx
from datetime import datetime, timedelta
import json


API_BASE = "http://localhost:8080"
API_KEY = "scar_key_456"  # SCAR's API key


class Colors:
    """Terminal colors"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_test(name: str):
    """Print test header"""
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}[TEST] {name}{Colors.ENDC}")


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}✅ {message}{Colors.ENDC}")


def print_failure(message: str):
    """Print failure message"""
    print(f"{Colors.FAIL}❌ {message}{Colors.ENDC}")


def print_info(message: str):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ️  {message}{Colors.ENDC}")


async def test_memory_retention():
    """
    Critical test from issue #22:
    Test that agent remembers info after /clear
    """
    print_test("Memory Retention After /clear")

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        user_id = "scar_test_001"

        try:
            # 1. Create test user
            print_info("Step 1: Creating test user")
            response = await client.post(
                f"{API_BASE}/api/v1/users",
                json={
                    "user_id": user_id,
                    "profile": {"age": 30, "weight_kg": 75}
                },
                headers=headers
            )
            if response.status_code != 201:
                # User might already exist
                print_info(f"User exists, continuing...")

            # 2. Tell agent some info
            print_info("Step 2: Telling agent important information")
            resp = await client.post(
                f"{API_BASE}/api/v1/chat",
                json={
                    "user_id": user_id,
                    "message": "I love pizza and my goal is to lose 5kg"
                },
                headers=headers
            )
            agent_response = resp.json()['response']
            print(f"Agent: {agent_response[:150]}...")

            # 3. Clear conversation
            print_info("Step 3: Clearing conversation history")
            await client.delete(
                f"{API_BASE}/api/v1/users/{user_id}/conversation",
                headers=headers
            )

            # 4. Ask agent to recall
            print_info("Step 4: Asking agent to recall information")
            resp = await client.post(
                f"{API_BASE}/api/v1/chat",
                json={
                    "user_id": user_id,
                    "message": "What's my favorite food and my goal?"
                },
                headers=headers
            )

            response_text = resp.json()['response']
            print(f"Agent recall: {response_text[:200]}...")

            # Verify
            has_pizza = "pizza" in response_text.lower()
            has_goal = "5" in response_text and ("kg" in response_text.lower() or "kilo" in response_text.lower())

            if has_pizza and has_goal:
                print_success("Memory retention test passed")
                return True
            else:
                print_failure(f"Memory retention test failed (pizza={has_pizza}, goal={has_goal})")
                return False

        except Exception as e:
            print_failure(f"Test failed with error: {e}")
            return False


async def test_food_logging_with_xp():
    """Test food logging and XP rewards"""
    print_test("Food Logging with XP")

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        user_id = "scar_test_002"

        try:
            # Create user
            print_info("Creating test user")
            await client.post(
                f"{API_BASE}/api/v1/users",
                json={"user_id": user_id},
                headers=headers
            )

            # Get initial XP
            resp = await client.get(
                f"{API_BASE}/api/v1/users/{user_id}/xp",
                headers=headers
            )
            initial_xp = resp.json()['xp']
            print_info(f"Initial XP: {initial_xp}")

            # Log food
            print_info("Logging food entry")
            await client.post(
                f"{API_BASE}/api/v1/users/{user_id}/food",
                json={"description": "Chicken breast with rice"},
                headers=headers
            )

            # Get new XP
            resp = await client.get(
                f"{API_BASE}/api/v1/users/{user_id}/xp",
                headers=headers
            )
            new_xp = resp.json()['xp']
            print_info(f"New XP: {new_xp}")

            xp_gained = new_xp - initial_xp

            if xp_gained > 0:
                print_success(f"XP test passed (gained {xp_gained} XP)")
                return True
            else:
                print_failure("No XP gained from food logging")
                return False

        except Exception as e:
            print_failure(f"Test failed with error: {e}")
            return False
        finally:
            # Cleanup
            await client.delete(f"{API_BASE}/api/v1/users/{user_id}", headers=headers)


async def test_reminder_scheduling():
    """Test reminder creation and scheduling"""
    print_test("Reminder Scheduling")

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        user_id = "scar_test_003"

        try:
            # Create user
            print_info("Creating test user")
            await client.post(
                f"{API_BASE}/api/v1/users",
                json={"user_id": user_id},
                headers=headers
            )

            # Create reminder
            print_info("Creating daily reminder at 09:00")
            resp = await client.post(
                f"{API_BASE}/api/v1/users/{user_id}/reminders",
                json={
                    "type": "daily",
                    "message": "Take vitamin D",
                    "daily_time": "09:00",
                    "timezone": "Europe/Stockholm"
                },
                headers=headers
            )

            reminder_id = resp.json()['id']
            print_info(f"Reminder created: {reminder_id}")

            # Verify reminder exists
            resp = await client.get(
                f"{API_BASE}/api/v1/users/{user_id}/reminders",
                headers=headers
            )

            reminders = resp.json()['reminders']

            if len(reminders) > 0:
                print_success(f"Reminder test passed ({len(reminders)} reminder(s) created)")
                return True
            else:
                print_failure("No reminders found")
                return False

        except Exception as e:
            print_failure(f"Test failed with error: {e}")
            return False
        finally:
            # Cleanup
            await client.delete(f"{API_BASE}/api/v1/users/{user_id}", headers=headers)


async def test_profile_updates_with_audit():
    """Test profile updates are logged"""
    print_test("Profile Updates with Audit Trail")

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        user_id = "scar_test_004"

        try:
            # Create user
            print_info("Creating test user")
            await client.post(
                f"{API_BASE}/api/v1/users",
                json={"user_id": user_id, "profile": {"weight_kg": 75}},
                headers=headers
            )

            # Update profile
            print_info("Updating weight: 75 -> 76")
            await client.patch(
                f"{API_BASE}/api/v1/users/{user_id}/profile",
                json={"field": "weight_kg", "value": "76"},
                headers=headers
            )

            # Verify update
            resp = await client.get(
                f"{API_BASE}/api/v1/users/{user_id}/profile",
                headers=headers
            )

            profile = resp.json()
            current_weight = profile.get("weight_kg")

            if current_weight == "76":
                print_success("Profile update test passed")
                return True
            else:
                print_failure(f"Profile update failed (weight={current_weight})")
                return False

        except Exception as e:
            print_failure(f"Test failed with error: {e}")
            return False
        finally:
            # Cleanup
            await client.delete(f"{API_BASE}/api/v1/users/{user_id}", headers=headers)


async def test_streak_tracking():
    """Test streak tracking"""
    print_test("Streak Tracking")

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        user_id = "scar_test_005"

        try:
            # Create user
            print_info("Creating test user")
            await client.post(
                f"{API_BASE}/api/v1/users",
                json={"user_id": user_id},
                headers=headers
            )

            # Get streaks
            resp = await client.get(
                f"{API_BASE}/api/v1/users/{user_id}/streaks",
                headers=headers
            )

            streaks = resp.json()['streaks']
            print_info(f"Active streaks: {len(streaks)}")

            print_success("Streak tracking test passed")
            return True

        except Exception as e:
            print_failure(f"Test failed with error: {e}")
            return False
        finally:
            # Cleanup
            await client.delete(f"{API_BASE}/api/v1/users/{user_id}", headers=headers)


async def test_conversation_clear():
    """Test conversation clearing doesn't affect memory"""
    print_test("Conversation Clear (Memory Isolation)")

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        user_id = "scar_test_006"

        try:
            # Create user
            await client.post(
                f"{API_BASE}/api/v1/users",
                json={"user_id": user_id},
                headers=headers
            )

            # Chat 1
            await client.post(
                f"{API_BASE}/api/v1/chat",
                json={
                    "user_id": user_id,
                    "message": "I'm training for a marathon"
                },
                headers=headers
            )

            # Clear
            await client.delete(
                f"{API_BASE}/api/v1/users/{user_id}/conversation",
                headers=headers
            )

            # Chat 2 - should still remember marathon goal
            resp = await client.post(
                f"{API_BASE}/api/v1/chat",
                json={
                    "user_id": user_id,
                    "message": "What am I training for?"
                },
                headers=headers
            )

            response_text = resp.json()['response']

            if "marathon" in response_text.lower():
                print_success("Conversation clear test passed")
                return True
            else:
                print_failure("Agent forgot info after clear")
                return False

        except Exception as e:
            print_failure(f"Test failed with error: {e}")
            return False
        finally:
            # Cleanup
            await client.delete(f"{API_BASE}/api/v1/users/{user_id}", headers=headers)


async def main():
    """Run all SCAR tests"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}")
    print("SCAR API TEST SUITE")
    print(f"{'=' * 60}{Colors.ENDC}\n")

    results = {}

    tests = [
        ("Memory Retention", test_memory_retention),
        ("Food Logging + XP", test_food_logging_with_xp),
        ("Reminder Scheduling", test_reminder_scheduling),
        ("Profile Updates", test_profile_updates_with_audit),
        ("Streak Tracking", test_streak_tracking),
        ("Conversation Clear", test_conversation_clear),
    ]

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print_failure(f"Test '{test_name}' crashed: {e}")
            results[test_name] = False

    # Summary
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}")
    print("TEST SUMMARY")
    print(f"{'=' * 60}{Colors.ENDC}\n")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = f"{Colors.OKGREEN}✅ PASS{Colors.ENDC}" if result else f"{Colors.FAIL}❌ FAIL{Colors.ENDC}"
        print(f"{test_name:.<40} {status}")

    print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed{Colors.ENDC}")

    if passed == total:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}🎉 ALL TESTS PASSED!{Colors.ENDC}")
    else:
        print(f"\n{Colors.WARNING}{Colors.BOLD}⚠️  Some tests failed{Colors.ENDC}")


if __name__ == "__main__":
    asyncio.run(main())
