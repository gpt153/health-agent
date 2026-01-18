"""Integration tests for Telegram bot handlers"""
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime, timezone

from src.bot import (
    should_process_message,
    start_command,
    help_command,
    stats_command,
    clear_command,
    handle_message,
    handle_photo,
    handle_voice,
)


# ============================================================================
# Message Filtering Tests
# ============================================================================

def test_should_process_message_private_chat():
    """Test that private chats are always processed"""
    update = Mock()
    update.message = Mock()
    update.message.chat.type = "private"
    update.message.message_thread_id = None

    assert should_process_message(update) is True


def test_should_process_message_group_no_topic_all_filter():
    """Test group message with no topic and 'all' filter"""
    update = Mock()
    update.message = Mock()
    update.message.chat.type = "group"
    update.message.message_thread_id = None

    with patch('src.bot.TELEGRAM_TOPIC_FILTER', 'all'):
        assert should_process_message(update) is True


def test_should_process_message_group_no_topic_none_filter():
    """Test group message with no topic and 'none' filter"""
    update = Mock()
    update.message = Mock()
    update.message.chat.type = "group"
    update.message.message_thread_id = None

    with patch('src.bot.TELEGRAM_TOPIC_FILTER', 'none'):
        assert should_process_message(update) is True


def test_should_process_message_group_with_topic_whitelist():
    """Test group message with topic on whitelist"""
    update = Mock()
    update.message = Mock()
    update.message.chat.type = "supergroup"
    update.message.message_thread_id = 10

    with patch('src.bot.TELEGRAM_TOPIC_FILTER', '10,20,30'):
        assert should_process_message(update) is True


def test_should_process_message_group_with_topic_not_on_whitelist():
    """Test group message with topic not on whitelist"""
    update = Mock()
    update.message = Mock()
    update.message.chat.type = "supergroup"
    update.message.message_thread_id = 99

    with patch('src.bot.TELEGRAM_TOPIC_FILTER', '10,20,30'):
        assert should_process_message(update) is False


def test_should_process_message_group_with_topic_blacklist():
    """Test group message with topic on blacklist"""
    update = Mock()
    update.message = Mock()
    update.message.chat.type = "supergroup"
    update.message.message_thread_id = 10

    with patch('src.bot.TELEGRAM_TOPIC_FILTER', '!10,20'):
        assert should_process_message(update) is False


def test_should_process_message_group_with_topic_not_blacklisted():
    """Test group message with topic not on blacklist"""
    update = Mock()
    update.message = Mock()
    update.message.chat.type = "supergroup"
    update.message.message_thread_id = 30

    with patch('src.bot.TELEGRAM_TOPIC_FILTER', '!10,20'):
        assert should_process_message(update) is True


# ============================================================================
# Start Command Tests
# ============================================================================

@pytest.mark.asyncio
async def test_start_command_new_user(mock_telegram_update, mock_telegram_context):
    """Test /start command for new user"""
    user_id = "123456789"
    mock_telegram_update.effective_user.id = int(user_id)

    with patch('src.bot.is_authorized', return_value=True):
        with patch('src.bot.user_exists', AsyncMock(return_value=False)):
            with patch('src.bot.create_user', AsyncMock()) as mock_create:
                with patch('src.bot.handle_onboarding_start', AsyncMock()):
                    await start_command(mock_telegram_update, mock_telegram_context)

                    mock_create.assert_called_once_with(user_id)


@pytest.mark.asyncio
async def test_start_command_existing_user(mock_telegram_update, mock_telegram_context):
    """Test /start command for existing user"""
    user_id = "123456789"
    mock_telegram_update.effective_user.id = int(user_id)

    with patch('src.bot.is_authorized', return_value=True):
        with patch('src.bot.user_exists', AsyncMock(return_value=True)):
            with patch('src.bot.handle_onboarding_start', AsyncMock()):
                await start_command(mock_telegram_update, mock_telegram_context)

                # Should still trigger onboarding start
                mock_telegram_update.message.reply_text.assert_called()


@pytest.mark.asyncio
async def test_start_command_unauthorized_user(mock_telegram_update, mock_telegram_context):
    """Test /start command with unauthorized user"""
    with patch('src.bot.is_authorized', return_value=False):
        await start_command(mock_telegram_update, mock_telegram_context)

        # Should send unauthorized message
        mock_telegram_update.message.reply_text.assert_called()
        call_args = mock_telegram_update.message.reply_text.call_args[0][0]
        assert "authorized" in call_args.lower()


# ============================================================================
# Help Command Tests
# ============================================================================

@pytest.mark.asyncio
async def test_help_command(mock_telegram_update, mock_telegram_context):
    """Test /help command"""
    with patch('src.bot.is_authorized', return_value=True):
        await help_command(mock_telegram_update, mock_telegram_context)

        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args[0][0]
        assert "help" in call_args.lower() or "command" in call_args.lower()


# ============================================================================
# Stats Command Tests
# ============================================================================

@pytest.mark.asyncio
async def test_stats_command(mock_telegram_update, mock_telegram_context, test_user_id):
    """Test /stats command"""
    mock_telegram_update.effective_user.id = int(test_user_id)

    mock_stats = {
        "total_food_entries": 50,
        "total_calories": 75000,
        "current_streak": 7,
        "total_xp": 1500,
        "level": 8,
    }

    with patch('src.bot.is_authorized', return_value=True):
        with patch('src.bot.get_user_stats', AsyncMock(return_value=mock_stats)):
            await stats_command(mock_telegram_update, mock_telegram_context)

            mock_telegram_update.message.reply_text.assert_called_once()


# ============================================================================
# Clear Command Tests
# ============================================================================

@pytest.mark.asyncio
async def test_clear_command(mock_telegram_update, mock_telegram_context, test_user_id):
    """Test /clear command to clear conversation history"""
    mock_telegram_update.effective_user.id = int(test_user_id)

    with patch('src.bot.is_authorized', return_value=True):
        with patch('src.bot.clear_conversation_history', AsyncMock()) as mock_clear:
            await clear_command(mock_telegram_update, mock_telegram_context)

            mock_clear.assert_called_once_with(test_user_id)
            mock_telegram_update.message.reply_text.assert_called_once()


# ============================================================================
# Message Handler Tests
# ============================================================================

@pytest.mark.asyncio
async def test_handle_message_authorized(mock_telegram_update, mock_telegram_context, test_user_id):
    """Test handling a text message from authorized user"""
    mock_telegram_update.effective_user.id = int(test_user_id)
    mock_telegram_update.message.text = "How many calories in an apple?"

    mock_response = "A medium apple contains about 95 calories."

    with patch('src.bot.should_process_message', return_value=True):
        with patch('src.bot.is_authorized', return_value=True):
            with patch('src.bot.get_agent_response', AsyncMock(return_value=mock_response)):
                with patch('src.bot.save_conversation_message', AsyncMock()):
                    await handle_message(mock_telegram_update, mock_telegram_context)

                    mock_telegram_update.message.reply_text.assert_called()


@pytest.mark.asyncio
async def test_handle_message_filtered_out(mock_telegram_update, mock_telegram_context):
    """Test message filtered out by topic filter"""
    with patch('src.bot.should_process_message', return_value=False):
        await handle_message(mock_telegram_update, mock_telegram_context)

        # Should not reply
        mock_telegram_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_handle_message_unauthorized(mock_telegram_update, mock_telegram_context):
    """Test handling message from unauthorized user"""
    with patch('src.bot.should_process_message', return_value=True):
        with patch('src.bot.is_authorized', return_value=False):
            await handle_message(mock_telegram_update, mock_telegram_context)

            # Should send unauthorized message
            mock_telegram_update.message.reply_text.assert_called()


@pytest.mark.asyncio
async def test_handle_message_saves_conversation(mock_telegram_update, mock_telegram_context, test_user_id):
    """Test that conversation is saved to database"""
    mock_telegram_update.effective_user.id = int(test_user_id)
    user_message = "Tell me about protein"
    mock_telegram_update.message.text = user_message
    agent_response = "Protein is essential for building muscle."

    with patch('src.bot.should_process_message', return_value=True):
        with patch('src.bot.is_authorized', return_value=True):
            with patch('src.bot.get_agent_response', AsyncMock(return_value=agent_response)):
                with patch('src.bot.save_conversation_message', AsyncMock()) as mock_save:
                    await handle_message(mock_telegram_update, mock_telegram_context)

                    # Should save both user message and agent response
                    assert mock_save.call_count == 2


# ============================================================================
# Photo Handler Tests
# ============================================================================

@pytest.mark.asyncio
async def test_handle_photo_authorized(mock_telegram_update, mock_telegram_context, test_user_id, mock_vision_analysis):
    """Test handling a photo upload"""
    mock_telegram_update.effective_user.id = int(test_user_id)
    mock_telegram_update.message.photo = [Mock()]  # Photo array
    mock_telegram_update.message.photo[-1].file_id = "photo_123"

    mock_file = Mock()
    mock_file.file_path = "/tmp/photo.jpg"
    mock_telegram_context.bot.get_file = AsyncMock(return_value=mock_file)

    with patch('src.bot.should_process_message', return_value=True):
        with patch('src.bot.is_authorized', return_value=True):
            with patch('src.bot.analyze_food_photo', AsyncMock(return_value=mock_vision_analysis)):
                with patch('src.bot.save_food_entry', AsyncMock()):
                    with patch('src.bot.handle_food_entry_gamification', AsyncMock()):
                        await handle_photo(mock_telegram_update, mock_telegram_context)

                        # Should reply with analysis
                        mock_telegram_update.message.reply_text.assert_called()


@pytest.mark.asyncio
async def test_handle_photo_no_food_detected(mock_telegram_update, mock_telegram_context, test_user_id):
    """Test handling photo with no food detected"""
    mock_telegram_update.effective_user.id = int(test_user_id)
    mock_telegram_update.message.photo = [Mock()]
    mock_telegram_update.message.photo[-1].file_id = "photo_123"

    mock_file = Mock()
    mock_file.file_path = "/tmp/photo.jpg"
    mock_telegram_context.bot.get_file = AsyncMock(return_value=mock_file)

    # Empty vision analysis
    empty_analysis = {
        "food_items": [],
        "total_calories": 0
    }

    with patch('src.bot.should_process_message', return_value=True):
        with patch('src.bot.is_authorized', return_value=True):
            with patch('src.bot.analyze_food_photo', AsyncMock(return_value=empty_analysis)):
                await handle_photo(mock_telegram_update, mock_telegram_context)

                # Should send message about no food detected
                mock_telegram_update.message.reply_text.assert_called()


# ============================================================================
# Voice Handler Tests
# ============================================================================

@pytest.mark.asyncio
async def test_handle_voice_authorized(mock_telegram_update, mock_telegram_context, test_user_id):
    """Test handling a voice message"""
    mock_telegram_update.effective_user.id = int(test_user_id)
    mock_telegram_update.message.voice = Mock()
    mock_telegram_update.message.voice.file_id = "voice_123"

    mock_file = Mock()
    mock_file.file_path = "/tmp/voice.ogg"
    mock_telegram_context.bot.get_file = AsyncMock(return_value=mock_file)

    transcription = "I ate a chicken salad for lunch"

    with patch('src.bot.should_process_message', return_value=True):
        with patch('src.bot.is_authorized', return_value=True):
            with patch('src.bot.transcribe_voice', AsyncMock(return_value=transcription)):
                with patch('src.bot.get_agent_response', AsyncMock(return_value="Got it!")):
                    with patch('src.bot.save_conversation_message', AsyncMock()):
                        await handle_voice(mock_telegram_update, mock_telegram_context)

                        # Should process transcribed message
                        mock_telegram_update.message.reply_text.assert_called()


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_handle_message_exception_handling(mock_telegram_update, mock_telegram_context):
    """Test that exceptions in message handling are caught"""
    with patch('src.bot.should_process_message', return_value=True):
        with patch('src.bot.is_authorized', return_value=True):
            with patch('src.bot.get_agent_response', AsyncMock(side_effect=Exception("Test error"))):
                # Should not raise exception
                await handle_message(mock_telegram_update, mock_telegram_context)

                # Should send error message to user
                mock_telegram_update.message.reply_text.assert_called()


@pytest.mark.asyncio
async def test_handle_photo_exception_handling(mock_telegram_update, mock_telegram_context):
    """Test that exceptions in photo handling are caught"""
    mock_telegram_update.message.photo = [Mock()]
    mock_telegram_update.message.photo[-1].file_id = "photo_123"

    with patch('src.bot.should_process_message', return_value=True):
        with patch('src.bot.is_authorized', return_value=True):
            with patch('src.bot.analyze_food_photo', AsyncMock(side_effect=Exception("Vision API error"))):
                # Should not raise exception
                await handle_photo(mock_telegram_update, mock_telegram_context)

                # Should send error message
                mock_telegram_update.message.reply_text.assert_called()


# ============================================================================
# Gamification Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_handle_photo_triggers_gamification(mock_telegram_update, mock_telegram_context, test_user_id, mock_vision_analysis):
    """Test that photo upload triggers gamification"""
    mock_telegram_update.effective_user.id = int(test_user_id)
    mock_telegram_update.message.photo = [Mock()]
    mock_telegram_update.message.photo[-1].file_id = "photo_123"

    mock_file = Mock()
    mock_file.file_path = "/tmp/photo.jpg"
    mock_telegram_context.bot.get_file = AsyncMock(return_value=mock_file)

    with patch('src.bot.should_process_message', return_value=True):
        with patch('src.bot.is_authorized', return_value=True):
            with patch('src.bot.analyze_food_photo', AsyncMock(return_value=mock_vision_analysis)):
                with patch('src.bot.save_food_entry', AsyncMock()):
                    with patch('src.bot.handle_food_entry_gamification', AsyncMock()) as mock_gamif:
                        await handle_photo(mock_telegram_update, mock_telegram_context)

                        # Should trigger gamification
                        mock_gamif.assert_called_once()
