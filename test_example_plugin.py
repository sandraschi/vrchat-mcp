#!/usr/bin/env python3
"""
Test the example plugin directly.

This script creates an instance of the example plugin and tests its functionality.
"""

import asyncio
from vrchat_mcp.plugins.example_plugin import ExamplePlugin

async def main():
    """Test the example plugin."""
    print("Creating example plugin...")
    plugin = ExamplePlugin()
    
    print(f"Plugin name: {plugin.name}")
    print(f"Version: {plugin.version}")
    print(f"Description: {plugin.description}")
    
    # Test the greet tool
    print("\nTesting greet tool:")
    result = plugin.greet("Alice")
    print(f"  greet('Alice') = {result}")
    
    result = plugin.greet("Bob", "Hi")
    print(f"  greet('Bob', 'Hi') = {result}")
    
    result = plugin.greet("Charlie", excited=True)
    print(f"  greet('Charlie', excited=True) = {result}")
    
    # Test the calculate_stats tool
    print("\nTesting calculate_stats tool:")
    numbers = [1, 2, 3, 4, 5]
    result = plugin.calculate_stats(numbers)
    print(f"  calculate_stats({numbers}) = {result}")
    
    # Test event listeners
    print("\nTesting event listeners:")
    print("  Emitting player_joined event...")
    await plugin.on_player_joined({"player_name": "TestUser", "player_id": "123"})
    
    print("  Emitting player_left event...")
    await plugin.on_player_left({"player_name": "TestUser", "player_id": "123"})
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
