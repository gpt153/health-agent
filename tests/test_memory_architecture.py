"""
Tests for memory architecture cleanup

Verifies that redundant markdown files are no longer created
and that audit trails are properly logged.
"""

import pytest
from pathlib import Path
from src.memory.file_manager import MemoryFileManager
from src.config import DATA_PATH


@pytest.mark.asyncio
async def test_redundant_files_not_created():
    """Verify patterns.md, food_history.md, visual_patterns.md are not created"""
    manager = MemoryFileManager()
    test_user_id = "test_memory_arch_user"

    # Create user files
    await manager.create_user_files(test_user_id)

    user_dir = manager.get_user_dir(test_user_id)

    # Should exist
    assert (user_dir / "profile.md").exists(), "profile.md should be created"
    assert (user_dir / "preferences.md").exists(), "preferences.md should be created"

    # Should NOT exist
    assert not (user_dir / "patterns.md").exists(), "patterns.md should NOT be created"
    assert not (user_dir / "food_history.md").exists(), "food_history.md should NOT be created"
    assert not (user_dir / "visual_patterns.md").exists(), "visual_patterns.md should NOT be created"

    # Cleanup
    import shutil
    if user_dir.exists():
        shutil.rmtree(user_dir)


@pytest.mark.asyncio
async def test_load_user_memory_only_returns_profile_and_preferences():
    """Verify load_user_memory only loads profile and preferences"""
    manager = MemoryFileManager()
    test_user_id = "test_memory_load_user"

    # Create user files
    await manager.create_user_files(test_user_id)

    # Load memory
    memory = await manager.load_user_memory(test_user_id)

    # Should only have profile and preferences
    assert "profile" in memory, "profile should be in memory"
    assert "preferences" in memory, "preferences should be in memory"
    assert "patterns" not in memory, "patterns should NOT be in memory"
    assert "food_history" not in memory, "food_history should NOT be in memory"
    assert "visual_patterns" not in memory, "visual_patterns should NOT be in memory"

    # Cleanup
    import shutil
    user_dir = manager.get_user_dir(test_user_id)
    if user_dir.exists():
        shutil.rmtree(user_dir)


@pytest.mark.asyncio
async def test_profile_update_calls_audit():
    """Verify profile updates call audit function (integration test)"""
    from unittest.mock import AsyncMock, patch

    manager = MemoryFileManager()
    test_user_id = "test_profile_audit_user"

    # Create user files
    await manager.create_user_files(test_user_id)

    # Mock the audit function
    with patch('src.memory.file_manager.audit_profile_update', new_callable=AsyncMock) as mock_audit:
        # Update profile
        await manager.update_profile(test_user_id, "height", "180cm")

        # Verify audit was called
        mock_audit.assert_called_once()
        args = mock_audit.call_args[0]
        assert args[0] == test_user_id
        assert args[1] == "height"
        assert args[3] == "180cm"

    # Cleanup
    import shutil
    user_dir = manager.get_user_dir(test_user_id)
    if user_dir.exists():
        shutil.rmtree(user_dir)


@pytest.mark.asyncio
async def test_preference_update_calls_audit():
    """Verify preference updates call audit function (integration test)"""
    from unittest.mock import AsyncMock, patch

    manager = MemoryFileManager()
    test_user_id = "test_pref_audit_user"

    # Create user files
    await manager.create_user_files(test_user_id)

    # Mock the audit function
    with patch('src.memory.file_manager.audit_preference_update', new_callable=AsyncMock) as mock_audit:
        # Update preference
        await manager.update_preferences(test_user_id, "Tone", "casual")

        # Verify audit was called
        mock_audit.assert_called_once()
        args = mock_audit.call_args[0]
        assert args[0] == test_user_id
        assert args[1] == "Tone"
        assert args[3] == "casual"

    # Cleanup
    import shutil
    user_dir = manager.get_user_dir(test_user_id)
    if user_dir.exists():
        shutil.rmtree(user_dir)
