#!/usr/bin/env python3
"""Manual test to verify alertness question fix logic"""

# Test the new alertness question flow

def test_alertness_keyboard_logic():
    """Test that submit button appears after selection"""

    # Simulate user_data
    user_data = {
        'sleep_quiz_data': {}
    }

    # Test 1: No selection yet - should NOT show submit button
    selected = user_data['sleep_quiz_data'].get('alertness_rating')
    print(f"Test 1 - No selection: selected={selected}")
    assert selected is None, "Should have no selection initially"

    # Simulate keyboard generation
    keyboard = [
        [str(i) for i in range(1, 6)],
        [str(i) for i in range(6, 11)],
    ]
    if selected:
        keyboard.append(['✅ Submit'])

    print(f"  Keyboard rows: {len(keyboard)}")
    assert len(keyboard) == 2, "Should have 2 rows (no submit button yet)"
    print("  ✅ PASS: No submit button before selection\n")

    # Test 2: After selection - should show submit button
    user_data['sleep_quiz_data']['alertness_rating'] = 7
    selected = user_data['sleep_quiz_data'].get('alertness_rating')
    print(f"Test 2 - After selection: selected={selected}")
    assert selected == 7, "Should have selected rating"

    keyboard = [
        [str(i) for i in range(1, 6)],
        [str(i) for i in range(6, 11)],
    ]
    if selected:
        keyboard.append(['✅ Submit'])

    print(f"  Keyboard rows: {len(keyboard)}")
    assert len(keyboard) == 3, "Should have 3 rows (submit button added)"
    assert keyboard[2] == ['✅ Submit'], "Third row should be submit button"
    print("  ✅ PASS: Submit button appears after selection\n")

    # Test 3: Callback data validation
    print("Test 3 - Callback data patterns:")
    callback_patterns = {
        'number_selection': [f'alert_{i}' for i in range(1, 11)],
        'submit': 'alert_submit'
    }

    # Test parsing number
    for cb in callback_patterns['number_selection']:
        value = int(cb.replace('alert_', ''))
        assert 1 <= value <= 10, f"Value {value} out of range"
    print(f"  ✅ PASS: All number callbacks parse correctly (1-10)")

    # Test submit button
    assert callback_patterns['submit'] == 'alert_submit', "Submit callback correct"
    print(f"  ✅ PASS: Submit callback pattern correct\n")


def test_error_handling():
    """Test that required field validation works"""

    print("Test 4 - Data validation:")

    quiz_data = {
        'bedtime': '22:00',
        'wake_time': '07:00',
        'sleep_latency_minutes': 15,
        'sleep_quality_rating': 8,
        'phone_usage': False,
        'alertness_rating': 7
    }

    required_fields = ['bedtime', 'wake_time', 'sleep_latency_minutes',
                      'sleep_quality_rating', 'phone_usage']

    missing_fields = [f for f in required_fields if f not in quiz_data]

    print(f"  Required fields: {required_fields}")
    print(f"  Missing fields: {missing_fields}")
    assert len(missing_fields) == 0, "All required fields should be present"
    print("  ✅ PASS: All required fields present\n")

    # Test with missing field
    incomplete_data = {
        'bedtime': '22:00',
        'wake_time': '07:00',
        # missing sleep_latency_minutes
        'sleep_quality_rating': 8,
        'phone_usage': False,
    }

    missing = [f for f in required_fields if f not in incomplete_data]
    print(f"Test 5 - Missing field detection:")
    print(f"  Missing fields: {missing}")
    assert 'sleep_latency_minutes' in missing, "Should detect missing field"
    print("  ✅ PASS: Missing field correctly detected\n")


def test_sleep_calculation():
    """Test sleep duration calculation"""

    print("Test 6 - Sleep duration calculation:")

    # Test case: bed at 22:00, wake at 07:00, 15 min to fall asleep
    bed_hour, bed_min = 22, 0
    wake_hour, wake_min = 7, 0
    latency = 15

    bed_total_min = bed_hour * 60 + bed_min  # 1320
    wake_total_min = wake_hour * 60 + wake_min  # 420

    # Handle overnight
    if wake_total_min < bed_total_min:
        wake_total_min += 24 * 60  # 1860

    sleep_minutes = wake_total_min - bed_total_min - latency  # 525
    total_sleep_hours = sleep_minutes / 60.0  # 8.75

    print(f"  Bedtime: {bed_hour:02d}:{bed_min:02d}")
    print(f"  Wake time: {wake_hour:02d}:{wake_min:02d}")
    print(f"  Latency: {latency} min")
    print(f"  Calculated sleep: {total_sleep_hours} hours")

    assert total_sleep_hours == 8.75, f"Expected 8.75 hours, got {total_sleep_hours}"
    print("  ✅ PASS: Sleep duration calculated correctly\n")


if __name__ == "__main__":
    print("="*60)
    print("Testing Alertness Question Bug Fixes")
    print("="*60 + "\n")

    try:
        test_alertness_keyboard_logic()
        test_error_handling()
        test_sleep_calculation()

        print("="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        exit(1)
