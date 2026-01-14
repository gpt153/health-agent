"""Integration tests for smart conditional reminders (GitHub issue #41)"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.db.queries import (
    save_food_entry,
    create_reminder,
    get_reminder_by_id,
    has_logged_food_in_window,
    has_completed_reminder_today,
    save_reminder_completion
)
from src.models.food import FoodEntry, FoodItem, Macros
from src.models.reminder import Reminder, ReminderSchedule


@pytest.mark.asyncio
async def test_food_logged_condition_met():
    """
    Test that food_logged condition returns True when food was logged within time window
    """
    user_id = f"test_user_{uuid4()}"

    # Log food entry 1 hour ago
    entry = FoodEntry(
        user_id=user_id,
        timestamp=datetime.now() - timedelta(hours=1),
        photo_path=None,
        foods=[
            FoodItem(
                name="Lunch",
                quantity="1 plate",
                calories=500,
                macros=Macros(protein=30, carbs=50, fat=20)
            )
        ],
        total_calories=500,
        total_macros=Macros(protein=30, carbs=50, fat=20),
        meal_type="lunch",
        notes="Test entry"
    )
    await save_food_entry(entry)

    # Check if food logged in last 2 hours - should be True
    result = await has_logged_food_in_window(user_id, window_hours=2)
    assert result is True


@pytest.mark.asyncio
async def test_food_logged_condition_not_met():
    """
    Test that food_logged condition returns False when food was logged outside time window
    """
    user_id = f"test_user_{uuid4()}"

    # Log food entry 5 hours ago
    entry = FoodEntry(
        user_id=user_id,
        timestamp=datetime.now() - timedelta(hours=5),
        photo_path=None,
        foods=[
            FoodItem(
                name="Breakfast",
                quantity="1 plate",
                calories=400,
                macros=Macros(protein=20, carbs=40, fat=15)
            )
        ],
        total_calories=400,
        total_macros=Macros(protein=20, carbs=40, fat=15),
        meal_type="breakfast",
        notes="Test entry"
    )
    await save_food_entry(entry)

    # Check if food logged in last 2 hours - should be False
    result = await has_logged_food_in_window(user_id, window_hours=2)
    assert result is False


@pytest.mark.asyncio
async def test_food_logged_with_meal_type_filter():
    """
    Test that food_logged condition correctly filters by meal_type
    """
    user_id = f"test_user_{uuid4()}"

    # Log breakfast 1 hour ago
    breakfast = FoodEntry(
        user_id=user_id,
        timestamp=datetime.now() - timedelta(hours=1),
        photo_path=None,
        foods=[
            FoodItem(
                name="Oatmeal",
                quantity="1 bowl",
                calories=300,
                macros=Macros(protein=10, carbs=50, fat=5)
            )
        ],
        total_calories=300,
        total_macros=Macros(protein=10, carbs=50, fat=5),
        meal_type="breakfast",
        notes="Morning meal"
    )
    await save_food_entry(breakfast)

    # Check for lunch in last 2 hours - should be False (only breakfast logged)
    result = await has_logged_food_in_window(user_id, window_hours=2, meal_type="lunch")
    assert result is False

    # Check for breakfast in last 2 hours - should be True
    result = await has_logged_food_in_window(user_id, window_hours=2, meal_type="breakfast")
    assert result is True


@pytest.mark.asyncio
async def test_completion_condition_met():
    """
    Test that completion check returns True when reminder was completed today
    """
    user_id = f"test_user_{uuid4()}"
    reminder_id = str(uuid4())

    # Mark reminder as completed today
    await save_reminder_completion(
        user_id=user_id,
        reminder_id=reminder_id,
        scheduled_time="12:00"
    )

    # Check if reminder completed today - should be True
    result = await has_completed_reminder_today(user_id, reminder_id)
    assert result is True


@pytest.mark.asyncio
async def test_completion_condition_not_met():
    """
    Test that completion check returns False when reminder was not completed
    """
    user_id = f"test_user_{uuid4()}"
    reminder_id = str(uuid4())

    # Don't mark as completed
    # Check if reminder completed today - should be False
    result = await has_completed_reminder_today(user_id, reminder_id)
    assert result is False


@pytest.mark.asyncio
async def test_reminder_with_check_condition_stored():
    """
    Test that check_condition JSONB field persists correctly in database
    """
    user_id = f"test_user_{uuid4()}"

    # Create reminder with check_condition
    reminder = Reminder(
        user_id=user_id,
        reminder_type="simple",
        message="Eat lunch if you haven't logged food",
        schedule=ReminderSchedule(
            type="daily",
            time="12:00",
            timezone="Europe/Stockholm"
        ),
        check_condition={
            "type": "food_logged",
            "window_hours": 2,
            "meal_type": "lunch"
        }
    )

    await create_reminder(reminder)

    # Retrieve reminder and verify check_condition persists
    retrieved = await get_reminder_by_id(str(reminder.id))

    assert retrieved is not None
    assert retrieved["check_condition"] is not None
    assert retrieved["check_condition"]["type"] == "food_logged"
    assert retrieved["check_condition"]["window_hours"] == 2
    assert retrieved["check_condition"]["meal_type"] == "lunch"


@pytest.mark.asyncio
async def test_backward_compatibility_no_condition():
    """
    Test that reminders without check_condition work unchanged (backward compatible)
    """
    user_id = f"test_user_{uuid4()}"

    # Create reminder WITHOUT check_condition (like existing reminders)
    reminder = Reminder(
        user_id=user_id,
        reminder_type="simple",
        message="Take your vitamins",
        schedule=ReminderSchedule(
            type="daily",
            time="09:00",
            timezone="UTC"
        )
        # Note: no check_condition specified
    )

    await create_reminder(reminder)

    # Retrieve reminder and verify check_condition is None
    retrieved = await get_reminder_by_id(str(reminder.id))

    assert retrieved is not None
    assert retrieved["check_condition"] is None  # Should default to None


@pytest.mark.asyncio
async def test_food_logged_no_entries():
    """
    Test that food_logged condition returns False when user has no food entries
    """
    user_id = f"test_user_{uuid4()}"  # New user, no entries

    # Check if food logged in last 2 hours - should be False
    result = await has_logged_food_in_window(user_id, window_hours=2)
    assert result is False


@pytest.mark.asyncio
async def test_food_logged_multiple_entries_in_window():
    """
    Test that food_logged condition returns True when multiple entries exist in window
    """
    user_id = f"test_user_{uuid4()}"

    # Log multiple entries within window
    for i in range(3):
        entry = FoodEntry(
            user_id=user_id,
            timestamp=datetime.now() - timedelta(minutes=30 * i),
            photo_path=None,
            foods=[
                FoodItem(
                    name=f"Snack {i}",
                    quantity="1 serving",
                    calories=100,
                    macros=Macros(protein=5, carbs=10, fat=3)
                )
            ],
            total_calories=100,
            total_macros=Macros(protein=5, carbs=10, fat=3),
            meal_type="snack",
            notes=f"Test entry {i}"
        )
        await save_food_entry(entry)

    # Check if food logged in last 2 hours - should be True
    result = await has_logged_food_in_window(user_id, window_hours=2)
    assert result is True


@pytest.mark.asyncio
async def test_food_logged_boundary_condition():
    """
    Test boundary condition: food logged exactly at window edge
    """
    user_id = f"test_user_{uuid4()}"

    # Log food exactly 2 hours ago (at the boundary)
    entry = FoodEntry(
        user_id=user_id,
        timestamp=datetime.now() - timedelta(hours=2, seconds=1),  # Just outside
        photo_path=None,
        foods=[
            FoodItem(
                name="Boundary test",
                quantity="1 serving",
                calories=200,
                macros=Macros(protein=10, carbs=20, fat=8)
            )
        ],
        total_calories=200,
        total_macros=Macros(protein=10, carbs=20, fat=8),
        meal_type="snack",
        notes="Boundary test"
    )
    await save_food_entry(entry)

    # Check if food logged in last 2 hours - should be False (just outside)
    result = await has_logged_food_in_window(user_id, window_hours=2)
    assert result is False

    # Log another entry just inside window
    entry2 = FoodEntry(
        user_id=user_id,
        timestamp=datetime.now() - timedelta(hours=1, minutes=59),  # Just inside
        photo_path=None,
        foods=[
            FoodItem(
                name="Boundary test 2",
                quantity="1 serving",
                calories=200,
                macros=Macros(protein=10, carbs=20, fat=8)
            )
        ],
        total_calories=200,
        total_macros=Macros(protein=10, carbs=20, fat=8),
        meal_type="snack",
        notes="Boundary test 2"
    )
    await save_food_entry(entry2)

    # Check again - should now be True
    result = await has_logged_food_in_window(user_id, window_hours=2)
    assert result is True
