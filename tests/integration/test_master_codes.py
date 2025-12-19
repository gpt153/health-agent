"""Integration tests for master code functionality"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.agent import generate_invite_code, AgentDeps
from src.db.queries import validate_invite_code, deactivate_invite_code
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


class TestMasterCodes:
    """Test suite for master code feature"""

    @pytest.mark.asyncio
    async def test_generate_master_code_as_admin(self, admin_deps):
        """Test that admin can generate master codes"""
        ctx = Mock()
        ctx.deps = admin_deps

        with patch('src.agent.create_invite_code', new_callable=AsyncMock) as mock_create:
            result = await generate_invite_code(
                ctx,
                count=1,
                tier='premium',
                trial_days=0,
                is_master_code=True,
                description="Family & Friends Code"
            )

            assert result.success is True
            assert result.code is not None
            assert "Master Code Created" in result.message
            assert "Unlimited Uses" in result.message
            assert "Family & Friends Code" in result.message

            # Verify create_invite_code was called with correct params
            call_args = mock_create.call_args
            assert call_args.kwargs['is_master_code'] is True
            assert call_args.kwargs['description'] == "Family & Friends Code"
            assert call_args.kwargs['max_uses'] is None  # Unlimited

    @pytest.mark.asyncio
    async def test_generate_master_code_as_non_admin(self, non_admin_deps):
        """Test that non-admin cannot generate master codes"""
        ctx = Mock()
        ctx.deps = non_admin_deps

        result = await generate_invite_code(
            ctx,
            count=1,
            tier='premium',
            is_master_code=True
        )

        assert result.success is False
        assert "Only the admin" in result.message

    @pytest.mark.asyncio
    async def test_master_code_forces_unlimited_uses(self, admin_deps):
        """Test that is_master_code=True overrides max_uses parameter"""
        ctx = Mock()
        ctx.deps = admin_deps

        with patch('src.agent.create_invite_code', new_callable=AsyncMock) as mock_create:
            # Try to create master code with max_uses=5 (should be ignored)
            result = await generate_invite_code(
                ctx,
                count=1,
                tier='premium',
                max_uses=5,  # This should be overridden to None
                is_master_code=True
            )

            # Verify max_uses was forced to None (unlimited)
            call_args = mock_create.call_args
            assert call_args.kwargs['max_uses'] is None

    @pytest.mark.asyncio
    async def test_master_code_default_description(self, admin_deps):
        """Test that master codes get default description if not provided"""
        ctx = Mock()
        ctx.deps = admin_deps

        with patch('src.agent.create_invite_code', new_callable=AsyncMock) as mock_create:
            result = await generate_invite_code(
                ctx,
                count=1,
                tier='premium',
                is_master_code=True
                # No description provided
            )

            # Should have auto-generated description
            call_args = mock_create.call_args
            assert call_args.kwargs['description'] == "Master Code (Premium tier)"

    @pytest.mark.asyncio
    async def test_validate_master_code_unlimited_uses(self):
        """Test that master codes can be validated even with high use count"""
        from datetime import datetime

        # Mock database result for master code with 100 uses
        master_code_data = (
            'code-id-123',  # id
            'family-premium-access',  # code
            None,  # max_uses (unlimited)
            100,  # uses_count (already used 100 times)
            'premium',  # tier
            0,  # trial_days
            None,  # expires_at
            True,  # active
            True,  # is_master_code
            'VIP Friends and Family'  # description
        )

        with patch('src.db.queries.db.connection') as mock_conn:
            mock_cursor = AsyncMock()
            mock_cursor.fetchone.return_value = master_code_data
            mock_conn.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value = mock_cursor

            result = await validate_invite_code('family-premium-access')

            assert result is not None
            assert result['is_master_code'] is True
            assert result['code'] == 'family-premium-access'
            assert result['tier'] == 'premium'

    @pytest.mark.asyncio
    async def test_validate_regular_code_exhausted(self):
        """Test that regular codes fail validation when exhausted"""
        from datetime import datetime

        # Mock database result for exhausted regular code
        regular_code_data = (
            'code-id-456',  # id
            'regular-code-123',  # code
            1,  # max_uses
            1,  # uses_count (exhausted)
            'free',  # tier
            7,  # trial_days
            None,  # expires_at
            True,  # active
            False,  # is_master_code
            None  # description
        )

        with patch('src.db.queries.db.connection') as mock_conn:
            mock_cursor = AsyncMock()
            mock_cursor.fetchone.return_value = regular_code_data
            mock_conn.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value = mock_cursor

            result = await validate_invite_code('regular-code-123')

            # Regular code should fail validation (exhausted)
            assert result is None

    @pytest.mark.asyncio
    async def test_deactivate_master_code(self):
        """Test deactivating a master code"""
        # Mock database result
        mock_result = ('code-id-789', True)  # (id, is_master_code)

        with patch('src.db.queries.db.connection') as mock_conn:
            mock_cursor = AsyncMock()
            mock_cursor.fetchone.return_value = mock_result
            mock_conn.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_conn.return_value.__aenter__.return_value.commit = AsyncMock()

            result = await deactivate_invite_code('family-premium-access')

            assert result is True

    @pytest.mark.asyncio
    async def test_deactivate_nonexistent_code(self):
        """Test deactivating a code that doesn't exist"""
        with patch('src.db.queries.db.connection') as mock_conn:
            mock_cursor = AsyncMock()
            mock_cursor.fetchone.return_value = None
            mock_conn.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_conn.return_value.__aenter__.return_value.commit = AsyncMock()

            result = await deactivate_invite_code('nonexistent-code')

            assert result is False

    @pytest.mark.asyncio
    async def test_master_code_response_format(self, admin_deps):
        """Test that master code generation returns correct message format"""
        ctx = Mock()
        ctx.deps = admin_deps

        with patch('src.agent.create_invite_code', new_callable=AsyncMock):
            with patch('random.choices', return_value=['tiger', 'coral', 'moon']):
                result = await generate_invite_code(
                    ctx,
                    count=1,
                    tier='premium',
                    trial_days=0,
                    is_master_code=True,
                    description="VIP Code"
                )

                assert result.success is True
                assert result.code == 'tiger-coral-moon'
                assert "Master Code Created" in result.message
                assert "VIP Code" in result.message
                assert "Unlimited Uses" in result.message
                assert "Expires: Never" in result.message
                assert "⚠️" in result.message  # Warning about sharing

    @pytest.mark.asyncio
    async def test_regular_code_vs_master_code_generation(self, admin_deps):
        """Test that regular and master codes are generated differently"""
        ctx = Mock()
        ctx.deps = admin_deps

        with patch('src.agent.create_invite_code', new_callable=AsyncMock) as mock_create:
            # Generate regular code
            await generate_invite_code(ctx, count=1, tier='free', max_uses=1, is_master_code=False)

            regular_call = mock_create.call_args
            assert regular_call.kwargs['is_master_code'] is False
            assert regular_call.kwargs['max_uses'] == 1

            # Generate master code
            await generate_invite_code(ctx, count=1, tier='premium', is_master_code=True)

            master_call = mock_create.call_args
            assert master_call.kwargs['is_master_code'] is True
            assert master_call.kwargs['max_uses'] is None  # Unlimited
