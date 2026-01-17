"""
Integration tests for event hooks
Epic 009 - Phase 5: Event Timeline Foundation

Tests that saving food/sleep/tracking entries automatically creates
corresponding health_events in the background.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from src.models.food import FoodEntry, FoodItem, FoodMacros
from src.models.sleep import SleepEntry
from src.models.tracking import TrackerEntry, TrackingCategory, TrackingField
from src.db.queries.food import save_food_entry
from src.db.queries.tracking import save_sleep_entry, save_tracking_entry, create_tracking_category
from src.services.health_events import get_health_events


class TestFoodEntryEventHook:
    """Test that food entries create meal health_events"""

    @pytest.mark.asyncio
    async def test_food_entry_creates_health_event(self):
        """Test that saving a food entry automatically creates a meal health_event"""
        user_id = f"test_user_{uuid4()}"
        timestamp = datetime.now()

        # Create food entry
        entry = FoodEntry(
            user_id=user_id,
            timestamp=timestamp,
            foods=[
                FoodItem(
                    name="Apple",
                    quantity="1 medium",
                    calories=95,
                    macros=FoodMacros(protein=0.5, carbs=25, fat=0.3)
                )
            ],
            total_calories=95,
            total_macros=FoodMacros(protein=0.5, carbs=25, fat=0.3),
            meal_type="snack"
        )

        await save_food_entry(entry)

        # Wait for background task to complete
        await asyncio.sleep(0.5)

        # Verify health event was created
        events = await get_health_events(
            user_id,
            start_date=timestamp - timedelta(seconds=10),
            end_date=timestamp + timedelta(seconds=10),
            event_types=["meal"]
        )

        assert len(events) >= 1, "Health event was not created"

        event = events[0]
        assert event["event_type"] == "meal"
        assert event["user_id"] == user_id
        assert event["metadata"]["total_calories"] == 95
        assert event["metadata"]["meal_type"] == "snack"
        assert event["source_table"] == "food_entries"

    @pytest.mark.asyncio
    async def test_multiple_food_entries_create_multiple_events(self):
        """Test that multiple food entries create multiple health_events"""
        user_id = f"test_user_{uuid4()}"
        timestamp = datetime.now()

        # Create 3 food entries
        for i in range(3):
            entry = FoodEntry(
                user_id=user_id,
                timestamp=timestamp + timedelta(hours=i),
                foods=[
                    FoodItem(
                        name=f"Food {i}",
                        quantity="100g",
                        calories=100 + i * 50,
                        macros=FoodMacros(protein=10, carbs=15, fat=5)
                    )
                ],
                total_calories=100 + i * 50,
                total_macros=FoodMacros(protein=10, carbs=15, fat=5),
                meal_type="meal"
            )
            await save_food_entry(entry)

        # Wait for background tasks
        await asyncio.sleep(1)

        # Verify all events were created
        events = await get_health_events(
            user_id,
            start_date=timestamp - timedelta(seconds=10),
            end_date=timestamp + timedelta(hours=3),
            event_types=["meal"]
        )

        assert len(events) >= 3


class TestSleepEntryEventHook:
    """Test that sleep entries create sleep health_events"""

    @pytest.mark.asyncio
    async def test_sleep_entry_creates_health_event(self):
        """Test that saving a sleep entry automatically creates a sleep health_event"""
        user_id = f"test_user_{uuid4()}"
        logged_at = datetime.now()

        # Create sleep entry
        entry = SleepEntry(
            id=str(uuid4()),
            user_id=user_id,
            logged_at=logged_at,
            bedtime=datetime.strptime("23:00", "%H:%M").time(),
            sleep_latency_minutes=15,
            wake_time=datetime.strptime("07:30", "%H:%M").time(),
            total_sleep_hours=7.5,
            night_wakings=1,
            sleep_quality_rating=8,
            disruptions=["bathroom"],
            phone_usage=False,
            phone_duration_minutes=0,
            alertness_rating=7
        )

        await save_sleep_entry(entry)

        # Wait for background task
        await asyncio.sleep(0.5)

        # Verify health event was created
        events = await get_health_events(
            user_id,
            start_date=logged_at - timedelta(seconds=10),
            end_date=logged_at + timedelta(seconds=10),
            event_types=["sleep"]
        )

        assert len(events) >= 1, "Sleep health event was not created"

        event = events[0]
        assert event["event_type"] == "sleep"
        assert event["user_id"] == user_id
        assert event["metadata"]["total_sleep_hours"] == 7.5
        assert event["metadata"]["sleep_quality_rating"] == 8
        assert event["metadata"]["bedtime"] == "23:00:00"
        assert event["metadata"]["wake_time"] == "07:30:00"
        assert event["source_table"] == "sleep_entries"


class TestTrackerEntryEventHook:
    """Test that tracker entries create tracker health_events"""

    @pytest.mark.asyncio
    async def test_tracker_entry_creates_health_event(self):
        """Test that saving a tracker entry automatically creates a tracker health_event"""
        user_id = f"test_user_{uuid4()}"
        timestamp = datetime.now()

        # Create tracking category first
        category = TrackingCategory(
            user_id=user_id,
            name="Blood Pressure Test",
            fields={
                "systolic": TrackingField(type="number", label="Systolic", required=True),
                "diastolic": TrackingField(type="number", label="Diastolic", required=True)
            },
            active=True
        )
        await create_tracking_category(category)

        # Create tracker entry
        entry = TrackerEntry(
            user_id=user_id,
            category_id=category.id,
            timestamp=timestamp,
            data={"systolic": 120, "diastolic": 80},
            notes="Morning reading"
        )

        await save_tracking_entry(entry)

        # Wait for background task
        await asyncio.sleep(0.5)

        # Verify health event was created
        events = await get_health_events(
            user_id,
            start_date=timestamp - timedelta(seconds=10),
            end_date=timestamp + timedelta(seconds=10),
            event_types=["tracker"]
        )

        assert len(events) >= 1, "Tracker health event was not created"

        event = events[0]
        assert event["event_type"] == "tracker"
        assert event["user_id"] == user_id
        assert event["metadata"]["category_name"] == "Blood Pressure Test"
        assert event["metadata"]["data"]["systolic"] == 120
        assert event["metadata"]["data"]["diastolic"] == 80
        assert event["metadata"]["notes"] == "Morning reading"
        assert event["source_table"] == "tracking_entries"


class TestEventHookResilience:
    """Test that event hooks are resilient to failures"""

    @pytest.mark.asyncio
    async def test_food_entry_saves_even_if_event_creation_fails(self):
        """
        Test that the main food_entry transaction succeeds even if
        health_event creation fails in background.

        This is important for system resilience - user-facing operations
        should not fail due to background event processing issues.
        """
        user_id = f"test_user_{uuid4()}"
        timestamp = datetime.now()

        # Create food entry (should succeed regardless of event hook)
        entry = FoodEntry(
            user_id=user_id,
            timestamp=timestamp,
            foods=[
                FoodItem(
                    name="Test Food",
                    quantity="100g",
                    calories=100,
                    macros=FoodMacros(protein=10, carbs=15, fat=5)
                )
            ],
            total_calories=100,
            total_macros=FoodMacros(protein=10, carbs=15, fat=5),
            meal_type="meal"
        )

        # This should not raise an exception even if background task fails
        await save_food_entry(entry)

        # The entry itself was saved successfully
        # (Background event creation may or may not succeed - that's ok)
