"""Global test fixtures and utilities for health-agent tests"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from datetime import datetime, date, timezone
from pathlib import Path
import tempfile
from zoneinfo import ZoneInfo


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
async def mock_db_connection():
    """Mock database connection with standard methods"""
    conn = AsyncMock()
    conn.cursor = AsyncMock()
    conn.commit = AsyncMock()
    conn.rollback = AsyncMock()
    conn.close = AsyncMock()
    return conn


@pytest.fixture
async def mock_db_cursor():
    """Mock database cursor with standard query results"""
    cursor = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=None)
    cursor.fetchall = AsyncMock(return_value=[])
    cursor.execute = AsyncMock()
    cursor.close = AsyncMock()
    return cursor


@pytest.fixture
def mock_db_pool():
    """Mock database connection pool"""
    pool = Mock()
    pool.connection = AsyncMock()
    return pool


# ============================================================================
# User & Auth Fixtures
# ============================================================================

@pytest.fixture
def test_user_id():
    """Standard test user ID"""
    return "123456789"


@pytest.fixture
def test_user_profile():
    """Standard test user profile"""
    return {
        "telegram_id": "123456789",
        "name": "Test User",
        "age": 30,
        "height_cm": 175.0,
        "current_weight_kg": 75.0,
        "target_weight_kg": 70.0,
        "goal_type": "lose_weight",
        "created_at": datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    }


@pytest.fixture
def test_api_key():
    """Standard test API key"""
    return "test_api_key_12345"


# ============================================================================
# Telegram Bot Fixtures
# ============================================================================

@pytest.fixture
def mock_telegram_user():
    """Mock Telegram User object"""
    user = Mock()
    user.id = 123456789
    user.first_name = "Test"
    user.last_name = "User"
    user.username = "testuser"
    user.is_bot = False
    return user


@pytest.fixture
def mock_telegram_chat():
    """Mock Telegram Chat object"""
    chat = Mock()
    chat.id = 123456789
    chat.type = "private"
    chat.first_name = "Test"
    chat.last_name = "User"
    return chat


@pytest.fixture
def mock_telegram_message(mock_telegram_user, mock_telegram_chat):
    """Mock Telegram Message object"""
    message = Mock()
    message.message_id = 1
    message.from_user = mock_telegram_user
    message.chat = mock_telegram_chat
    message.text = "Test message"
    message.date = datetime.now(timezone.utc)
    message.reply_text = AsyncMock()
    message.reply_photo = AsyncMock()
    message.reply_document = AsyncMock()
    message.edit_text = AsyncMock()
    return message


@pytest.fixture
def mock_telegram_update(mock_telegram_message):
    """Mock Telegram Update object"""
    update = Mock()
    update.update_id = 1
    update.message = mock_telegram_message
    update.effective_user = mock_telegram_message.from_user
    update.effective_chat = mock_telegram_message.chat
    update.effective_message = mock_telegram_message
    return update


@pytest.fixture
def mock_telegram_context():
    """Mock Telegram Context object"""
    context = Mock()
    context.bot = Mock()
    context.bot.send_message = AsyncMock()
    context.bot.send_photo = AsyncMock()
    context.bot.edit_message_text = AsyncMock()
    context.bot.get_file = AsyncMock()
    context.user_data = {}
    context.chat_data = {}
    context.bot_data = {}
    context.job_queue = Mock()
    context.job_queue.run_once = Mock()
    context.job_queue.run_repeating = Mock()
    return context


@pytest.fixture
def telegram_update_factory(mock_telegram_user, mock_telegram_chat):
    """Factory for creating custom Telegram updates"""
    def _create(text="", user_id=None, chat_type="private", **kwargs):
        if user_id:
            mock_telegram_user.id = int(user_id)

        message = Mock()
        message.message_id = kwargs.get("message_id", 1)
        message.from_user = mock_telegram_user
        message.chat = mock_telegram_chat
        message.chat.type = chat_type
        message.text = text
        message.date = kwargs.get("date", datetime.now(timezone.utc))
        message.reply_text = AsyncMock()
        message.reply_photo = AsyncMock()
        message.reply_document = AsyncMock()
        message.edit_text = AsyncMock()

        # Add photo if provided
        if "photo" in kwargs:
            message.photo = kwargs["photo"]

        # Add voice if provided
        if "voice" in kwargs:
            message.voice = kwargs["voice"]

        update = Mock()
        update.update_id = kwargs.get("update_id", 1)
        update.message = message
        update.effective_user = message.from_user
        update.effective_chat = message.chat
        update.effective_message = message

        return update

    return _create


# ============================================================================
# AI Client Fixtures
# ============================================================================

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    client = Mock()
    client.chat = Mock()
    client.chat.completions = Mock()
    client.chat.completions.create = AsyncMock()

    # Default response
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message = Mock()
    response.choices[0].message.content = "Test AI response"
    client.chat.completions.create.return_value = response

    return client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client"""
    client = Mock()
    client.messages = Mock()
    client.messages.create = AsyncMock()

    # Default response
    response = Mock()
    response.content = [Mock()]
    response.content[0].text = "Test AI response"
    client.messages.create.return_value = response

    return client


@pytest.fixture
def mock_vision_analysis():
    """Mock vision analysis result"""
    return {
        "food_items": [
            {
                "name": "Grilled Chicken Breast",
                "quantity": "150g",
                "calories": 165,
                "protein": 31.0,
                "carbs": 0.0,
                "fat": 3.6,
                "confidence": 0.85
            }
        ],
        "total_calories": 165,
        "total_protein": 31.0,
        "total_carbs": 0.0,
        "total_fat": 3.6
    }


# ============================================================================
# Time & Timezone Fixtures
# ============================================================================

@pytest.fixture
def frozen_time():
    """Freeze time to a specific moment for deterministic testing"""
    frozen = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    with patch('src.utils.datetime_helpers.now_utc', return_value=frozen):
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = frozen
            mock_datetime.utcnow.return_value = frozen
            yield frozen


@pytest.fixture
def test_timezone():
    """Standard test timezone (US/Eastern)"""
    return ZoneInfo("America/New_York")


# ============================================================================
# File & Directory Fixtures
# ============================================================================

@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_image_path(temp_data_dir):
    """Create a test image file"""
    from PIL import Image

    img_path = temp_data_dir / "test_image.jpg"
    img = Image.new('RGB', (100, 100), color='red')
    img.save(img_path)

    return img_path


# ============================================================================
# Gamification Fixtures
# ============================================================================

@pytest.fixture
def test_xp_data():
    """Standard test XP data"""
    return {
        "user_id": "123456789",
        "total_xp": 1500,
        "level": 5,
        "current_level_xp": 500,
        "next_level_xp": 1000,
    }


@pytest.fixture
def test_streak_data():
    """Standard test streak data"""
    return {
        "user_id": "123456789",
        "current_streak": 7,
        "best_streak": 14,
        "last_activity": date(2024, 1, 15),
        "freeze_count": 2,
    }


@pytest.fixture
def test_achievement_data():
    """Standard test achievement data"""
    return {
        "id": "first_food_log",
        "name": "First Steps",
        "description": "Log your first meal",
        "category": "food",
        "xp_reward": 50,
        "icon": "🎯",
    }


# ============================================================================
# Food & Nutrition Fixtures
# ============================================================================

@pytest.fixture
def test_food_item():
    """Standard test food item"""
    return {
        "name": "Grilled Chicken Breast",
        "quantity": "150g",
        "calories": 165,
        "protein": 31.0,
        "carbs": 0.0,
        "fat": 3.6,
        "fiber": 0.0,
        "sugar": 0.0,
    }


@pytest.fixture
def test_food_entry(test_user_id, test_food_item):
    """Standard test food entry"""
    return {
        "id": "entry_123",
        "user_id": test_user_id,
        "timestamp": datetime(2024, 1, 15, 12, 30, 0, tzinfo=timezone.utc),
        "meal_type": "lunch",
        "food_items": [test_food_item],
        "total_calories": 165,
        "total_protein": 31.0,
        "total_carbs": 0.0,
        "total_fat": 3.6,
        "notes": "Post-workout meal",
    }


@pytest.fixture
def mock_usda_api_response():
    """Mock USDA API nutrition search response"""
    return {
        "foods": [
            {
                "fdcId": 171477,
                "description": "Chicken, broilers or fryers, breast, meat only, cooked, roasted",
                "foodNutrients": [
                    {"nutrientName": "Energy", "value": 165, "unitName": "kcal"},
                    {"nutrientName": "Protein", "value": 31.0, "unitName": "g"},
                    {"nutrientName": "Carbohydrate, by difference", "value": 0, "unitName": "g"},
                    {"nutrientName": "Total lipid (fat)", "value": 3.6, "unitName": "g"},
                ],
            }
        ]
    }


# ============================================================================
# Reminder Fixtures
# ============================================================================

@pytest.fixture
def test_reminder():
    """Standard test reminder"""
    return {
        "id": "reminder_123",
        "user_id": "123456789",
        "type": "food_log",
        "time": "12:00",
        "timezone": "America/New_York",
        "days_of_week": [0, 1, 2, 3, 4],  # Mon-Fri
        "active": True,
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }


# ============================================================================
# Sleep Fixtures
# ============================================================================

@pytest.fixture
def test_sleep_data():
    """Standard test sleep data"""
    return {
        "user_id": "123456789",
        "date": date(2024, 1, 15),
        "bedtime": "23:00",
        "wake_time": "07:00",
        "duration_hours": 8.0,
        "quality": 4,  # 1-5 scale
        "notes": "Felt rested",
    }


# ============================================================================
# HTTP & API Fixtures
# ============================================================================

@pytest.fixture
def mock_httpx_client():
    """Mock httpx async client"""
    client = Mock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.delete = AsyncMock()

    # Default response
    response = Mock()
    response.status_code = 200
    response.json = Mock(return_value={})
    response.text = ""
    client.get.return_value = response
    client.post.return_value = response

    return client


# ============================================================================
# Environment & Config Fixtures
# ============================================================================

@pytest.fixture
def test_env_vars(monkeypatch):
    """Set standard test environment variables"""
    env_vars = {
        "DATABASE_URL": "postgresql://test:test@localhost/test_db",
        "TELEGRAM_BOT_TOKEN": "test_bot_token",
        "OPENAI_API_KEY": "test_openai_key",
        "ANTHROPIC_API_KEY": "test_anthropic_key",
        "API_SECRET_KEY": "test_secret_key",
        "ENVIRONMENT": "test",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


# ============================================================================
# Async Utilities
# ============================================================================

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
