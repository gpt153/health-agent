"""Integration tests for end-to-end food photo workflow"""
import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch
from src.memory.file_manager import MemoryFileManager
from src.models.food import FoodItem, FoodMacros, VisionAnalysisResult
from src.utils.vision import analyze_food_photo


@pytest.fixture
def temp_data_dir():
    """Create temporary directory for test data"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def memory_manager(temp_data_dir):
    """Create memory manager with temporary directory"""
    return MemoryFileManager(data_path=temp_data_dir)


@pytest.fixture
def mock_vision_result():
    """Mock vision AI result"""
    return VisionAnalysisResult(
        foods=[
            FoodItem(
                name="Grilled Chicken",
                quantity="200g",
                calories=330,
                macros=FoodMacros(protein=62.0, carbs=0.0, fat=7.0),
            ),
            FoodItem(
                name="Brown Rice",
                quantity="1 cup",
                calories=218,
                macros=FoodMacros(protein=5.0, carbs=45.0, fat=1.6),
            ),
        ],
        confidence="high",
        clarifying_questions=[],
    )


@pytest.mark.asyncio
async def test_complete_food_photo_workflow(
    memory_manager, temp_data_dir, mock_vision_result
):
    """Test complete workflow: photo upload -> analysis -> storage"""
    user_id = "test_user_123"

    # Setup: Create user
    await memory_manager.create_user_files(user_id)

    # Create fake photo
    photo_path = temp_data_dir / user_id / "photos" / "test_food.jpg"
    photo_path.parent.mkdir(parents=True, exist_ok=True)
    photo_path.write_bytes(b"fake image data")

    # Mock vision analysis
    with patch("src.utils.vision.analyze_food_photo", return_value=mock_vision_result):
        result = await analyze_food_photo(str(photo_path))

        # Verify analysis result
        assert isinstance(result, VisionAnalysisResult)
        assert len(result.foods) == 2
        assert result.confidence == "high"

        # Calculate totals
        total_calories = sum(f.calories for f in result.foods)
        total_protein = sum(f.macros.protein for f in result.foods)

        assert total_calories == 548  # 330 + 218
        assert total_protein == 67.0  # 62 + 5


@pytest.mark.asyncio
async def test_user_memory_persistence(memory_manager):
    """Test that user memory persists across sessions"""
    user_id = "test_user_123"

    # Create user and update profile
    await memory_manager.create_user_files(user_id)
    await memory_manager.update_profile(user_id, "name", "Test User")
    await memory_manager.update_preferences(user_id, "brevity", "brief")

    # Simulate new session - create new manager instance
    memory_manager_2 = MemoryFileManager(data_path=memory_manager.data_path)

    # Load memory with new instance
    memory = await memory_manager_2.load_user_memory(user_id)

    # Verify data persisted
    assert "Test User" in memory["profile"]
    assert "brief" in memory["preferences"]


@pytest.mark.asyncio
async def test_multiple_profile_updates(memory_manager):
    """Test updating profile multiple times"""
    user_id = "test_user_123"

    await memory_manager.create_user_files(user_id)

    # Multiple updates
    await memory_manager.update_profile(user_id, "name", "John")
    await memory_manager.update_profile(user_id, "age", "30")
    await memory_manager.update_profile(user_id, "name", "John Doe")  # Update again

    # Verify latest values
    content = await memory_manager.read_file(user_id, "profile.md")

    assert "John Doe" in content
    assert "30" in content


@pytest.mark.asyncio
async def test_concurrent_memory_operations(memory_manager):
    """Test concurrent read/write operations"""
    user_id = "test_user_123"

    await memory_manager.create_user_files(user_id)

    # Run concurrent updates
    async def update_task(field, value):
        await memory_manager.update_profile(user_id, field, value)

    tasks = [
        update_task("name", "Alice"),
        update_task("age", "25"),
        update_task("goal_type", "lose_weight"),
    ]

    await asyncio.gather(*tasks)

    # Verify all updates applied
    content = await memory_manager.read_file(user_id, "profile.md")

    assert "Alice" in content
    assert "25" in content
    assert "lose_weight" in content
