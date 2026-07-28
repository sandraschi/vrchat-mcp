"""Tests for the plugin decorators in vrchat_mcp.plugins."""

import inspect
from typing import Any

import pytest

from vrchat_mcp.plugins import Plugin, event_listener, tool


class SamplePlugin(Plugin):
    """Test plugin for testing decorators."""

    @property
    def name(self) -> str:
        return "test_plugin"

    @tool(
        name="test_tool",
        category="Testing",
        description="A test tool for unit tests",
        args={
            "param1": {"type": "string", "description": "First parameter", "required": True},
            "param2": {
                "type": "integer",
                "description": "Second parameter with default",
                "default": 42,
                "required": False,
            },
        },
        returns={
            "type": "object",
            "description": "Result of the operation",
            "schema": {"success": {"type": "boolean"}, "message": {"type": "string"}},
        },
        requires_auth=True,
        rate_limit={"calls": 10, "interval": 60},
    )
    def test_tool(self, param1: str, param2: int = 42) -> dict[str, Any]:
        """Test tool with documentation.

        This is a more detailed description of the test tool.

        Args:
            param1: The first parameter
            param2: The second parameter with default

        Returns:
            A dictionary with the operation result
        """
        return {"success": True, "message": f"Processed {param1} and {param2}"}

    @event_listener("test_event")
    async def on_test_event(self, event_data: dict[str, Any]) -> None:
        """Handle test events."""
        self.last_event = event_data

    async def on_load(self, mcp: Any) -> None:
        pass

    async def on_unload(self) -> None:
        pass


def test_tool_decorator():
    plugin = SamplePlugin()
    assert hasattr(plugin.test_tool, "_is_tool")
    assert plugin.test_tool._is_tool is True
    metadata = plugin.test_tool._tool_metadata
    assert metadata["name"] == "test_tool"
    assert "Result of the operation" in metadata["returns"]["description"]


def test_tool_invocation():
    plugin = SamplePlugin()
    result = plugin.test_tool("test_value", 123)
    assert result["success"] is True


@pytest.mark.asyncio
async def test_event_listener():
    plugin = SamplePlugin()
    assert plugin.on_test_event._event_listeners[0]["event_type"] == "test_event"
    await plugin.on_test_event({"test": "data"})
    assert plugin.last_event == {"test": "data"}


def test_tool_signature_preservation():
    plugin = SamplePlugin()
    sig = inspect.signature(plugin.test_tool)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert params[0].name == "param1"
    assert params[1].name == "param2"
    assert params[1].default == 42
