"""Unit tests for sleep data models"""
from src.models.sleep import SleepEntry
from datetime import datetime, time
import pytest


def test_sleep_entry_validation():
    """Test Pydantic validation for SleepEntry"""
    # Valid entry
    entry = SleepEntry(
        id="test123",
        user_id="user1",
        logged_at=datetime.now(),
        bedtime=time(22, 0),
        sleep_latency_minutes=15,
        wake_time=time(7, 0),
        total_sleep_hours=8.5,
        night_wakings=0,
        sleep_quality_rating=8,
        disruptions=[],
        phone_usage=False,
        phone_duration_minutes=None,
        alertness_rating=7
    )
    assert entry.sleep_quality_rating == 8
    assert entry.total_sleep_hours == 8.5
    assert entry.alertness_rating == 7


def test_sleep_entry_invalid_quality_rating():
    """Test quality rating out of range"""
    with pytest.raises(ValueError):
        SleepEntry(
            id="test",
            user_id="u1",
            logged_at=datetime.now(),
            bedtime=time(22, 0),
            sleep_latency_minutes=15,
            wake_time=time(7, 0),
            total_sleep_hours=8.5,
            night_wakings=0,
            sleep_quality_rating=11,  # > 10, should fail
            disruptions=[],
            phone_usage=False,
            phone_duration_minutes=None,
            alertness_rating=7
        )


def test_sleep_entry_invalid_alertness():
    """Test alertness rating out of range"""
    with pytest.raises(ValueError):
        SleepEntry(
            id="test",
            user_id="u1",
            logged_at=datetime.now(),
            bedtime=time(22, 0),
            sleep_latency_minutes=15,
            wake_time=time(7, 0),
            total_sleep_hours=8.5,
            night_wakings=0,
            sleep_quality_rating=8,
            disruptions=[],
            phone_usage=False,
            phone_duration_minutes=None,
            alertness_rating=0  # < 1, should fail
        )


def test_sleep_entry_with_disruptions():
    """Test entry with multiple disruptions"""
    entry = SleepEntry(
        id="test",
        user_id="u1",
        logged_at=datetime.now(),
        bedtime=time(23, 30),
        sleep_latency_minutes=45,
        wake_time=time(6, 15),
        total_sleep_hours=6.75,
        night_wakings=2,
        sleep_quality_rating=5,
        disruptions=["noise", "light", "stress"],
        phone_usage=True,
        phone_duration_minutes=30,
        alertness_rating=4
    )
    assert len(entry.disruptions) == 3
    assert "noise" in entry.disruptions
    assert entry.phone_usage is True
    assert entry.phone_duration_minutes == 30


def test_sleep_entry_negative_latency():
    """Test negative latency is rejected"""
    with pytest.raises(ValueError):
        SleepEntry(
            id="test",
            user_id="u1",
            logged_at=datetime.now(),
            bedtime=time(22, 0),
            sleep_latency_minutes=-5,  # Negative, should fail
            wake_time=time(7, 0),
            total_sleep_hours=8.5,
            night_wakings=0,
            sleep_quality_rating=8,
            disruptions=[],
            phone_usage=False,
            phone_duration_minutes=None,
            alertness_rating=7
        )
