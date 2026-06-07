"""
Unit tests for VRChat MCP Avatar Manager
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from vrchat_mcp.models import AvatarState
from vrchat_mcp.tools.avatar.tools import AvatarManager


# Module-level fixtures
@pytest.fixture
def mock_osc_manager():
    """Create a mock OSC manager for testing."""
    mock = Mock()
    mock.send_parameter = AsyncMock()
    return mock


@pytest.fixture
def avatar_manager(mock_osc_manager):
    """Create an AvatarManager instance for testing."""
    return AvatarManager(
        osc_manager=mock_osc_manager,
    )


class TestAvatarManager:
    """Test cases for AvatarManager class."""

    @pytest.mark.asyncio
    async def test_load_avatar_success(self, avatar_manager, mock_osc_manager):
        """Test successful avatar loading."""
        result = await avatar_manager.load_avatar("test_avatar_123")

        assert result["status"] == "success"
        assert result["avatar_id"] == "test_avatar_123"
        assert result["message"] == "Avatar 'test_avatar_123' load requested"

        # Verify OSC command was sent
        mock_osc_manager.send_parameter.assert_called_once_with("VRC_Avatar", "test_avatar_123")

        # Verify avatar state was created
        assert "test_avatar_123" in avatar_manager.avatars
        assert avatar_manager.current_avatar_id == "test_avatar_123"

    @pytest.mark.asyncio
    async def test_load_avatar_osc_failure(self, avatar_manager, mock_osc_manager):
        """Test avatar loading when OSC manager fails."""
        mock_osc_manager.send_parameter.side_effect = Exception("OSC connection failed")

        result = await avatar_manager.load_avatar("test_avatar_123")

        assert result["status"] == "error"
        assert result["error"] == "OSC connection failed"
        assert result["avatar_id"] == "test_avatar_123"

    @pytest.mark.asyncio
    async def test_get_avatar_state_existing(self, avatar_manager):
        """Test getting state of existing avatar."""
        # Pre-populate with test data
        avatar_manager.avatars["test_avatar"] = AvatarState(
            avatar_id="test_avatar", parameters={"param1": 0.5, "param2": True}, loaded_at=1234567890.0
        )
        avatar_manager.current_avatar_id = "test_avatar"

        result = await avatar_manager.get_avatar_state("test_avatar")

        assert result["status"] == "success"
        assert result["avatar_id"] == "test_avatar"
        assert result["current"] is True
        assert result["parameters"]["param1"] == 0.5
        assert result["parameter_count"] == 2

    @pytest.mark.asyncio
    async def test_get_avatar_state_not_found(self, avatar_manager):
        """Test getting state of non-existent avatar."""
        result = await avatar_manager.get_avatar_state("nonexistent")

        assert result["status"] == "error"
        assert result["error"] == "Avatar 'nonexistent' not found"

    @pytest.mark.asyncio
    async def test_set_parameter_success(self, avatar_manager, mock_osc_manager):
        """Test successful parameter setting."""
        # Pre-create avatar
        avatar_manager.avatars["test_avatar"] = AvatarState(
            avatar_id="test_avatar", parameters={}, loaded_at=1234567890.0
        )

        result = await avatar_manager.set_parameter("test_avatar", "TestParam", 0.75)

        assert result is True
        mock_osc_manager.send_parameter.assert_called_once_with("TestParam", 0.75, "test_avatar")

        # Verify parameter was stored
        assert avatar_manager.avatars["test_avatar"].parameters["TestParam"] == 0.75

    @pytest.mark.asyncio
    async def test_set_parameter_different_types(self, avatar_manager, mock_osc_manager):
        """Test setting parameters of different types."""
        # Pre-create avatar
        avatar_manager.avatars["test_avatar"] = AvatarState(
            avatar_id="test_avatar", parameters={}, loaded_at=1234567890.0
        )

        # Test float
        result = await avatar_manager.set_parameter("test_avatar", "FloatParam", 0.5)
        assert result is True
        mock_osc_manager.send_parameter.assert_called_with("FloatParam", 0.5, "test_avatar")

        # Test int
        result = await avatar_manager.set_parameter("test_avatar", "IntParam", 42)
        assert result is True
        mock_osc_manager.send_parameter.assert_called_with("IntParam", 42, "test_avatar")

        # Test bool
        result = await avatar_manager.set_parameter("test_avatar", "BoolParam", True)
        assert result is True
        mock_osc_manager.send_parameter.assert_called_with("BoolParam", True, "test_avatar")

        # Test string
        result = await avatar_manager.set_parameter("test_avatar", "StringParam", "test_value")
        assert result is True
        mock_osc_manager.send_parameter.assert_called_with("StringParam", "test_value", "test_avatar")

    @pytest.mark.asyncio
    async def test_set_parameter_invalid_type(self, avatar_manager, mock_osc_manager):
        """Test setting parameter with invalid type."""
        avatar_manager.avatars["test_avatar"] = AvatarState(
            avatar_id="test_avatar", parameters={}, loaded_at=1234567890.0
        )

        # Configure mock to raise ValueError for invalid type
        mock_osc_manager.send_parameter.side_effect = ValueError("Unsupported parameter type: dict")

        # This should fail since dict is not a supported OSC type
        result = await avatar_manager.set_parameter("test_avatar", "InvalidParam", {"key": "value"})

        assert result is False
        mock_osc_manager.send_parameter.assert_called_once_with("InvalidParam", {"key": "value"}, "test_avatar")

    @pytest.mark.asyncio
    async def test_get_parameter_existing(self, avatar_manager):
        """Test getting existing parameter."""
        avatar_manager.avatars["test_avatar"] = AvatarState(
            avatar_id="test_avatar", parameters={"TestParam": 0.75}, loaded_at=1234567890.0
        )

        result = await avatar_manager.get_parameter("test_avatar", "TestParam")

        assert result == 0.75

    @pytest.mark.asyncio
    async def test_get_parameter_not_found(self, avatar_manager):
        """Test getting non-existent parameter."""
        avatar_manager.avatars["test_avatar"] = AvatarState(
            avatar_id="test_avatar", parameters={}, loaded_at=1234567890.0
        )

        result = await avatar_manager.get_parameter("test_avatar", "NonExistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_parameter_with_default(self, avatar_manager):
        """Test getting parameter with default value."""
        avatar_manager.avatars["test_avatar"] = AvatarState(
            avatar_id="test_avatar", parameters={}, loaded_at=1234567890.0
        )

        result = await avatar_manager.get_parameter("test_avatar", "NonExistent", default=42)

        assert result == 42

    @pytest.mark.asyncio
    async def test_list_avatars(self, avatar_manager):
        """Test listing all tracked avatars."""
        avatar_manager.avatars = {
            "avatar1": AvatarState(avatar_id="avatar1", parameters={}, loaded_at=1.0),
            "avatar2": AvatarState(avatar_id="avatar2", parameters={}, loaded_at=2.0),
            "avatar3": AvatarState(avatar_id="avatar3", parameters={}, loaded_at=3.0),
        }

        result = avatar_manager.list_avatars()

        assert len(result) == 3
        assert "avatar1" in result
        assert "avatar2" in result
        assert "avatar3" in result

    def test_get_current_avatar(self, avatar_manager):
        """Test getting current avatar ID."""
        avatar_manager.current_avatar_id = "current_avatar"

        result = avatar_manager.get_current_avatar()

        assert result == "current_avatar"

    def test_get_current_avatar_none(self, avatar_manager):
        """Test getting current avatar when none is set."""
        avatar_manager.current_avatar_id = None

        result = avatar_manager.get_current_avatar()

        assert result is None

    @pytest.mark.asyncio
    async def test_cleanup(self, avatar_manager):
        """Test cleanup functionality."""
        # Add some mock interpolation tasks
        mock_task = AsyncMock()
        avatar_manager._interpolation_tasks = {"task1": mock_task}

        await avatar_manager.cleanup()

        # Verify task was cancelled
        mock_task.cancel.assert_called_once()

        # Verify tasks dict is empty
        assert len(avatar_manager._interpolation_tasks) == 0


# Module-level fixtures for interpolation tests
@pytest.fixture
def mock_interpolation():
    """Create a mock interpolation system."""
    mock = Mock()
    mock.ease_linear = Mock(return_value=0.5)
    return mock


@pytest.fixture
def avatar_manager_with_interp(mock_osc_manager, mock_interpolation):
    """Create an AvatarManager with interpolation enabled."""
    return AvatarManager(osc_manager=mock_osc_manager, interpolation_system=mock_interpolation)


class TestAvatarManagerInterpolation:
    """Test cases for AvatarManager interpolation functionality."""

    @pytest.mark.asyncio
    async def test_set_parameter_with_interpolation(
        self, avatar_manager_with_interp, mock_osc_manager, mock_interpolation
    ):
        """Test parameter setting with interpolation enabled."""
        # Pre-create avatar with initial value
        avatar_manager_with_interp.avatars["test_avatar"] = AvatarState(
            avatar_id="test_avatar", parameters={"TestParam": 0.0}, loaded_at=1234567890.0
        )

        # Mock asyncio.sleep to avoid waiting
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.time.return_value = 0.0

                # Start interpolation (this will be cancelled immediately for testing)
                result = await avatar_manager_with_interp.set_parameter(
                    "test_avatar", "TestParam", 1.0, interpolate=True, duration=1.0, easing="linear"
                )

                assert result is True

                # Verify interpolation task was created
                assert len(avatar_manager_with_interp._interpolation_tasks) > 0

                # Cancel the task to clean up
                for task in avatar_manager_with_interp._interpolation_tasks.values():
                    task.cancel()

    @pytest.mark.asyncio
    async def test_interpolation_without_system(self, avatar_manager, mock_osc_manager):
        """Test that interpolation falls back to direct setting when no interpolation system."""
        avatar_manager.avatars["test_avatar"] = AvatarState(
            avatar_id="test_avatar", parameters={}, loaded_at=1234567890.0
        )

        result = await avatar_manager.set_parameter("test_avatar", "TestParam", 1.0, interpolate=True, duration=1.0)

        # Should still work but without interpolation
        assert result is True
        mock_osc_manager.send_parameter.assert_called_once_with("TestParam", 1.0, "test_avatar")
