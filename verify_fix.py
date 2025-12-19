#!/usr/bin/env python3
"""
Verification script for issue #12 fix
Tests the is_admin function in isolation
"""

# Inline version of the fixed is_admin function for verification
def is_admin(telegram_id: str) -> bool:
    """
    Check if user is admin

    Normalizes input to handle type variations (int/str) and whitespace.
    This ensures consistent admin checks regardless of how telegram_id is passed.
    """
    ADMIN_USER_ID = "7376426503"

    # Handle None case explicitly
    if telegram_id is None:
        print(f"  DEBUG: telegram_id is None, returning False")
        return False

    # Normalize input: convert to string and strip whitespace
    normalized_id = str(telegram_id).strip()
    result = normalized_id == ADMIN_USER_ID

    # Debug logging to help diagnose admin check issues
    print(
        f"  DEBUG: input='{telegram_id}' (type: {type(telegram_id).__name__}), "
        f"normalized='{normalized_id}', result={result}"
    )

    return result


def test_is_admin():
    """Run test cases for is_admin function"""
    print("=" * 60)
    print("Testing is_admin function (Issue #12 Fix Verification)")
    print("=" * 60)

    test_cases = [
        ("String admin ID", "7376426503", True),
        ("Integer admin ID", 7376426503, True),
        ("Admin ID with leading whitespace", " 7376426503", True),
        ("Admin ID with trailing whitespace", "7376426503 ", True),
        ("Admin ID with both whitespace", " 7376426503 ", True),
        ("Admin ID with tab/newline", "\t7376426503\n", True),
        ("Non-admin string", "12345", False),
        ("Non-admin integer", 12345, False),
        ("Empty string", "", False),
        ("Whitespace only", "   ", False),
        ("None value", None, False),
        ("Wrong admin ID", "7376426504", False),
    ]

    passed = 0
    failed = 0

    for test_name, input_val, expected in test_cases:
        print(f"\nTest: {test_name}")
        result = is_admin(input_val)

        if result == expected:
            print(f"  ✓ PASS (expected {expected}, got {result})")
            passed += 1
        else:
            print(f"  ✗ FAIL (expected {expected}, got {result})")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("✓ All tests passed! Fix verified successfully.")
        return True
    else:
        print("✗ Some tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = test_is_admin()
    exit(0 if success else 1)
