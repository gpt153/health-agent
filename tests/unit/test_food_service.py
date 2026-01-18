"""Unit tests for FoodService"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date, timedelta
import sys

# Mock external dependencies before importing FoodService
sys.modules['psycopg'] = MagicMock()
sys.modules['psycopg_pool'] = MagicMock()
sys.modules['src.db.connection'] = MagicMock()
sys.modules['httpx'] = MagicMock()
sys.modules['src.utils.nutrition_search'] = MagicMock()
sys.modules['src.utils.vision'] = MagicMock()
sys.modules['src.agent.nutrition_validator'] = MagicMock()
sys.modules['src.memory.mem0_manager'] = MagicMock()
sys.modules['src.memory.habit_extractor'] = MagicMock()

from src.services.food_service import FoodService
from src.models.food import FoodItem, FoodMacros, VisionAnalysisResult


@pytest.fixture
def mock_db():
    """Mock database connection"""
    db = MagicMock()
    db.connection = AsyncMock()
    return db


@pytest.fixture
def mock_memory_manager():
    """Mock memory manager"""
    memory = AsyncMock()
    memory.load_user_memory = AsyncMock(return_value={'visual_patterns': 'test patterns'})
    return memory


@pytest.fixture
def food_service(mock_db, mock_memory_manager):
    """Create FoodService instance with mocks"""
    return FoodService(mock_db, mock_memory_manager)


@pytest.fixture
def sample_food_item():
    """Sample FoodItem for testing"""
    return FoodItem(
        name="Grilled Chicken Breast",
        quantity="100g",
        calories=165,
        macros=FoodMacros(protein=31.0, carbs=0.0, fat=3.6),
        verification_source="usda"
    )


@pytest.fixture
def sample_vision_result(sample_food_item):
    """Sample VisionAnalysisResult for testing"""
    return VisionAnalysisResult(
        foods=[sample_food_item],
        confidence="high",
        clarifying_questions=[],
        timestamp=datetime.now()
    )


# Test analyze_food_photo
@pytest.mark.asyncio
@patch('src.services.food_service.analyze_food_photo')
@patch('src.services.food_service.verify_food_items')
@patch('src.services.food_service.get_validator')
@patch('src.services.food_service.mem0_manager')
@patch('src.services.food_service.queries')
async def test_analyze_food_photo_success(
    mock_queries,
    mock_mem0,
    mock_get_validator,
    mock_verify,
    mock_analyze,
    food_service,
    sample_vision_result,
    sample_food_item
):
    """Test successful food photo analysis"""
    # Setup
    user_id = "12345"
    photo_path = "/path/to/photo.jpg"
    caption = "grilled chicken"

    # Mock Mem0 search
    mock_mem0.search = MagicMock(return_value={'results': []})

    # Mock database queries
    mock_queries.get_food_entries_by_date = AsyncMock(return_value=[])

    # Mock habit extractor
    with patch('src.services.food_service.habit_extractor') as mock_habit:
        mock_habit.get_user_habits = AsyncMock(return_value=[])

        # Mock vision analysis (async function)
        mock_analyze.return_value = sample_vision_result

        # Make it awaitable by wrapping in AsyncMock
        async def mock_vision_analysis(*args, **kwargs):
            return sample_vision_result
        mock_analyze.side_effect = mock_vision_analysis

        # Mock USDA verification (async function)
        async def mock_usda_verify(*args, **kwargs):
            return [sample_food_item]
        mock_verify.side_effect = mock_usda_verify

        # Mock validator
        mock_validator = MagicMock()
        mock_validator.validate = AsyncMock(return_value=(sample_vision_result, []))
        mock_get_validator.return_value = mock_validator

        # Execute
        result = await food_service.analyze_food_photo(user_id, photo_path, caption)

        # Assert
        assert result is not None
        assert 'foods' in result
        assert 'total_calories' in result
        assert 'total_macros' in result
        assert 'confidence' in result
        assert 'validation_warnings' in result
        assert 'clarifying_questions' in result
        assert 'timestamp' in result

        assert len(result['foods']) == 1
        assert result['total_calories'] == 165
        assert result['total_macros'].protein == 31.0
        assert result['confidence'] == "high"


@pytest.mark.asyncio
@patch('src.services.food_service.analyze_food_photo')
@patch('src.services.food_service.verify_food_items')
@patch('src.services.food_service.get_validator')
@patch('src.services.food_service.mem0_manager')
@patch('src.services.food_service.queries')
async def test_analyze_food_photo_with_validation_warnings(
    mock_queries,
    mock_mem0,
    mock_get_validator,
    mock_verify,
    mock_analyze,
    food_service,
    sample_vision_result,
    sample_food_item
):
    """Test food photo analysis with validation warnings"""
    # Setup
    user_id = "12345"
    photo_path = "/path/to/photo.jpg"
    warnings = ["Portion size seems unusually large"]

    mock_mem0.search = MagicMock(return_value={'results': []})
    mock_queries.get_food_entries_by_date = AsyncMock(return_value=[])

    with patch('src.services.food_service.habit_extractor') as mock_habit:
        mock_habit.get_user_habits = AsyncMock(return_value=[])

        # Mock vision analysis (async)
        async def mock_vision_analysis(*args, **kwargs):
            return sample_vision_result
        mock_analyze.side_effect = mock_vision_analysis

        # Mock USDA verification (async)
        async def mock_usda_verify(*args, **kwargs):
            return [sample_food_item]
        mock_verify.side_effect = mock_usda_verify

        # Mock validator with warnings
        mock_validator = MagicMock()
        mock_validator.validate = AsyncMock(return_value=(sample_vision_result, warnings))
        mock_get_validator.return_value = mock_validator

        # Execute
        result = await food_service.analyze_food_photo(user_id, photo_path)

        # Assert
        assert result['validation_warnings'] == warnings


@pytest.mark.asyncio
@patch('src.services.food_service.queries')
async def test_get_food_history_context_success(mock_queries, food_service, mock_memory_manager):
    """Test _get_food_history_context with recent foods"""
    # Setup
    user_id = "12345"
    recent_entries = [
        {
            'foods': '[{"food_name": "Chicken Breast", "quantity": "100g"}]',
            'total_calories': 165
        },
        {
            'foods': '[{"food_name": "Chicken Breast", "quantity": "100g"}]',
            'total_calories': 165
        },
        {
            'foods': '[{"food_name": "Rice", "quantity": "200g"}]',
            'total_calories': 260
        }
    ]

    mock_queries.get_food_entries_by_date = AsyncMock(return_value=recent_entries)

    # Execute
    context = await food_service._get_food_history_context(user_id)

    # Assert
    assert "Your recent eating patterns (last 7 days):" in context
    assert "Chicken Breast" in context
    assert "logged 2x this week" in context


@pytest.mark.asyncio
@patch('src.services.food_service.queries')
async def test_get_food_history_context_empty(mock_queries, food_service, mock_memory_manager):
    """Test _get_food_history_context with no recent foods"""
    # Setup
    user_id = "12345"
    mock_queries.get_food_entries_by_date = AsyncMock(return_value=[])

    # Execute
    context = await food_service._get_food_history_context(user_id)

    # Assert
    assert context == ""


@pytest.mark.asyncio
async def test_get_habit_context_success(food_service, mock_memory_manager):
    """Test _get_habit_context with user habits"""
    # Setup
    user_id = "12345"
    habits = [
        {
            'habit_key': 'oatmeal_prep',
            'habit_data': {
                'food': 'oatmeal',
                'liquid': 'whole_milk',
                'ratio': '1:2'
            },
            'confidence': 0.85
        }
    ]

    with patch('src.services.food_service.habit_extractor') as mock_habit:
        mock_habit.get_user_habits = AsyncMock(return_value=habits)

        # Execute
        context = await food_service._get_habit_context(user_id)

        # Assert
        assert "User's food preparation habits:" in context
        assert "oatmeal" in context
        assert "whole milk" in context
        assert "1:2 ratio" in context
        assert "85%" in context


@pytest.mark.asyncio
async def test_get_habit_context_empty(food_service, mock_memory_manager):
    """Test _get_habit_context with no habits"""
    # Setup
    user_id = "12345"

    with patch('src.services.food_service.habit_extractor') as mock_habit:
        mock_habit.get_user_habits = AsyncMock(return_value=[])

        # Execute
        context = await food_service._get_habit_context(user_id)

        # Assert
        assert context == ""


# Test log_food_entry
@pytest.mark.asyncio
@patch('src.services.food_service.queries')
async def test_log_food_entry_success(mock_queries, food_service, sample_food_item):
    """Test successful food entry logging"""
    # Setup
    user_id = "12345"
    photo_path = "/path/to/photo.jpg"
    foods = [sample_food_item]
    total_calories = 165
    total_macros = FoodMacros(protein=31.0, carbs=0.0, fat=3.6)
    timestamp = datetime.now()

    mock_queries.save_food_entry = AsyncMock()

    with patch('src.services.food_service.habit_extractor') as mock_habit:
        mock_habit.detect_food_prep_habit = AsyncMock()

        # Execute
        result = await food_service.log_food_entry(
            user_id=user_id,
            photo_path=photo_path,
            foods=foods,
            total_calories=total_calories,
            total_macros=total_macros,
            timestamp=timestamp,
            notes="Lunch"
        )

        # Assert
        assert result['success'] is True
        assert 'entry_id' in result
        assert result['entry'] is not None
        assert result['message'] == 'Food entry saved successfully'

        mock_queries.save_food_entry.assert_called_once()


@pytest.mark.asyncio
@patch('src.services.food_service.queries')
async def test_log_food_entry_failure(mock_queries, food_service, sample_food_item):
    """Test food entry logging failure"""
    # Setup
    user_id = "12345"
    photo_path = "/path/to/photo.jpg"
    foods = [sample_food_item]
    total_calories = 165
    total_macros = FoodMacros(protein=31.0, carbs=0.0, fat=3.6)
    timestamp = datetime.now()

    # Mock save_food_entry to raise exception
    mock_queries.save_food_entry = AsyncMock(side_effect=Exception("Database error"))

    # Execute
    result = await food_service.log_food_entry(
        user_id=user_id,
        photo_path=photo_path,
        foods=foods,
        total_calories=total_calories,
        total_macros=total_macros,
        timestamp=timestamp
    )

    # Assert
    assert result['success'] is False
    assert result['entry_id'] is None
    assert 'Error saving food entry' in result['message']


# Test get_food_entries
@pytest.mark.asyncio
@patch('src.services.food_service.queries')
async def test_get_food_entries_by_date_range(mock_queries, food_service):
    """Test getting food entries by date range"""
    # Setup
    user_id = "12345"
    start_date = date(2024, 1, 1)
    end_date = date(2024, 1, 7)
    mock_entries = [
        {'id': '1', 'total_calories': 500},
        {'id': '2', 'total_calories': 600}
    ]

    mock_queries.get_food_entries_by_date = AsyncMock(return_value=mock_entries)

    # Execute
    result = await food_service.get_food_entries(user_id, start_date, end_date)

    # Assert
    assert len(result) == 2
    assert result == mock_entries
    mock_queries.get_food_entries_by_date.assert_called_once_with(
        user_id, '2024-01-01', '2024-01-07'
    )


@pytest.mark.asyncio
@patch('src.services.food_service.queries')
async def test_get_food_entries_recent(mock_queries, food_service):
    """Test getting recent food entries without date range"""
    # Setup
    user_id = "12345"
    limit = 10
    mock_entries = [{'id': '1'}, {'id': '2'}, {'id': '3'}]

    mock_queries.get_recent_food_entries = AsyncMock(return_value=mock_entries)

    # Execute
    result = await food_service.get_food_entries(user_id, limit=limit)

    # Assert
    assert len(result) == 3
    mock_queries.get_recent_food_entries.assert_called_once_with(user_id, limit)


@pytest.mark.asyncio
@patch('src.services.food_service.queries')
async def test_get_food_entries_empty(mock_queries, food_service):
    """Test getting food entries with no results"""
    # Setup
    user_id = "12345"
    mock_queries.get_recent_food_entries = AsyncMock(return_value=None)

    # Execute
    result = await food_service.get_food_entries(user_id)

    # Assert
    assert result == []


# Test get_daily_nutrition_summary
@pytest.mark.asyncio
@patch('src.services.food_service.queries')
async def test_get_daily_nutrition_summary_with_entries(mock_queries, food_service):
    """Test daily nutrition summary with entries"""
    # Setup
    user_id = "12345"
    target_date = date(2024, 1, 15)
    mock_entries = [
        {
            'total_calories': 500,
            'total_macros': '{"protein": 30.0, "carbs": 40.0, "fat": 15.0}'
        },
        {
            'total_calories': 600,
            'total_macros': '{"protein": 35.0, "carbs": 50.0, "fat": 20.0}'
        }
    ]

    mock_queries.get_food_entries_by_date = AsyncMock(return_value=mock_entries)

    # Execute
    result = await food_service.get_daily_nutrition_summary(user_id, target_date)

    # Assert
    assert result['date'] == '2024-01-15'
    assert result['total_calories'] == 1100
    assert result['total_protein'] == 65.0
    assert result['total_carbs'] == 90.0
    assert result['total_fat'] == 35.0
    assert result['meal_count'] == 2
    assert len(result['entries']) == 2


@pytest.mark.asyncio
@patch('src.services.food_service.queries')
async def test_get_daily_nutrition_summary_no_entries(mock_queries, food_service):
    """Test daily nutrition summary with no entries"""
    # Setup
    user_id = "12345"
    target_date = date(2024, 1, 15)

    mock_queries.get_food_entries_by_date = AsyncMock(return_value=[])

    # Execute
    result = await food_service.get_daily_nutrition_summary(user_id, target_date)

    # Assert
    assert result['date'] == '2024-01-15'
    assert result['total_calories'] == 0
    assert result['total_protein'] == 0.0
    assert result['total_carbs'] == 0.0
    assert result['total_fat'] == 0.0
    assert result['meal_count'] == 0
    assert result['entries'] == []


@pytest.mark.asyncio
@patch('src.services.food_service.queries')
async def test_get_daily_nutrition_summary_error(mock_queries, food_service):
    """Test daily nutrition summary with database error"""
    # Setup
    user_id = "12345"
    target_date = date(2024, 1, 15)

    mock_queries.get_food_entries_by_date = AsyncMock(side_effect=Exception("DB error"))

    # Execute
    result = await food_service.get_daily_nutrition_summary(user_id, target_date)

    # Assert
    assert result['date'] == '2024-01-15'
    assert result['total_calories'] == 0
    assert 'error' in result
    assert result['error'] == "DB error"


# Test habit detection
@pytest.mark.asyncio
async def test_detect_food_habits_success(food_service, sample_food_item):
    """Test habit detection for food items"""
    # Setup
    user_id = "12345"
    foods = [sample_food_item]

    with patch('src.services.food_service.habit_extractor') as mock_habit:
        mock_habit.detect_food_prep_habit = AsyncMock()

        # Execute
        await food_service._detect_food_habits(user_id, foods)

        # Assert
        mock_habit.detect_food_prep_habit.assert_called_once()


@pytest.mark.asyncio
async def test_detect_food_habits_failure(food_service, sample_food_item):
    """Test habit detection handles errors gracefully"""
    # Setup
    user_id = "12345"
    foods = [sample_food_item]

    with patch('src.services.food_service.habit_extractor') as mock_habit:
        mock_habit.detect_food_prep_habit = AsyncMock(side_effect=Exception("Habit error"))

        # Execute - should not raise exception
        await food_service._detect_food_habits(user_id, foods)

        # No assertion needed - just verify it doesn't raise
