"""Tests for system prompt generation - Issue #18 fix verification"""
import pytest
from src.memory.system_prompt import generate_system_prompt


def test_system_prompt_includes_sleep_quiz_instruction():
    """
    Test that the system prompt includes sleep quiz instructions.

    This test verifies the fix for GitHub issue #18:
    When users ask to log sleep, AI should direct them to /sleep_quiz command.
    """
    # Arrange - minimal user memory
    user_memory = {
        "profile": "Name: Test User\nTimezone: UTC",
        "preferences": "",
        "patterns": ""
    }

    # Act - generate system prompt
    prompt = generate_system_prompt(user_memory, user_id="test_user", current_query="log my sleep")

    # Assert - verify sleep tracking instructions are present
    assert "Sleep Tracking:" in prompt, "System prompt should include 'Sleep Tracking:' section"
    assert "/sleep_quiz" in prompt, "System prompt should mention /sleep_quiz command"
    assert "log my sleep" in prompt or "track sleep" in prompt, "Should mention sleep logging phrases"
    assert "DO NOT try to collect this data conversationally" in prompt, "Should explicitly prevent conversational collection"


def test_system_prompt_sleep_quiz_mentions_button_ui():
    """Test that sleep quiz instruction emphasizes the button-based UI."""
    user_memory = {
        "profile": "Timezone: Europe/Stockholm",
        "preferences": "",
        "patterns": ""
    }

    prompt = generate_system_prompt(user_memory)

    # Should mention the interactive nature and buttons
    assert "interactive" in prompt.lower() or "buttons" in prompt.lower(), \
        "Should emphasize interactive/button UI"
    assert "8-question" in prompt or "survey" in prompt, \
        "Should mention it's an 8-question survey"


def test_system_prompt_sleep_quiz_lists_captured_data():
    """Test that sleep quiz instruction lists what data it captures."""
    user_memory = {
        "profile": "",
        "preferences": "",
        "patterns": ""
    }

    prompt = generate_system_prompt(user_memory)

    # Should list key data points captured by the quiz
    expected_data_points = [
        "Bedtime",
        "wake time",
        "Sleep latency",
        "Night wakings",
        "Sleep quality",
        "Phone usage",
        "disruptions",
        "alertness"
    ]

    for data_point in expected_data_points:
        assert data_point.lower() in prompt.lower(), \
            f"Should mention '{data_point}' as captured data"


def test_system_prompt_basic_structure_intact():
    """Test that adding sleep instructions doesn't break basic prompt structure."""
    user_memory = {
        "profile": "Name: Test\nTimezone: UTC",
        "preferences": "Brevity: brief",
        "patterns": ""
    }

    prompt = generate_system_prompt(user_memory)

    # Verify core sections still exist
    assert "Communication Style:" in prompt
    assert "Your Capabilities:" in prompt
    assert "Sleep Tracking:" in prompt  # New section
    assert "CRITICAL SAFETY RULES" in prompt
    assert "<user_context>" in prompt


def test_system_prompt_sleep_variations():
    """Test that sleep instruction mentions various ways users might ask."""
    user_memory = {"profile": "", "preferences": "", "patterns": ""}

    prompt = generate_system_prompt(user_memory)

    # Should mention various phrases users might use
    sleep_phrases = ["log my sleep", "track sleep", "I slept", "record my night"]

    # At least some of these phrases should be mentioned as examples
    found_phrases = [phrase for phrase in sleep_phrases if phrase in prompt.lower()]
    assert len(found_phrases) >= 2, \
        f"Should mention at least 2 sleep logging phrases, found: {found_phrases}"
