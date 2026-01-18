"""
Performance tests for temporal queries
Epic 009 - Phase 5: Event Timeline Foundation

Tests that temporal queries meet the <50ms performance target for 30-day ranges.
These tests verify that the database indexes are working correctly.
"""
import pytest
import time
from datetime import datetime, timedelta
from uuid import uuid4
from src.services.health_events import create_health_event, get_health_events


class TestTemporalQueryPerformance:
    """Test performance of temporal queries"""

    @pytest.mark.asyncio
    async def test_30_day_query_performance(self):
        """
        Test that 30-day queries complete in <50ms.

        This is a CRITICAL performance requirement for Phase 5.
        The idx_health_events_user_time index must be optimized for this.
        """
        user_id = f"perf_test_user_{uuid4()}"
        start = datetime.now() - timedelta(days=30)
        end = datetime.now()

        # Create 100 events spread over 30 days
        # (Simulates an active user logging ~3 meals/day)
        for i in range(100):
            timestamp = start + timedelta(hours=i * 7)  # Every 7 hours
            await create_health_event(
                user_id=user_id,
                event_type="meal",
                timestamp=timestamp,
                metadata={"calories": 500 + i, "meal_type": "meal"}
            )

        # Measure query time (using high-resolution timer)
        query_start = time.perf_counter()
        events = await get_health_events(
            user_id,
            start_date=start,
            end_date=end
        )
        query_end = time.perf_counter()

        query_time_ms = (query_end - query_start) * 1000

        # Assertions
        assert len(events) == 100, f"Expected 100 events, got {len(events)}"
        assert query_time_ms < 50, (
            f"Query took {query_time_ms:.2f}ms (target: <50ms). "
            f"Index optimization may be needed."
        )

        print(f"\n✅ 30-day query performance: {query_time_ms:.2f}ms (target: <50ms)")

    @pytest.mark.asyncio
    async def test_filtered_query_performance(self):
        """
        Test that filtered queries (by event_type) are also fast.

        Uses idx_health_events_user_type_time index.
        """
        user_id = f"perf_test_user_{uuid4()}"
        start = datetime.now() - timedelta(days=30)
        end = datetime.now()

        # Create mixed event types (meals, sleep, trackers)
        for i in range(60):
            # Meals
            await create_health_event(
                user_id=user_id,
                event_type="meal",
                timestamp=start + timedelta(hours=i * 12),
                metadata={"calories": 500}
            )

        for i in range(30):
            # Sleep
            await create_health_event(
                user_id=user_id,
                event_type="sleep",
                timestamp=start + timedelta(days=i),
                metadata={"hours": 7.5}
            )

        for i in range(20):
            # Trackers
            await create_health_event(
                user_id=user_id,
                event_type="tracker",
                timestamp=start + timedelta(days=i),
                metadata={"value": 100}
            )

        # Measure filtered query time (meals only)
        query_start = time.perf_counter()
        meals = await get_health_events(
            user_id,
            start_date=start,
            end_date=end,
            event_types=["meal"]
        )
        query_time_ms = (time.perf_counter() - query_start) * 1000

        assert len(meals) == 60
        assert query_time_ms < 50, (
            f"Filtered query took {query_time_ms:.2f}ms (target: <50ms)"
        )

        print(f"\n✅ Filtered query performance: {query_time_ms:.2f}ms")

    @pytest.mark.asyncio
    async def test_multi_type_query_performance(self):
        """Test querying multiple event types at once"""
        user_id = f"perf_test_user_{uuid4()}"
        start = datetime.now() - timedelta(days=30)
        end = datetime.now()

        # Create events
        for i in range(50):
            await create_health_event(
                user_id, "meal", start + timedelta(hours=i * 14), {"calories": 500}
            )
        for i in range(30):
            await create_health_event(
                user_id, "sleep", start + timedelta(days=i), {"hours": 7}
            )

        # Query meals + sleep
        query_start = time.perf_counter()
        events = await get_health_events(
            user_id,
            start_date=start,
            end_date=end,
            event_types=["meal", "sleep"]
        )
        query_time_ms = (time.perf_counter() - query_start) * 1000

        assert len(events) == 80
        assert query_time_ms < 50, (
            f"Multi-type query took {query_time_ms:.2f}ms (target: <50ms)"
        )

        print(f"\n✅ Multi-type query performance: {query_time_ms:.2f}ms")

    @pytest.mark.asyncio
    async def test_large_dataset_performance(self):
        """
        Test performance with larger dataset (300+ events).

        This simulates a very active user with 3+ months of data.
        """
        user_id = f"perf_test_user_{uuid4()}"
        start = datetime.now() - timedelta(days=90)
        end = datetime.now()

        # Create 300 events (90 days * ~3 events/day)
        for i in range(300):
            timestamp = start + timedelta(hours=i * 7)
            await create_health_event(
                user_id=user_id,
                event_type="meal" if i % 3 != 0 else "sleep",
                timestamp=timestamp,
                metadata={"value": i}
            )

        # Query 30-day window within the 90 days
        query_start_date = start + timedelta(days=30)
        query_end_date = start + timedelta(days=60)

        query_start = time.perf_counter()
        events = await get_health_events(
            user_id,
            start_date=query_start_date,
            end_date=query_end_date
        )
        query_time_ms = (time.perf_counter() - query_start) * 1000

        # Should get ~100 events (30 days * ~3 events/day)
        assert 90 <= len(events) <= 110, f"Got {len(events)} events"
        assert query_time_ms < 50, (
            f"Large dataset query took {query_time_ms:.2f}ms (target: <50ms)"
        )

        print(f"\n✅ Large dataset query performance: {query_time_ms:.2f}ms")


class TestIndexEffectiveness:
    """Test that database indexes are being used effectively"""

    @pytest.mark.asyncio
    async def test_query_returns_sorted_results(self):
        """
        Test that results are sorted by timestamp DESC.

        This verifies the index is working (sorted results with no extra sort operation).
        """
        user_id = f"test_user_{uuid4()}"
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()

        # Create events in random order
        timestamps = [
            start + timedelta(days=5),
            start + timedelta(days=1),
            start + timedelta(days=3),
            start + timedelta(days=6),
            start + timedelta(days=2),
        ]

        for ts in timestamps:
            await create_health_event(
                user_id, "meal", ts, {"calories": 500}
            )

        # Query events
        events = await get_health_events(user_id, start, end)

        # Verify sorted DESC (newest first)
        event_timestamps = [e["timestamp"] for e in events]
        assert event_timestamps == sorted(event_timestamps, reverse=True), (
            "Events are not sorted by timestamp DESC"
        )

    @pytest.mark.asyncio
    async def test_user_isolation(self):
        """
        Test that queries only return events for the specified user.

        This verifies the user_id index is working correctly.
        """
        user1 = f"user1_{uuid4()}"
        user2 = f"user2_{uuid4()}"
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()

        # Create events for both users
        for _ in range(5):
            await create_health_event(
                user1, "meal", datetime.now(), {"calories": 500}
            )
            await create_health_event(
                user2, "meal", datetime.now(), {"calories": 500}
            )

        # Query user1's events
        user1_events = await get_health_events(user1, start, end)

        # Verify all events belong to user1
        assert all(e["user_id"] == user1 for e in user1_events)
        assert len(user1_events) == 5


class TestQueryEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_empty_date_range(self):
        """Test query with no events in date range"""
        user_id = f"test_user_{uuid4()}"

        # Create event today
        await create_health_event(
            user_id, "meal", datetime.now(), {"calories": 500}
        )

        # Query for events from 2 years ago
        start = datetime.now() - timedelta(days=730)
        end = datetime.now() - timedelta(days=700)

        events = await get_health_events(user_id, start, end)

        assert events == []

    @pytest.mark.asyncio
    async def test_single_day_query(self):
        """Test querying events from a single day"""
        user_id = f"test_user_{uuid4()}"
        today = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)

        # Create events throughout the day
        for hour in [8, 12, 18]:
            await create_health_event(
                user_id,
                "meal",
                today.replace(hour=hour),
                {"calories": 500}
            )

        # Query just today
        start = today.replace(hour=0, minute=0)
        end = today.replace(hour=23, minute=59)

        events = await get_health_events(user_id, start, end)

        assert len(events) == 3
