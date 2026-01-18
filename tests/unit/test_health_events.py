"""
Unit tests for health_events service
Epic 009 - Phase 5: Event Timeline Foundation

Tests the core event ingestion pipeline including:
- Event creation validation
- Event querying
- Duplicate detection
- Event type validation
- Metadata handling
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from src.services.health_events import (
    create_health_event,
    get_health_events,
    check_duplicate_event,
    get_event_count_by_type,
    delete_health_event,
    VALID_EVENT_TYPES
)


class TestCreateHealthEvent:
    """Tests for create_health_event() function"""

    @pytest.mark.asyncio
    async def test_create_meal_event(self):
        """Test creating a meal health event"""
        user_id = f"test_user_{uuid4()}"
        timestamp = datetime.now()
        metadata = {
            "meal_type": "lunch",
            "total_calories": 650,
            "total_macros": {"protein": 35, "carbs": 75, "fat": 18},
            "foods": [
                {"name": "Chicken breast", "quantity": "200g", "calories": 330}
            ]
        }

        event_id = await create_health_event(
            user_id=user_id,
            event_type="meal",
            timestamp=timestamp,
            metadata=metadata
        )

        assert event_id is not None
        assert isinstance(event_id, UUID)

    @pytest.mark.asyncio
    async def test_create_sleep_event(self):
        """Test creating a sleep health event"""
        user_id = f"test_user_{uuid4()}"
        timestamp = datetime.now()
        metadata = {
            "bedtime": "23:00",
            "wake_time": "07:30",
            "total_sleep_hours": 7.5,
            "sleep_quality_rating": 8,
            "night_wakings": 1
        }

        event_id = await create_health_event(
            user_id=user_id,
            event_type="sleep",
            timestamp=timestamp,
            metadata=metadata
        )

        assert event_id is not None
        assert isinstance(event_id, UUID)

    @pytest.mark.asyncio
    async def test_create_tracker_event(self):
        """Test creating a custom tracker event"""
        user_id = f"test_user_{uuid4()}"
        timestamp = datetime.now()
        metadata = {
            "category_name": "Blood Pressure",
            "category_id": str(uuid4()),
            "data": {"systolic": 120, "diastolic": 80, "heart_rate": 72}
        }

        event_id = await create_health_event(
            user_id=user_id,
            event_type="tracker",
            timestamp=timestamp,
            metadata=metadata
        )

        assert event_id is not None

    @pytest.mark.asyncio
    async def test_invalid_event_type_raises_error(self):
        """Test that invalid event types raise ValueError"""
        with pytest.raises(ValueError, match="Invalid event_type"):
            await create_health_event(
                user_id="test_user",
                event_type="invalid_type",  # type: ignore
                timestamp=datetime.now(),
                metadata={"some": "data"}
            )

    @pytest.mark.asyncio
    async def test_empty_metadata_raises_error(self):
        """Test that empty metadata raises ValueError"""
        with pytest.raises(ValueError, match="metadata cannot be empty"):
            await create_health_event(
                user_id="test_user",
                event_type="meal",
                timestamp=datetime.now(),
                metadata={}
            )

    @pytest.mark.asyncio
    async def test_all_event_types_supported(self):
        """Test that all documented event types are supported"""
        user_id = f"test_user_{uuid4()}"
        timestamp = datetime.now()

        for event_type in VALID_EVENT_TYPES:
            event_id = await create_health_event(
                user_id=user_id,
                event_type=event_type,  # type: ignore
                timestamp=timestamp,
                metadata={"test": "data"}
            )
            assert event_id is not None

    @pytest.mark.asyncio
    async def test_create_with_source_tracking(self):
        """Test creating event with source_table and source_id"""
        user_id = f"test_user_{uuid4()}"
        source_id = uuid4()

        event_id = await create_health_event(
            user_id=user_id,
            event_type="meal",
            timestamp=datetime.now(),
            metadata={"calories": 300},
            source_table="food_entries",
            source_id=source_id
        )

        assert event_id is not None

        # Verify we can check for duplicate
        is_duplicate = await check_duplicate_event("food_entries", source_id)
        assert is_duplicate is True


class TestGetHealthEvents:
    """Tests for get_health_events() query function"""

    @pytest.mark.asyncio
    async def test_get_events_in_date_range(self):
        """Test querying events within a date range"""
        user_id = f"test_user_{uuid4()}"
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()

        # Create multiple events
        for i in range(5):
            await create_health_event(
                user_id=user_id,
                event_type="meal",
                timestamp=start + timedelta(days=i),
                metadata={"calories": 300 + i * 50}
            )

        # Query events
        events = await get_health_events(user_id, start, end)

        assert len(events) >= 5
        # Events should be sorted by timestamp DESC
        timestamps = [e["timestamp"] for e in events]
        assert timestamps == sorted(timestamps, reverse=True)

    @pytest.mark.asyncio
    async def test_filter_events_by_type(self):
        """Test filtering events by event_type"""
        user_id = f"test_user_{uuid4()}"
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()

        # Create mixed event types
        await create_health_event(
            user_id=user_id,
            event_type="meal",
            timestamp=start + timedelta(days=1),
            metadata={"calories": 300}
        )
        await create_health_event(
            user_id=user_id,
            event_type="sleep",
            timestamp=start + timedelta(days=2),
            metadata={"hours": 7}
        )
        await create_health_event(
            user_id=user_id,
            event_type="meal",
            timestamp=start + timedelta(days=3),
            metadata={"calories": 400}
        )

        # Query only meals
        meals = await get_health_events(
            user_id, start, end, event_types=["meal"]
        )

        assert len(meals) >= 2
        assert all(e["event_type"] == "meal" for e in meals)

    @pytest.mark.asyncio
    async def test_query_multiple_event_types(self):
        """Test querying multiple event types at once"""
        user_id = f"test_user_{uuid4()}"
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()

        # Create different event types
        await create_health_event(
            user_id, "meal", start + timedelta(days=1), {"calories": 300}
        )
        await create_health_event(
            user_id, "sleep", start + timedelta(days=2), {"hours": 7}
        )
        await create_health_event(
            user_id, "exercise", start + timedelta(days=3), {"duration": 30}
        )

        # Query meals and sleep only
        events = await get_health_events(
            user_id, start, end, event_types=["meal", "sleep"]
        )

        assert len(events) >= 2
        event_types = {e["event_type"] for e in events}
        assert "exercise" not in event_types

    @pytest.mark.asyncio
    async def test_empty_result_for_no_events(self):
        """Test that empty list is returned when no events match"""
        user_id = f"test_user_{uuid4()}"
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()

        events = await get_health_events(user_id, start, end)

        assert events == []


class TestDuplicateDetection:
    """Tests for check_duplicate_event() function"""

    @pytest.mark.asyncio
    async def test_duplicate_detection_returns_true(self):
        """Test that duplicate events are detected"""
        source_id = uuid4()

        # Create first event
        await create_health_event(
            user_id="test_user",
            event_type="meal",
            timestamp=datetime.now(),
            metadata={"calories": 300},
            source_table="food_entries",
            source_id=source_id
        )

        # Check duplicate
        is_duplicate = await check_duplicate_event("food_entries", source_id)
        assert is_duplicate is True

    @pytest.mark.asyncio
    async def test_no_duplicate_returns_false(self):
        """Test that non-existent events return False"""
        source_id = uuid4()

        is_duplicate = await check_duplicate_event("food_entries", source_id)
        assert is_duplicate is False

    @pytest.mark.asyncio
    async def test_different_source_tables(self):
        """Test that different source tables are treated separately"""
        source_id = uuid4()

        # Create event from food_entries
        await create_health_event(
            user_id="test_user",
            event_type="meal",
            timestamp=datetime.now(),
            metadata={"calories": 300},
            source_table="food_entries",
            source_id=source_id
        )

        # Check against sleep_entries (should be False)
        is_duplicate = await check_duplicate_event("sleep_entries", source_id)
        assert is_duplicate is False


class TestEventCountByType:
    """Tests for get_event_count_by_type() function"""

    @pytest.mark.asyncio
    async def test_count_events_by_type(self):
        """Test counting events grouped by type"""
        user_id = f"test_user_{uuid4()}"
        start = datetime.now() - timedelta(days=30)
        end = datetime.now()

        # Create multiple events of different types
        for _ in range(3):
            await create_health_event(
                user_id, "meal", datetime.now(), {"calories": 300}
            )
        for _ in range(2):
            await create_health_event(
                user_id, "sleep", datetime.now(), {"hours": 7}
            )
        await create_health_event(
            user_id, "exercise", datetime.now(), {"duration": 30}
        )

        counts = await get_event_count_by_type(user_id, start, end)

        assert counts.get("meal", 0) >= 3
        assert counts.get("sleep", 0) >= 2
        assert counts.get("exercise", 0) >= 1


class TestDeleteHealthEvent:
    """Tests for delete_health_event() function"""

    @pytest.mark.asyncio
    async def test_delete_existing_event(self):
        """Test deleting an existing event"""
        user_id = f"test_user_{uuid4()}"
        event_id = await create_health_event(
            user_id=user_id,
            event_type="meal",
            timestamp=datetime.now(),
            metadata={"calories": 300}
        )

        # Delete the event
        deleted = await delete_health_event(event_id)
        assert deleted is True

    @pytest.mark.asyncio
    async def test_delete_non_existent_event(self):
        """Test deleting a non-existent event returns False"""
        fake_id = uuid4()
        deleted = await delete_health_event(fake_id)
        assert deleted is False
