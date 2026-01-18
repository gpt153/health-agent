"""Unit tests for database queries (src/db/queries.py)"""
import pytest
import json
from datetime import datetime, date, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from uuid import uuid4

from src.db import queries
from src.models.user import UserProfile
from src.models.food import FoodEntry, FoodItem, FoodMacros
from src.models.tracking import TrackingCategory, TrackingEntry, TrackingField
from src.models.reminder import Reminder
from src.models.sleep import SleepEntry


# ============================================================================
# User Operations Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_user_new():
    """Test creating a new user"""
    telegram_id = "123456789"

    mock_cursor = AsyncMock()
    mock_cursor.execute = AsyncMock()

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        await queries.create_user(telegram_id)

        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "INSERT INTO users" in call_args[0]
        assert telegram_id in call_args[1]
        mock_conn.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_existing():
    """Test creating user that already exists (should not raise error due to ON CONFLICT)"""
    telegram_id = "123456789"

    mock_cursor = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        await queries.create_user(telegram_id)

        # Should complete without error
        mock_conn.commit.assert_called_once()


@pytest.mark.asyncio
async def test_user_exists_true():
    """Test user_exists returns True for existing user"""
    telegram_id = "123456789"

    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = {"telegram_id": telegram_id}

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        result = await queries.user_exists(telegram_id)

        assert result is True
        mock_cursor.execute.assert_called_once()


@pytest.mark.asyncio
async def test_user_exists_false():
    """Test user_exists returns False for non-existent user"""
    telegram_id = "999999999"

    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = None

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        result = await queries.user_exists(telegram_id)

        assert result is False


# ============================================================================
# Food Entry Operations Tests
# ============================================================================

@pytest.mark.asyncio
async def test_save_food_entry_success():
    """Test successfully saving a food entry"""
    food_item = FoodItem(
        name="Chicken Breast",
        quantity="150g",
        calories=165,
        protein=31.0,
        carbs=0.0,
        fat=3.6
    )

    macros = FoodMacros(protein=31.0, carbs=0.0, fat=3.6)

    entry = FoodEntry(
        user_id="123456789",
        timestamp=datetime.now(timezone.utc),
        foods=[food_item],
        total_calories=165,
        total_macros=macros,
        meal_type="lunch"
    )

    mock_cursor = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        await queries.save_food_entry(entry)

        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "INSERT INTO food_entries" in call_args[0]
        assert entry.user_id in call_args[1]
        mock_conn.commit.assert_called_once()


@pytest.mark.asyncio
async def test_save_food_entry_with_photo():
    """Test saving food entry with photo path"""
    food_item = FoodItem(
        name="Pizza",
        quantity="2 slices",
        calories=285,
        protein=12.0,
        carbs=36.0,
        fat=10.0
    )

    macros = FoodMacros(protein=12.0, carbs=36.0, fat=10.0)

    entry = FoodEntry(
        user_id="123456789",
        timestamp=datetime.now(timezone.utc),
        photo_path="/photos/pizza_123.jpg",
        foods=[food_item],
        total_calories=285,
        total_macros=macros,
        meal_type="dinner"
    )

    mock_cursor = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        await queries.save_food_entry(entry)

        mock_conn.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_food_entry_success():
    """Test successfully updating a food entry"""
    entry_id = str(uuid4())
    user_id = "123456789"

    # Mock existing entry
    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = {
        "id": entry_id,
        "user_id": user_id,
        "total_calories": 200,
        "total_macros": {"protein": 20.0, "carbs": 10.0, "fat": 8.0},
        "foods": []
    }

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        result = await queries.update_food_entry(
            entry_id=entry_id,
            user_id=user_id,
            total_calories=250,
            total_macros={"protein": 25.0, "carbs": 15.0, "fat": 10.0},
            correction_note="Updated macros"
        )

        assert result["success"] is True
        mock_conn.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_food_entry_not_found():
    """Test updating non-existent food entry"""
    entry_id = str(uuid4())
    user_id = "123456789"

    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = None

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        result = await queries.update_food_entry(
            entry_id=entry_id,
            user_id=user_id,
            total_calories=250
        )

        assert result["success"] is False
        assert "not found" in result.get("error", "").lower()


@pytest.mark.asyncio
async def test_update_food_entry_wrong_user():
    """Test updating food entry with wrong user ID"""
    entry_id = str(uuid4())
    user_id = "123456789"
    wrong_user = "999999999"

    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = None  # No match for wrong user

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        result = await queries.update_food_entry(
            entry_id=entry_id,
            user_id=wrong_user,
            total_calories=250
        )

        assert result["success"] is False


@pytest.mark.asyncio
async def test_get_recent_food_entries():
    """Test retrieving recent food entries"""
    user_id = "123456789"

    mock_entries = [
        {
            "id": str(uuid4()),
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc),
            "total_calories": 200,
            "foods": []
        },
        {
            "id": str(uuid4()),
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc) - timedelta(hours=3),
            "total_calories": 350,
            "foods": []
        }
    ]

    mock_cursor = AsyncMock()
    mock_cursor.fetchall.return_value = mock_entries

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        entries = await queries.get_recent_food_entries(user_id, limit=10)

        assert len(entries) == 2
        mock_cursor.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_food_entries_by_date():
    """Test retrieving food entries for a specific date"""
    user_id = "123456789"
    target_date = date(2024, 1, 15)

    mock_entries = [
        {
            "id": str(uuid4()),
            "user_id": user_id,
            "timestamp": datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc),
            "total_calories": 400,
        }
    ]

    mock_cursor = AsyncMock()
    mock_cursor.fetchall.return_value = mock_entries

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        entries = await queries.get_food_entries_by_date(user_id, target_date)

        assert len(entries) == 1
        mock_cursor.execute.assert_called_once()


@pytest.mark.asyncio
async def test_has_logged_food_in_window_true():
    """Test has_logged_food_in_window returns True when food logged"""
    user_id = "123456789"
    hours = 4

    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = {"count": 1}

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        result = await queries.has_logged_food_in_window(user_id, hours)

        assert result is True


@pytest.mark.asyncio
async def test_has_logged_food_in_window_false():
    """Test has_logged_food_in_window returns False when no food logged"""
    user_id = "123456789"
    hours = 4

    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = {"count": 0}

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        result = await queries.has_logged_food_in_window(user_id, hours)

        assert result is False


# ============================================================================
# Reminder Operations Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_reminder_basic():
    """Test creating a basic reminder"""
    reminder = Reminder(
        user_id="123456789",
        type="food_log",
        time="12:00",
        timezone="America/New_York",
        days_of_week=[0, 1, 2, 3, 4],  # Mon-Fri
        active=True
    )

    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = {"id": str(uuid4())}

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        await queries.create_reminder(reminder)

        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_active_reminders():
    """Test retrieving active reminders for a user"""
    user_id = "123456789"

    mock_reminders = [
        {
            "id": str(uuid4()),
            "user_id": user_id,
            "type": "food_log",
            "time": "12:00",
            "active": True
        },
        {
            "id": str(uuid4()),
            "user_id": user_id,
            "type": "water",
            "time": "09:00",
            "active": True
        }
    ]

    mock_cursor = AsyncMock()
    mock_cursor.fetchall.return_value = mock_reminders

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        reminders = await queries.get_active_reminders(user_id)

        assert len(reminders) == 2
        assert all(r["active"] for r in reminders)


@pytest.mark.asyncio
async def test_delete_reminder_success():
    """Test successfully deleting a reminder"""
    reminder_id = str(uuid4())
    user_id = "123456789"

    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = {"id": reminder_id}

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        result = await queries.delete_reminder(reminder_id, user_id)

        assert result is True
        mock_conn.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_reminder_not_found():
    """Test deleting non-existent reminder"""
    reminder_id = str(uuid4())
    user_id = "123456789"

    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = None

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        result = await queries.delete_reminder(reminder_id, user_id)

        assert result is False


@pytest.mark.asyncio
async def test_delete_reminder_wrong_user():
    """Test deleting reminder with wrong user ID"""
    reminder_id = str(uuid4())
    user_id = "123456789"
    wrong_user = "999999999"

    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = None

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        result = await queries.delete_reminder(reminder_id, wrong_user)

        assert result is False


@pytest.mark.asyncio
async def test_update_reminder():
    """Test updating a reminder"""
    reminder_id = str(uuid4())
    user_id = "123456789"

    mock_cursor = AsyncMock()
    mock_cursor.fetchone.side_effect = [
        {"id": reminder_id, "user_id": user_id},  # First call: check ownership
        {"id": reminder_id}  # Second call: return updated reminder
    ]

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        result = await queries.update_reminder(
            reminder_id=reminder_id,
            user_id=user_id,
            time="14:00",
            days_of_week=[1, 3, 5]
        )

        assert result is not None
        mock_conn.commit.assert_called_once()


@pytest.mark.asyncio
async def test_find_duplicate_reminders():
    """Test finding duplicate reminders"""
    user_id = "123456789"

    mock_duplicates = [
        {
            "user_id": user_id,
            "type": "food_log",
            "time": "12:00",
            "count": 3
        }
    ]

    mock_cursor = AsyncMock()
    mock_cursor.fetchall.return_value = mock_duplicates

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        duplicates = await queries.find_duplicate_reminders(user_id)

        assert len(duplicates) >= 0
        mock_cursor.execute.assert_called_once()


@pytest.mark.asyncio
async def test_deactivate_duplicate_reminders():
    """Test deactivating duplicate reminders"""
    user_id = "123456789"

    mock_cursor = AsyncMock()
    mock_cursor.fetchall.return_value = [
        {"type": "food_log", "time": "12:00", "user_id": user_id}
    ]

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        result = await queries.deactivate_duplicate_reminders(user_id)

        assert "deactivated" in result
        mock_conn.commit.assert_called()


# ============================================================================
# Conversation History Tests
# ============================================================================

@pytest.mark.asyncio
async def test_save_conversation_message():
    """Test saving a conversation message"""
    user_id = "123456789"
    role = "user"
    content = "Hello, how many calories in an apple?"

    mock_cursor = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        await queries.save_conversation_message(user_id, role, content)

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_conversation_history():
    """Test retrieving conversation history"""
    user_id = "123456789"

    mock_messages = [
        {
            "role": "user",
            "content": "Hello",
            "timestamp": datetime.now(timezone.utc)
        },
        {
            "role": "assistant",
            "content": "Hi there!",
            "timestamp": datetime.now(timezone.utc)
        }
    ]

    mock_cursor = AsyncMock()
    mock_cursor.fetchall.return_value = mock_messages

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        history = await queries.get_conversation_history(user_id, limit=50)

        assert len(history) == 2
        assert history[0]["role"] == "user"


@pytest.mark.asyncio
async def test_clear_conversation_history():
    """Test clearing conversation history"""
    user_id = "123456789"

    mock_cursor = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        await queries.clear_conversation_history(user_id)

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()


# ============================================================================
# Tracking Operations Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_tracking_category():
    """Test creating a tracking category"""
    category = TrackingCategory(
        user_id="123456789",
        name="Water Intake",
        category_type="water",
        icon="💧",
        fields=[
            TrackingField(name="amount", field_type="number", unit="ml")
        ]
    )

    mock_cursor = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        await queries.create_tracking_category(category)

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_tracking_categories():
    """Test retrieving tracking categories"""
    user_id = "123456789"

    mock_categories = [
        {
            "id": str(uuid4()),
            "user_id": user_id,
            "name": "Water Intake",
            "active": True
        }
    ]

    mock_cursor = AsyncMock()
    mock_cursor.fetchall.return_value = mock_categories

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        categories = await queries.get_tracking_categories(user_id)

        assert len(categories) == 1
        assert categories[0]["active"] is True


@pytest.mark.asyncio
async def test_save_tracking_entry():
    """Test saving a tracking entry"""
    entry = TrackingEntry(
        user_id="123456789",
        category_id=str(uuid4()),
        timestamp=datetime.now(timezone.utc),
        values={"amount": 500}
    )

    mock_cursor = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        await queries.save_tracking_entry(entry)

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()


# ============================================================================
# Dynamic Tools Tests
# ============================================================================

@pytest.mark.asyncio
async def test_save_dynamic_tool():
    """Test saving a dynamic tool"""
    user_id = "123456789"
    tool_name = "calculate_bmi"
    tool_code = "def calculate_bmi(weight, height): return weight / (height ** 2)"

    mock_cursor = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        await queries.save_dynamic_tool(
            user_id=user_id,
            tool_name=tool_name,
            tool_code=tool_code,
            description="Calculate BMI"
        )

        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_enabled_tools():
    """Test retrieving all enabled tools"""
    mock_tools = [
        {
            "id": str(uuid4()),
            "name": "calculate_bmi",
            "enabled": True
        }
    ]

    mock_cursor = AsyncMock()
    mock_cursor.fetchall.return_value = mock_tools

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        tools = await queries.get_all_enabled_tools()

        assert len(tools) >= 0
        mock_cursor.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_tool_by_name():
    """Test retrieving a tool by name"""
    tool_name = "calculate_bmi"

    mock_tool = {
        "id": str(uuid4()),
        "name": tool_name,
        "enabled": True
    }

    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = mock_tool

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        tool = await queries.get_tool_by_name(tool_name)

        assert tool is not None
        assert tool["name"] == tool_name


@pytest.mark.asyncio
async def test_disable_tool():
    """Test disabling a tool"""
    tool_id = str(uuid4())

    mock_cursor = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        await queries.disable_tool(tool_id)

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()


@pytest.mark.asyncio
async def test_enable_tool():
    """Test enabling a tool"""
    tool_id = str(uuid4())

    mock_cursor = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        await queries.enable_tool(tool_id)

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()


# ============================================================================
# Onboarding Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_onboarding_state():
    """Test retrieving onboarding state"""
    user_id = "123456789"

    mock_state = {
        "user_id": user_id,
        "path": "quick_start",
        "current_step": "focus_selection",
        "completed": False
    }

    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = mock_state

    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        state = await queries.get_onboarding_state(user_id)

        assert state is not None
        assert state["path"] == "quick_start"


@pytest.mark.asyncio
async def test_start_onboarding():
    """Test starting onboarding"""
    user_id = "123456789"
    path = "full_tour"

    mock_cursor = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        await queries.start_onboarding(user_id, path)

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_onboarding_step():
    """Test updating onboarding step"""
    user_id = "123456789"
    step = "language_selection"

    mock_cursor = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()

    with patch('src.db.queries.db.connection') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        await queries.update_onboarding_step(user_id, step, data={"language": "en"})

        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()
