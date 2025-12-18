"""Integration tests for onboarding flows"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.handlers.onboarding import (
    handle_onboarding_start,
    handle_path_selection,
    quick_start_complete,
    handle_onboarding_message
)


@pytest.fixture
def mock_user_id():
    """Standard test user ID"""
    return "789"


@pytest.fixture
def mock_update(mock_user_id):
    """Mock Telegram Update object"""
    update = Mock()
    update.effective_user.id = int(mock_user_id)
    update.message.text = ""
    update.message.reply_text = AsyncMock()
    update.message.location = None
    return update


@pytest.fixture
def mock_context():
    """Mock Telegram Context object"""
    context = Mock()
    context.user_data = {}
    context.bot.send_message = AsyncMock()
    return context


@pytest.mark.asyncio
class TestQuickStartFlow:
    """Test complete Quick Start onboarding flow"""

    @pytest.mark.asyncio
    async def test_complete_quick_start_flow(self, mock_update, mock_context, mock_user_id):
        """Test user completing entire Quick Start path"""

        # Step 1: Show path selection
        with patch("src.db.queries.get_onboarding_state", return_value=None):
            with patch("src.db.queries.start_onboarding", new_callable=AsyncMock):
                await handle_onboarding_start(mock_update, mock_context)

                # Verify path selection shown
                mock_update.message.reply_text.assert_called_once()
                call_args = mock_update.message.reply_text.call_args
                assert "How should we start" in call_args[0][0]

        # Step 2: User selects Quick Start
        mock_update.message.text = "Quick Start 🚀"
        with patch("src.db.queries.start_onboarding", new_callable=AsyncMock):
            with patch("src.handlers.onboarding.quick_start_timezone", new_callable=AsyncMock) as mock_tz:
                await handle_path_selection(mock_update, mock_context)

                # Verify routed to timezone setup
                mock_tz.assert_called_once()

        # Step 3: User sets timezone
        mock_update.message.text = "Europe/Stockholm"
        state_mock = {
            "onboarding_path": "quick",
            "current_step": "timezone_setup",
            "step_data": {},
            "completed_steps": [],
            "completed_at": None
        }

        with patch("src.db.queries.get_onboarding_state", return_value=state_mock):
            with patch("src.utils.timezone_helper.update_timezone_in_profile"):
                with patch("src.db.queries.update_onboarding_step", new_callable=AsyncMock):
                    with patch("src.handlers.onboarding.quick_start_focus_selection", new_callable=AsyncMock) as mock_focus:
                        await handle_onboarding_message(mock_update, mock_context)

                        # Verify advanced to focus selection
                        mock_focus.assert_called_once()

        # Step 4: User picks nutrition focus
        mock_update.message.text = "🍽️ Track nutrition"
        state_mock["current_step"] = "focus_selection"

        with patch("src.db.queries.get_onboarding_state", return_value=state_mock):
            with patch("src.db.queries.update_onboarding_step", new_callable=AsyncMock):
                with patch("src.db.queries.log_feature_discovery", new_callable=AsyncMock):
                    await handle_onboarding_message(mock_update, mock_context)

                    # Verify demo shown
                    assert mock_update.message.reply_text.called

        # Step 5: Complete onboarding
        with patch("src.db.queries.complete_onboarding", new_callable=AsyncMock) as mock_complete:
            await quick_start_complete(mock_update, mock_context)

            # Verify completion
            mock_complete.assert_called_once_with(mock_user_id)
            assert mock_update.message.reply_text.called


@pytest.mark.asyncio
class TestFullTourFlow:
    """Test complete Full Tour onboarding flow"""

    @pytest.mark.asyncio
    async def test_full_tour_path_selection(self, mock_update, mock_context):
        """Test selecting Full Tour path"""
        mock_update.message.text = "Show Me Around 🎬"

        with patch("src.db.queries.start_onboarding", new_callable=AsyncMock):
            with patch("src.handlers.onboarding.full_tour_timezone", new_callable=AsyncMock) as mock_tz:
                await handle_path_selection(mock_update, mock_context)

                # Verify routed to full tour
                mock_tz.assert_called_once()


@pytest.mark.asyncio
class TestJustChatFlow:
    """Test Just Chat onboarding path"""

    @pytest.mark.asyncio
    async def test_just_chat_immediate_completion(self, mock_update, mock_context, mock_user_id):
        """Test Just Chat path completes immediately"""
        mock_update.message.text = "Just Chat 💬"

        with patch("src.db.queries.start_onboarding", new_callable=AsyncMock):
            with patch("src.handlers.onboarding.just_chat_start", new_callable=AsyncMock) as mock_chat:
                await handle_path_selection(mock_update, mock_context)

                # Verify just chat started
                mock_chat.assert_called_once()
