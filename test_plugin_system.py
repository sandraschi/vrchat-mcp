#!/usr/bin/env python3
"""
Test script to verify the plugin system is working correctly.

This script loads all plugins and prints information about the registered tools
and event listeners.
"""

import asyncio
import importlib
import inspect
import os
import sys
from typing import Any, Dict, List, Type

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

# Import the Plugin base class
from src.vrchat_mcp.plugins import Plugin

def load_plugins() -> List[Type[Plugin]]:
    """Load all plugin classes from the plugins directory."""
    plugins_dir = os.path.join("src", "vrchat_mcp", "plugins")
    plugins = []
    
    for filename in os.listdir(plugins_dir):
        if filename.startswith('_') or not filename.endswith('.py'):
            continue
            
        module_name = filename[:-3]  # Remove .py extension
        try:
            # Import the module
            module = importlib.import_module(f"src.vrchat_mcp.plugins.{module_name}")
            
            # Find all classes that inherit from Plugin
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, Plugin) and 
                    obj is not Plugin and 
                    obj.__module__ == module.__name__):
                    plugins.append(obj)
                    print(f"Found plugin: {name}")
        except Exception as e:
            print(f"Error loading {filename}: {e}")
    
    return plugins

def print_plugin_info(plugin_class: Type[Plugin]) -> None:
    """Print information about a plugin's tools and event listeners."""
    plugin = plugin_class()
    
    print(f"\nPlugin: {plugin.name}")
    print(f"Version: {plugin.version}")
    print(f"Description: {plugin.description}")
    
    # Find tools (methods with _is_tool = True)
    tools = []
    for name, method in inspect.getmembers(plugin_class, inspect.isfunction):
        if hasattr(method, "_is_tool") and method._is_tool:
            tools.append((name, method))
    
    if tools:
        print("\nTools:")
        for name, method in tools:
            meta = getattr(method, "_tool_metadata", {})
            print(f"  {name}")
            print(f"    Description: {meta.get('description', 'No description')}")
            print(f"    Category: {meta.get('category', 'Uncategorized')}")
            print(f"    Requires auth: {meta.get('requires_auth', False)}")
    
    # Find event listeners (methods with _event_listeners)
    event_listeners = []
    for name, method in inspect.getmembers(plugin_class, inspect.isfunction):
        if hasattr(method, "_event_listeners"):
            for listener in method._event_listeners:
                event_listeners.append((name, listener.get('event_type', 'unknown')))
    
    if event_listeners:
        print("\nEvent Listeners:")
        for method_name, event_type in event_listeners:
            print(f"  {method_name} (event: {event_type})")

async def main():
    """Main function to test the plugin system."""
    print("Loading plugins...")
    plugins = load_plugins()
    
    if not plugins:
        print("No plugins found!")
        return
    
    print(f"\nFound {len(plugins)} plugins:")
    for plugin_class in plugins:
        print_plugin_info(plugin_class)
    
    # Test creating an instance of each plugin
    print("\nTesting plugin instantiation...")
    for plugin_class in plugins:
        try:
            plugin = plugin_class()
            print(f"  Successfully created instance of {plugin.name}")
            
            # Test on_load if it exists
            if hasattr(plugin, 'on_load'):
                print(f"  Testing on_load for {plugin.name}...")
                await plugin.on_load(None)  # Pass None as MCP server for now
                print(f"  on_load completed for {plugin.name}")
            
            # Test a tool if available
            for name, method in inspect.getmembers(plugin, inspect.ismethod):
                if hasattr(method, "_is_tool") and method._is_tool:
                    print(f"  Testing tool: {name}")
                    try:
                        # Get the method's signature to determine required parameters
                        sig = inspect.signature(method)
                        params = list(sig.parameters.values())
                        
                        # Skip 'self' parameter
                        if len(params) > 1 and params[1].name == 'param1':
                            # This is a simple test for our example plugin's greet method
                            if len(params) == 3:  # self, param1, param2 with default
                                result = method("TestUser")
                                print(f"    Result: {result}")
                            else:
                                print(f"    Skipping test for {name} - unsupported signature")
                        else:
                            print(f"    No test available for {name} - skipping")
                    except Exception as e:
                        print(f"    Error testing {name}: {e}")
            
            # Test on_unload if it exists
            if hasattr(plugin, 'on_unload'):
                print(f"  Testing on_unload for {plugin.name}...")
                await plugin.on_unload()
                print(f"  on_unload completed for {plugin.name}")
            
            print()
            
        except Exception as e:
            print(f"  Error creating instance of {plugin_class.__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
