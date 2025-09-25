"""Tests for the example plugin."""

import pytest
from typing import Any, Dict

# Test the example plugin
class TestExamplePlugin:
    """Test the example plugin functionality."""
    
    def test_greet_tool(self, example_plugin):
        """Test the greet tool with different inputs."""
        # Test with just the name
        result = example_plugin.greet("Alice")
        assert result == "Hello, Alice."
        
        # Test with name and custom greeting
        result = example_plugin.greet("Bob", "Hi")
        assert result == "Hi, Bob."
        
        # Test with excited=True
        result = example_plugin.greet("Charlie", excited=True)
        assert result == "Hello, Charlie!"
        
        # Test with all parameters
        result = example_plugin.greet("Diana", "Hey", True)
        assert result == "Hey, Diana!"
    
    def test_calculate_stats_tool(self, example_plugin):
        """Test the calculate_stats tool with various inputs."""
        # Test with simple list
        numbers = [1, 2, 3, 4, 5]
        expected = {
            "count": 5,
            "sum": 15,
            "average": 3.0,
            "min": 1,
            "max": 5
        }
        result = example_plugin.calculate_stats(numbers)
        assert result == expected
        
        # Test with empty list (should raise ValueError)
        with pytest.raises(ValueError, match="Cannot calculate statistics for an empty list"):
            example_plugin.calculate_stats([])
    
    @pytest.mark.asyncio
    async def test_event_listeners(self, example_plugin):
        """Test that event listeners are properly registered and called."""
        # Check that event listeners are registered
        assert hasattr(example_plugin.on_player_joined, "_event_listeners")
        assert hasattr(example_plugin.on_player_left, "_event_listeners")
        
        # Test player_joined event
        join_event = {"player_name": "TestUser", "player_id": "12345"}
        await example_plugin.on_player_joined(join_event)
        
        # Test player_left event
        leave_event = {"player_name": "TestUser", "player_id": "12345"}
        await example_plugin.on_player_left(leave_event)
    
    def test_plugin_metadata(self, example_plugin):
        """Test that the plugin has the correct metadata."""
        assert example_plugin.name == "example_plugin"
        assert example_plugin.version == "1.0.0"
        assert "example" in example_plugin.description.lower()
    
    def test_tool_metadata(self, example_plugin):
        """Test that tool metadata is correctly set up."""
        # Check greet tool metadata
        assert hasattr(example_plugin.greet, "_tool_metadata")
        greet_meta = example_plugin.greet._tool_metadata
        assert greet_meta["name"] == "greet"
        assert greet_meta["category"] == "Examples"
        assert "greeting message" in greet_meta["description"].lower()
        assert greet_meta["requires_auth"] is False
        assert greet_meta["rate_limit"] == {"calls": 60, "interval": 60}
        
        # Check args in metadata
        assert "name" in greet_meta["args"]
        assert greet_meta["args"]["name"]["type"] == "string"
        assert "name to include" in greet_meta["args"]["name"]["description"].lower()
        assert greet_meta["args"]["name"]["required"] is True
        
        assert "greeting" in greet_meta["args"]
        assert greet_meta["args"]["greeting"]["type"] == "string"
        assert greet_meta["args"]["greeting"]["default"] == "Hello"
        assert greet_meta["args"]["greeting"]["required"] is False
        
        assert "excited" in greet_meta["args"]
        assert greet_meta["args"]["excited"]["type"] == "boolean"
        assert greet_meta["args"]["excited"]["default"] is False
        
        # Check returns in metadata
        assert greet_meta["returns"]["type"] == "string"
        assert "greeting message" in greet_meta["returns"]["description"].lower()
        
        # Check calculate_stats tool metadata
        assert hasattr(example_plugin.calculate_stats, "_tool_metadata")
        stats_meta = example_plugin.calculate_stats._tool_metadata
        assert stats_meta["name"] == "calculate_stats"
        assert stats_meta["requires_auth"] is True
        
        # Check args in calculate_stats metadata
        assert "numbers" in stats_meta["args"]
        assert stats_meta["args"]["numbers"]["type"] == "array"
        assert stats_meta["args"]["numbers"]["items"]["type"] == "number"
        
        # Check returns in calculate_stats metadata
        assert stats_meta["returns"]["type"] == "object"
        assert "statistics" in stats_meta["returns"]["description"].lower()
        assert "count" in stats_meta["returns"]["schema"]
        assert "sum" in stats_meta["returns"]["schema"]
        assert "average" in stats_meta["returns"]["schema"]
        assert "min" in stats_meta["returns"]["schema"]
        assert "max" in stats_meta["returns"]["schema"]
    
    def test_plugin_lifecycle(self, example_plugin, mock_mcp_server):
        """Test the plugin lifecycle methods."""
        # Test on_load
        assert not hasattr(example_plugin, "_mcp")
        example_plugin.on_load(mock_mcp_server)
        assert hasattr(example_plugin, "_mcp")
        
        # Test that tools are registered with the MCP server
        assert "greet" in mock_mcp_server.tools
        assert "calculate_stats" in mock_mcp_server.tools
        
        # Test on_unload
        example_plugin.on_unload()
        # Add assertions for any cleanup that should happen on unload
    
    def test_plugin_docstrings(self, example_plugin):
        """Test that all tools and methods have proper docstrings."""
        # Check class docstring
        assert "example plugin" in example_plugin.__class__.__doc__.lower()
        
        # Check method docstrings
        methods = [
            "greet",
            "calculate_stats",
            "on_player_joined",
            "on_player_left",
            "on_load",
            "on_unload"
        ]
        
        for method_name in methods:
            method = getattr(example_plugin, method_name)
            doc = method.__doc__
            assert doc is not None, f"Method {method_name} is missing a docstring"
            assert len(doc.strip()) > 0, f"Method {method_name} has an empty docstring"
            
            # Check for Args section in methods with parameters
            if method_name in ["greet", "calculate_stats", "on_player_joined", "on_player_left", "on_load"]:
                assert "Args:" in doc, f"Method {method_name} is missing 'Args:' section in docstring"
            
            # Check for Returns section in methods that return values
            if method_name in ["greet", "calculate_stats"]:
                assert "Returns:" in doc, f"Method {method_name} is missing 'Returns:' section in docstring"
                
        # Check that the greet tool has examples
        greet_doc = example_plugin.greet.__doc__
        assert "Examples:" in greet_doc
        assert ">>> greet(\"Alice\")" in greet_doc
        assert ">>> greet(\"Bob\", excited=True)" in greet_doc
