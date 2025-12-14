"""Unit tests for memory file management"""
import pytest
import tempfile
from pathlib import Path
from src.memory.file_manager import MemoryFileManager


@pytest.fixture
def temp_data_dir():
    """Create temporary directory for test data"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def memory_manager(temp_data_dir):
    """Create memory manager with temporary directory"""
    return MemoryFileManager(data_path=temp_data_dir)


@pytest.mark.asyncio
async def test_create_user_files(memory_manager, temp_data_dir):
    """Test creating memory files for new user"""
    user_id = "test_user_123"

    await memory_manager.create_user_files(user_id)

    # Check that user directory exists
    user_dir = temp_data_dir / user_id
    assert user_dir.exists()
    assert user_dir.is_dir()

    # Check that all files exist
    assert (user_dir / "profile.md").exists()
    assert (user_dir / "preferences.md").exists()
    assert (user_dir / "patterns.md").exists()
    assert (user_dir / "food_history.md").exists()


@pytest.mark.asyncio
async def test_read_file(memory_manager):
    """Test reading a memory file"""
    user_id = "test_user_123"
    await memory_manager.create_user_files(user_id)

    content = await memory_manager.read_file(user_id, "profile.md")

    assert isinstance(content, str)
    assert len(content) > 0
    assert "Profile" in content or "profile" in content


@pytest.mark.asyncio
async def test_write_file(memory_manager, temp_data_dir):
    """Test writing to a memory file"""
    user_id = "test_user_123"
    await memory_manager.create_user_files(user_id)

    test_content = "# Test Content\nThis is a test"
    await memory_manager.write_file(user_id, "test.md", test_content)

    # Verify file was written
    file_path = temp_data_dir / user_id / "test.md"
    assert file_path.exists()
    assert file_path.read_text() == test_content


@pytest.mark.asyncio
async def test_load_user_memory(memory_manager):
    """Test loading all memory files"""
    user_id = "test_user_123"
    await memory_manager.create_user_files(user_id)

    memory = await memory_manager.load_user_memory(user_id)

    assert isinstance(memory, dict)
    assert "profile" in memory
    assert "preferences" in memory
    assert "patterns" in memory
    assert "food_history" in memory


@pytest.mark.asyncio
async def test_update_profile(memory_manager):
    """Test updating profile field"""
    user_id = "test_user_123"
    await memory_manager.create_user_files(user_id)

    # Update profile
    await memory_manager.update_profile(user_id, "name", "John Doe")

    # Verify update
    content = await memory_manager.read_file(user_id, "profile.md")
    assert "John Doe" in content
    assert "name" in content or "Name" in content


@pytest.mark.asyncio
async def test_update_preferences(memory_manager):
    """Test updating preference"""
    user_id = "test_user_123"
    await memory_manager.create_user_files(user_id)

    # Update preference
    await memory_manager.update_preferences(user_id, "brevity", "brief")

    # Verify update
    content = await memory_manager.read_file(user_id, "preferences.md")
    assert "brief" in content
    assert "brevity" in content or "Brevity" in content


@pytest.mark.asyncio
async def test_create_user_files_idempotent(memory_manager):
    """Test that creating files twice doesn't overwrite"""
    user_id = "test_user_123"

    # Create files
    await memory_manager.create_user_files(user_id)

    # Write custom content
    await memory_manager.write_file(user_id, "profile.md", "Custom content")

    # Create files again
    await memory_manager.create_user_files(user_id)

    # Verify custom content is preserved (files exist, so not overwritten)
    content = await memory_manager.read_file(user_id, "profile.md")
    assert "Custom content" in content
