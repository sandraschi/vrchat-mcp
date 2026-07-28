"""
Unit tests for VRChat API and 2026 Portmanteau tools.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vrchat_mcp.server import manage_economy, manage_input, manage_world


@pytest.mark.asyncio
async def test_manage_input_chatbox():
    # Mock OSCManager and app state
    with patch("vrchat_mcp.server.osc_manager") as mock_osc:
        mock_osc.send_message = AsyncMock()

        result = await manage_input(operation="chatbox", value="Test Message", immediate=True)

        assert result["success"] is True
        assert mock_osc.send_message.called
        # Check if correct address was used
        args, _ = mock_osc.send_message.call_args
        msg = args[0]
        assert msg.address == "/chatbox/input"
        assert msg.args == ["Test Message", True]


@pytest.mark.asyncio
async def test_manage_input_jump():
    with patch("vrchat_mcp.server.osc_manager") as mock_osc:
        mock_osc.send_message = AsyncMock()

        result = await manage_input(operation="jump")

        assert result["success"] is True
        # Jump sends two messages (Press and Release)
        assert mock_osc.send_message.call_count == 2


@pytest.mark.asyncio
async def test_manage_world_unauthorized():
    # If API not initialized, should raise RuntimeError in result
    with patch("vrchat_mcp.server.vrchat_api", None):
        result = await manage_world(operation="get_info", world_id="wrld_123")
        assert "error" in result
        assert "REST API Client not initialized" in result["error"]


@pytest.mark.asyncio
async def test_manage_world_info():
    mock_api = MagicMock()
    mock_api.get_world_info = AsyncMock(return_value={"id": "wrld_123", "name": "Trial World"})

    with patch("vrchat_mcp.server.vrchat_api", mock_api):
        result = await manage_world(operation="get_info", world_id="wrld_123")
        assert result["data"]["name"] == "Trial World"
        mock_api.get_world_info.assert_called_once_with("wrld_123")


@pytest.mark.asyncio
async def test_manage_economy_balance():
    mock_api = MagicMock()
    mock_api.get_economy_info = AsyncMock(return_value={"credits": 5000})

    with patch("vrchat_mcp.server.vrchat_api", mock_api):
        result = await manage_economy(operation="balance")
        assert result["data"]["credits"] == 5000
