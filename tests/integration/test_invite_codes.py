"""Integration tests for invite code generation"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.agent import generate_invite_code, AgentDeps
from src.memory.file_manager import MemoryFileManager


@pytest.fixture
def admin_deps():
    """Create AgentDeps for admin user"""
    memory_manager = Mock(spec=MemoryFileManager)
    return AgentDeps(
        telegram_id="7376426503",  # Admin user
        memory_manager=memory_manager,
        user_memory={},
        reminder_manager=None,
        bot_application=None,
    )


@pytest.fixture
def non_admin_deps():
    """Create AgentDeps for non-admin user"""
    memory_manager = Mock(spec=MemoryFileManager)
    return AgentDeps(
        telegram_id="12345",  # Non-admin user
        memory_manager=memory_manager,
        user_memory={},
        reminder_manager=None,
        bot_application=None,
    )


class TestInviteCodeGeneration:
    """Test suite for invite code generation"""

    @pytest.mark.asyncio
    async def test_generate_invite_code_as_admin(self, admin_deps):
        """Test that admin can generate invite codes"""
        ctx = Mock()
        ctx.deps = admin_deps

        with patch('src.agent.create_invite_code', new_callable=AsyncMock) as mock_create:
            result = await generate_invite_code(ctx, count=1, tier='free', trial_days=7, max_uses=1)

            assert result.success is True
            assert result.code is not None
            assert "✅" in result.message
            assert "Invite Code Generated" in result.message
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_invite_code_as_non_admin(self, non_admin_deps):
        """Test that non-admin cannot generate invite codes"""
        ctx = Mock()
        ctx.deps = non_admin_deps

        result = await generate_invite_code(ctx, count=1, tier='free', trial_days=7, max_uses=1)

        assert result.success is False
        assert "Only the admin" in result.message
        assert result.code is None

    @pytest.mark.asyncio
    async def test_generate_multiple_invite_codes(self, admin_deps):
        """Test generating multiple invite codes"""
        ctx = Mock()
        ctx.deps = admin_deps

        with patch('src.agent.create_invite_code', new_callable=AsyncMock) as mock_create:
            result = await generate_invite_code(ctx, count=3, tier='free', trial_days=7, max_uses=1)

            assert result.success is True
            assert result.code is None  # Multiple codes, so no single code returned
            assert "3 Invite Codes Generated" in result.message
            assert mock_create.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_invite_code_with_collision_retry(self, admin_deps):
        """Test that collision handling works with retry logic"""
        ctx = Mock()
        ctx.deps = admin_deps

        # Mock create_invite_code to fail once with unique constraint error, then succeed
        call_count = 0

        async def mock_create_with_collision(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: simulate unique constraint violation
                raise Exception("duplicate key value violates unique constraint")
            # Second call: succeed
            return "mock_id"

        with patch('src.agent.create_invite_code', side_effect=mock_create_with_collision):
            # Mock random.choices to return same code first time
            with patch('random.choices', side_effect=[
                ['apple', 'beach', 'cloud'],  # First attempt (will collide)
                ['tiger', 'moon', 'river'],   # Second attempt (will succeed)
            ]):
                result = await generate_invite_code(ctx, count=1, tier='free', trial_days=7, max_uses=1)

                assert result.success is True
                assert result.code == 'tiger-moon-river'  # Should use second generated code
                assert call_count == 2  # Should have retried once

    @pytest.mark.asyncio
    async def test_generate_invite_code_max_retries_exceeded(self, admin_deps):
        """Test that max retries limit is enforced"""
        ctx = Mock()
        ctx.deps = admin_deps

        # Mock create_invite_code to always fail with unique constraint error
        async def mock_create_always_collide(*args, **kwargs):
            raise Exception("duplicate key value violates unique constraint")

        with patch('src.agent.create_invite_code', side_effect=mock_create_always_collide):
            result = await generate_invite_code(ctx, count=1, tier='free', trial_days=7, max_uses=1)

            # Should fail after max retries
            assert result.success is False
            assert "Failed to generate codes" in result.message

    @pytest.mark.asyncio
    async def test_generate_invite_code_validation_count(self, admin_deps):
        """Test input validation for count parameter"""
        ctx = Mock()
        ctx.deps = admin_deps

        # Test count < 1
        result = await generate_invite_code(ctx, count=0, tier='free', trial_days=7, max_uses=1)
        assert result.success is False
        assert "Count must be between 1 and 100" in result.message

        # Test count > 100
        result = await generate_invite_code(ctx, count=101, tier='free', trial_days=7, max_uses=1)
        assert result.success is False
        assert "Count must be between 1 and 100" in result.message

    @pytest.mark.asyncio
    async def test_generate_invite_code_validation_tier(self, admin_deps):
        """Test input validation for tier parameter"""
        ctx = Mock()
        ctx.deps = admin_deps

        result = await generate_invite_code(ctx, count=1, tier='invalid', trial_days=7, max_uses=1)
        assert result.success is False
        assert "Tier must be" in result.message

    @pytest.mark.asyncio
    async def test_generate_invite_code_validation_trial_days(self, admin_deps):
        """Test input validation for trial_days parameter"""
        ctx = Mock()
        ctx.deps = admin_deps

        result = await generate_invite_code(ctx, count=1, tier='free', trial_days=-1, max_uses=1)
        assert result.success is False
        assert "Trial days must be 0 or positive" in result.message

    @pytest.mark.asyncio
    async def test_generate_invite_code_different_tiers(self, admin_deps):
        """Test generating codes with different tiers"""
        ctx = Mock()
        ctx.deps = admin_deps

        tiers = ['free', 'basic', 'premium']

        for tier in tiers:
            with patch('src.agent.create_invite_code', new_callable=AsyncMock) as mock_create:
                result = await generate_invite_code(ctx, count=1, tier=tier, trial_days=7, max_uses=1)

                assert result.success is True
                assert tier.title() in result.message

    @pytest.mark.asyncio
    async def test_admin_check_with_integer_telegram_id(self):
        """Test that admin check works with integer telegram_id"""
        # This tests the type normalization fix
        memory_manager = Mock(spec=MemoryFileManager)
        deps_with_int_id = AgentDeps(
            telegram_id=7376426503,  # Integer instead of string
            memory_manager=memory_manager,
            user_memory={},
            reminder_manager=None,
            bot_application=None,
        )

        ctx = Mock()
        ctx.deps = deps_with_int_id

        with patch('src.agent.create_invite_code', new_callable=AsyncMock) as mock_create:
            result = await generate_invite_code(ctx, count=1, tier='free', trial_days=7, max_uses=1)

            # Should succeed because is_admin now normalizes to string
            assert result.success is True
            assert result.code is not None
