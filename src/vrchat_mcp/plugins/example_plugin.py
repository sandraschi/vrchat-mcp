"""
Example plugin demonstrating the use of @tool and @event_listener decorators.

This plugin serves as a reference implementation for creating new plugins with
the VRChat MCP framework.
"""

import logging
from typing import Any, Dict, List, Optional

from vrchat_mcp.plugins import Plugin, tool, event_listener

logger = logging.getLogger(__name__)

class ExamplePlugin(Plugin):
    """Example plugin demonstrating tool and event listener registration."""
    
    @property
    def name(self) -> str:
        """Return the name of the plugin."""
        return "example_plugin"
    
    @property
    def version(self) -> str:
        """Return the version of the plugin."""
        return "1.0.0"
    
    @property
    def description(self) -> str:
        """Return a short description of the plugin."""
        return "An example plugin demonstrating tool and event listener registration."
    
    @tool(
        name="greet",
        category="Examples",
        description="Generate a greeting message.",
        args={
            "name": {
                "type": "string",
                "description": "The name to include in the greeting.",
                "required": True
            },
            "greeting": {
                "type": "string",
                "description": "The greeting to use (default: 'Hello').",
                "default": "Hello",
                "required": False
            },
            "excited": {
                "type": "boolean",
                "description": "Whether to add an exclamation mark.",
                "default": False,
                "required": False
            }
        },
        returns={
            "type": "string",
            "description": "The generated greeting message.",
        },
        requires_auth=False,
        rate_limit={"calls": 60, "interval": 60}  # 60 calls per minute
    )
    def greet(self, name: str, greeting: str = "Hello", excited: bool = False) -> str:
        """Generate a greeting message.
        
        This tool creates a personalized greeting message based on the provided
        parameters. It demonstrates how to use the @tool decorator with various
        parameter types and documentation.
        
        Args:
            name: The name to include in the greeting.
            greeting: The greeting to use (default: 'Hello').
            excited: Whether to add an exclamation mark (default: False).
            
        Returns:
            A string containing the generated greeting message.
            
        Examples:
            >>> greet("Alice")
            'Hello, Alice.'
            >>> greet("Bob", "Hi", excited=True)
            'Hi, Bob!'
        """
        message = f"{greeting}, {name}."
        if excited:
            message = message[:-1] + "!"  # Replace period with exclamation
        return message
    
    @tool(
        name="calculate_stats",
        category="Examples",
        description="Calculate basic statistics from a list of numbers.",
        args={
            "numbers": {
                "type": "array",
                "items": {"type": "number"},
                "description": "List of numbers to analyze.",
                "required": True
            }
        },
        returns={
            "type": "object",
            "description": "Dictionary containing calculated statistics.",
            "schema": {
                "count": {"type": "integer", "description": "Number of elements"},
                "sum": {"type": "number", "description": "Sum of all numbers"},
                "average": {"type": "number", "description": "Arithmetic mean"},
                "min": {"type": "number", "description": "Minimum value"},
                "max": {"type": "number", "description": "Maximum value"}
            }
        },
        requires_auth=True,
        rate_limit={"calls": 30, "interval": 60}  # 30 calls per minute
    )
    def calculate_stats(self, numbers: List[float]) -> Dict[str, float]:
        """Calculate basic statistics from a list of numbers.
        
        This tool demonstrates how to work with list parameters and return
        complex data structures. It also shows how to mark a tool as requiring
        authentication.
        
        Args:
            numbers: A list of numbers to analyze.
            
        Returns:
            A dictionary containing the count, sum, average, min, and max of the
            input numbers.
            
        Raises:
            ValueError: If the input list is empty.
            
        Examples:
            >>> calculate_stats([1, 2, 3, 4, 5])
            {'count': 5, 'sum': 15, 'average': 3.0, 'min': 1, 'max': 5}
        """
        if not numbers:
            raise ValueError("Cannot calculate statistics for an empty list")
            
        return {
            "count": len(numbers),
            "sum": sum(numbers),
            "average": sum(numbers) / len(numbers),
            "min": min(numbers),
            "max": max(numbers)
        }
    
    @event_listener("player_joined")
    async def on_player_joined(self, event_data: Dict[str, Any]) -> None:
        """Handle player_joined events.
        
        This method is called whenever a player joins the instance. It demonstrates
        how to use the @event_listener decorator to respond to events.
        
        Args:
            event_data: Dictionary containing event details. Expected to have at least
                      'player_name' and 'player_id' keys.
        """
        player_name = event_data.get('player_name', 'Unknown player')
        logger.info(f"{player_name} has joined the instance!")
    
    @event_listener("player_left")
    async def on_player_left(self, event_data: Dict[str, Any]) -> None:
        """Handle player_left events.
        
        This method is called whenever a player leaves the instance.
        
        Args:
            event_data: Dictionary containing event details. Expected to have at least
                      'player_name' and 'player_id' keys.
        """
        player_name = event_data.get('player_name', 'A player')
        logger.info(f"{player_name} has left the instance.")
    
    async def on_load(self, mcp: Any) -> None:
        """Called when the plugin is loaded.
        
        Args:
            mcp: Reference to the MCP server instance.
        """
        logger.info(f"{self.name} v{self.version} loaded!")
    
    async def on_unload(self) -> None:
        """Called when the plugin is unloaded."""
        logger.info(f"{self.name} v{self.version} unloaded!")
