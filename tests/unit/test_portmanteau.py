"""
Unit tests for VRChat MCP Portmanteau tools.
"""

from unittest.mock import patch

import pytest

from vrchat_mcp.server import manage_avatar, manage_osc, manage_system


@pytest.mark.asyncio
async def test_manage_avatar_load(mock_avatar_manager):
    """Test manage_avatar load operation."""
    with patch("vrchat_mcp.server.avatar_manager", mock_avatar_manager):
        result = await manage_avatar(operation="load", avatar_id="test_avatar")

        assert result["operation"] == "load"
        assert result["data"]["status"] == "success"
        mock_avatar_manager.load_avatar.assert_called_once_with("test_avatar")


@pytest.mark.asyncio
async def test_manage_avatar_set_param(mock_avatar_manager):
    """Test manage_avatar set_param operation."""
    with patch("vrchat_mcp.server.avatar_manager", mock_avatar_manager):
        result = await manage_avatar(operation="set_param", avatar_id="test_avatar", parameter="Mute", value=True)

        assert result["operation"] == "set_param"
        assert result["success"] is True
        mock_avatar_manager.set_parameter.assert_called_once_with("test_avatar", "Mute", True, False, 0.5, "linear")


@pytest.mark.asyncio
async def test_manage_osc_stats(mock_osc_manager):
    """Test manage_osc stats operation."""
    with patch("vrchat_mcp.server.osc_inspector", mock_osc_manager):
        result = await manage_osc(operation="stats")

        assert result["operation"] == "stats"
        assert result["data"]["messages_sent"] == 42
        mock_osc_manager.get_statistics.assert_called_once()


@pytest.mark.asyncio
async def test_manage_system_status():
    """Test manage_system status operation."""
    # We don't need to patch anything for a basic status report unless it calls managers
    result = await manage_system(operation="status")

    assert result["operation"] == "status"
    assert result["data"]["status"] == "running"
    assert "version" in result["data"]


@pytest.mark.asyncio
async def test_manage_system_metrics():
    """Test manage_system metrics operation."""
    result = await manage_system(operation="metrics")

    assert result["operation"] == "metrics"
    assert "uptime_seconds" in result["data"]
    assert "total_requests" in result["data"]


@pytest.mark.asyncio
async def test_invalid_operation():
    """Test handling of invalid operations."""
    result = await manage_avatar(operation="invalid_op")
    assert "error" in result
    assert "Unknown operation" in result["error"]
