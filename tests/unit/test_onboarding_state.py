"""Unit tests for onboarding state management"""
import pytest
from src.models.onboarding import OnboardingState, ONBOARDING_PATHS, TRACKABLE_FEATURES


class TestOnboardingModels:
    """Tests for onboarding Pydantic models"""

    def test_onboarding_state_creation(self):
        """Test creating an onboarding state"""
        state = OnboardingState(
            user_id="test_123",
            onboarding_path="quick",
            current_step="timezone_setup"
        )

        assert state.user_id == "test_123"
        assert state.onboarding_path == "quick"
        assert state.current_step == "timezone_setup"
        assert state.is_active is False  # started_at not set
        assert state.is_complete is False

    def test_onboarding_paths_config(self):
        """Test that all onboarding paths are configured"""
        assert "quick" in ONBOARDING_PATHS
        assert "full" in ONBOARDING_PATHS
        assert "chat" in ONBOARDING_PATHS

        quick_path = ONBOARDING_PATHS["quick"]
        assert quick_path.name == "quick"
        assert len(quick_path.steps) > 0
        assert "path_selection" in quick_path.steps
        assert "completed" in quick_path.steps

    def test_trackable_features_defined(self):
        """Test that trackable features are defined"""
        assert len(TRACKABLE_FEATURES) > 0
        assert "food_tracking" in TRACKABLE_FEATURES
        assert "voice_notes" in TRACKABLE_FEATURES
        assert "reminders" in TRACKABLE_FEATURES


@pytest.mark.asyncio
class TestOnboardingQueries:
    """Tests for onboarding database queries"""

    @pytest.fixture
    async def test_user_id(self):
        """Standard test user ID"""
        return "test_onboarding_user_456"

    @pytest.mark.asyncio
    async def test_get_nonexistent_onboarding_state(self, test_user_id):
        """Test getting state for user without onboarding"""
        from src.db.queries import get_onboarding_state

        state = await get_onboarding_state(test_user_id)
        assert state is None

    @pytest.mark.asyncio
    async def test_start_onboarding(self, test_user_id):
        """Test starting onboarding for a user"""
        from src.db.queries import start_onboarding, get_onboarding_state

        await start_onboarding(test_user_id, "quick")

        state = await get_onboarding_state(test_user_id)
        assert state is not None
        assert state["onboarding_path"] == "quick"
        assert state["current_step"] == "path_selection"
        assert state["started_at"] is not None

    @pytest.mark.asyncio
    async def test_update_onboarding_step(self, test_user_id):
        """Test updating onboarding step"""
        from src.db.queries import start_onboarding, update_onboarding_step, get_onboarding_state

        await start_onboarding(test_user_id, "quick")
        await update_onboarding_step(
            test_user_id,
            "timezone_setup",
            step_data={"timezone": "America/New_York"},
            mark_complete="path_selection"
        )

        state = await get_onboarding_state(test_user_id)
        assert state["current_step"] == "timezone_setup"
        assert "path_selection" in state["completed_steps"]
        assert state["step_data"]["timezone"] == "America/New_York"

    @pytest.mark.asyncio
    async def test_complete_onboarding(self, test_user_id):
        """Test marking onboarding as complete"""
        from src.db.queries import start_onboarding, complete_onboarding, get_onboarding_state

        await start_onboarding(test_user_id, "quick")
        await complete_onboarding(test_user_id)

        state = await get_onboarding_state(test_user_id)
        assert state["current_step"] == "completed"
        assert state["completed_at"] is not None
