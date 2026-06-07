"""Tests for the plugin decorators in vrchat_mcp.plugins."""

import inspect
from typing import Any

import pytest

from vrchat_mcp.plugins import Plugin, event_listener, tool


# Test plugin class that uses the decorators
class TestPlugin(Plugin):
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
        """Handle test events.

        Args:
            event_data: The event data
        """
        self.last_event = event_data


# Tests
def test_tool_decorator():
    """Test that the @tool decorator correctly sets up tool metadata."""
    plugin = TestPlugin()

    # Check that the method is marked as a tool
    assert hasattr(plugin.test_tool, "_is_tool")
    assert plugin.test_tool._is_tool is True

    # Check that the tool metadata is set up correctly
    assert hasattr(plugin.test_tool, "_tool_metadata")
    metadata = plugin.test_tool._tool_metadata

    assert metadata["name"] == "test_tool"
    assert metadata["category"] == "Testing"
    assert "A test tool for unit tests" in metadata["description"]
    assert metadata["requires_auth"] is True
    assert metadata["rate_limit"] == {"calls": 10, "interval": 60}

    # Check parameter metadata
    assert "param1" in metadata["args"]
    assert metadata["args"]["param1"]["type"] == "string"
    assert "First parameter" in metadata["args"]["param1"]["description"]
    assert metadata["args"]["param1"]["required"] is True

    assert "param2" in metadata["args"]
    assert metadata["args"]["param2"]["type"] == "integer"
    assert metadata["args"]["param2"]["default"] == 42
    assert metadata["args"]["param2"]["required"] is False

    # Check return type metadata
    assert metadata["returns"]["type"] == "object"
    assert "Result of the operation" in metadata["returns"]["description"]
    assert "success" in metadata["returns"]["schema"]

    # Check that the docstring is preserved
    assert "Test tool with documentation" in metadata["docstring"]
    assert "This is a more detailed description" in metadata["docstring"]
    assert "param1" in metadata["docstring"]
    assert "param2" in metadata["docstring"]


def test_tool_invocation():
    """Test that the tool can be called normally."""
    plugin = TestPlugin()
    result = plugin.test_tool("test_value", 123)
    assert result["success"] is True
    assert "test_value" in result["message"]
    assert "123" in result["message"]

    # Test with default parameter
    result = plugin.test_tool("another_test")
    assert "another_test" in result["message"]
    assert "42" in result["message"]  # Default value for param2


@pytest.mark.asyncio
async def test_event_listener():
    """Test that the @event_listener decorator works correctly."""
    plugin = TestPlugin()

    # Check that the method is marked as an event listener
    assert hasattr(plugin.on_test_event, "_event_listeners")
    assert isinstance(plugin.on_test_event._event_listeners, list)
    assert len(plugin.on_test_event._event_listeners) == 1

    # Check that the event listener is registered for the correct event type
    event_info = plugin.on_test_event._event_listeners[0]
    assert isinstance(event_info, dict)
    assert event_info["event_type"] == "test_event"
    assert event_info["method_name"] == "on_test_event"

    # Test that the event handler can be called
    test_data = {"test": "data"}
    await plugin.on_test_event(test_data)
    assert hasattr(plugin, "last_event")
    assert plugin.last_event == test_data


def test_tool_signature_preservation():
    """Test that the function signature is preserved by the @tool decorator."""
    plugin = TestPlugin()

    # Get the signature of the decorated method
    sig = inspect.signature(plugin.test_tool)
    params = list(sig.parameters.values())

    # Check that the signature includes 'self' and the parameters
    assert len(params) == 3  # self, param1, param2
    assert params[0].name == "self"
    assert params[1].name == "param1"
    assert params[2].name == "param2"
    assert params[2].default == 42  # Default value is preserved

    # Check return type annotation
    assert sig.return_annotation == dict[str, Any]


def test_event_listener_validation():
    """Test that the @event_listener decorator validates the method signature."""
    with pytest.raises(TypeError):
        # Non-async function should raise TypeError
        @event_listener("invalid_event")
        def invalid_listener(self):
            pass

    # This should work fine
    @event_listener("valid_event")
    async def valid_listener(self, event_data):
        pass
