"""
Plugin system for VRChat MCP.

This module provides a plugin architecture for extending VRChat MCP functionality.
"""

import asyncio
import importlib
import inspect
import logging
import pkgutil
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PluginError(Exception):
    """Base class for plugin-related errors."""

    pass


class Plugin(ABC):
    """Base class for all VRChat MCP plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the plugin."""
        pass

    @property
    def version(self) -> str:
        """Return the version of the plugin."""
        return "1.0.0"

    @property
    def description(self) -> str:
        """Return a short description of the plugin."""
        return ""

    @abstractmethod
    async def on_load(self, mcp: Any) -> None:
        """Called when the plugin is loaded."""
        pass

    @abstractmethod
    async def on_unload(self) -> None:
        """Called when the plugin is unloaded."""
        pass


class PluginManager:
    """Manages the loading and unloading of plugins."""

    def __init__(self, mcp: Any):
        """Initialize the plugin manager."""
        self.mcp = mcp
        self.plugins: dict[str, Plugin] = {}
        self._discovered_plugins: dict[str, type[Plugin]] = {}

    async def discover_plugins(self, package: str = "vrchat_mcp.plugins") -> None:
        """Discover all plugins in the specified package."""
        try:
            package = importlib.import_module(package)
            package_path = Path(package.__file__).parent if hasattr(package, "__file__") else None

            if not package_path:
                logger.warning(f"Could not find path for package: {package}")
                return

            for _, name, is_pkg in pkgutil.iter_modules([str(package_path)]):
                if is_pkg or name.startswith("_"):
                    continue

                try:
                    module = importlib.import_module(f"{package.__name__}.{name}")
                    for _, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, Plugin) and obj != Plugin and not inspect.isabstract(obj):
                            plugin_name = obj.name if hasattr(obj, "name") else obj.__name__
                            self._discovered_plugins[plugin_name] = obj
                            logger.debug(f"Discovered plugin: {plugin_name}")
                except ImportError as e:
                    logger.error(f"Error importing plugin module {name}: {e}")
        except ImportError as e:
            logger.error(f"Error discovering plugins: {e}")

    async def load_plugin(self, plugin_class: type[Plugin], *args, **kwargs) -> Plugin | None:
        """Load a plugin by its class."""
        try:
            if not issubclass(plugin_class, Plugin):
                raise PluginError(f"{plugin_class.__name__} is not a valid plugin class")

            plugin = plugin_class(*args, **kwargs)
            await plugin.on_load(self.mcp)
            self.plugins[plugin.name] = plugin
            logger.info(f"Loaded plugin: {plugin.name} v{plugin.version}")
            return plugin
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_class.__name__}: {e}")
            return None

    async def load_plugin_by_name(self, name: str, *args, **kwargs) -> Plugin | None:
        """Load a plugin by its name from discovered plugins."""
        if name not in self._discovered_plugins:
            logger.error(f"Plugin not found: {name}")
            return None
        return await self.load_plugin(self._discovered_plugins[name], *args, **kwargs)

    async def unload_plugin(self, name: str) -> bool:
        """Unload a plugin by name."""
        if name not in self.plugins:
            logger.warning(f"Plugin not loaded: {name}")
            return False

        try:
            await self.plugins[name].on_unload()
            del self.plugins[name]
            logger.info(f"Unloaded plugin: {name}")
            return True
        except Exception as e:
            logger.error(f"Error unloading plugin {name}: {e}")
            return False

    async def unload_all(self) -> None:
        """Unload all plugins."""
        for name in list(self.plugins.keys()):
            await self.unload_plugin(name)

    def get_plugin(self, name: str) -> Plugin | None:
        """Get a loaded plugin by name."""
        return self.plugins.get(name)

    def get_plugins(self) -> list[Plugin]:
        """Get all loaded plugins."""
        return list(self.plugins.values())

    def get_discovered_plugins(self) -> dict[str, type[Plugin]]:
        """Get all discovered plugin classes."""
        return self._discovered_plugins.copy()


# Plugin decorators
def tool(
    name: str | None = None,
    description: str = "",
    category: str = "General",
    args: dict[str, dict[str, Any]] | None = None,
    returns: dict[str, Any] | None = None,
    examples: list[dict[str, Any]] | None = None,
    requires_auth: bool = False,
    rate_limit: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Create a tool from a method, making it available through the MCP interface.

    This decorator transforms a method into a tool that can be called through the MCP
    interface. The tool's metadata is used for documentation, validation, and
    discovery.

    The decorator supports both simple and complex tool definitions, with automatic
    extraction of parameter information from type hints and docstrings.

    Args:
        name: The name of the tool. If not provided, the function name will be used.
        description: A short description of what the tool does. If not provided,
                    the first line of the function's docstring will be used.
        category: The category this tool belongs to, used for organization in UIs.
        args: A dictionary defining the tool's parameters. Each key is a parameter
              name, and each value is a dictionary with parameter metadata:
              - type: The parameter type (string, number, boolean, object, array, or a Python type)
              - description: Description of the parameter
              - required: Whether the parameter is required (default: True)
              - default: Default value if not provided
              - example: Example value for documentation
        returns: A dictionary describing the return value:
                - type: The return type
                - description: Description of the return value
                - schema: Optional JSON schema for complex return types
        examples: List of example usages, each with:
                 - description: What the example demonstrates
                 - code: Example code snippet
                 - returns: Expected return value or description
        requires_auth: If True, the tool requires authentication to be called.
        rate_limit: Rate limiting configuration:
                   - calls: Maximum number of calls allowed
                   - interval: Time window in seconds
        **kwargs: Additional metadata that will be stored with the tool.

    Returns:
        A decorator that converts a method into an MCP tool.

    Note:
        The decorator will automatically extract parameter information from the
        function's type hints and docstring if they are not explicitly provided
        in the `args` parameter.
    """

    def decorator(method: Callable[..., Any]) -> Callable[..., Any]:
        # Get the function's docstring and signature
        doc = inspect.getdoc(method) or ""
        sig = inspect.signature(method)

        # Extract description from docstring if not provided
        final_description = description
        if not final_description and doc:
            # Get the first non-empty line as the short description
            final_description = next((line.strip() for line in doc.split("\n") if line.strip()), "")

        # Parse parameter information from docstring
        param_docs: dict[str, str] = {}
        if doc and "Args:" in doc:
            # Extract the Args section
            arg_section = doc.split("Args:")[1].split("Returns:")[0] if "Returns:" in doc else doc.split("Args:")[1]
            # Parse each parameter's documentation
            for param_block in arg_section.split("\n    ")[1:]:
                if ":" in param_block:
                    param_name = param_block.split(":")[0].strip()
                    param_desc = ":".join(param_block.split(":")[1:]).strip()
                    param_docs[param_name] = param_desc

        # Process parameters
        final_args: dict[str, dict[str, Any]] = {}

        # Start with explicitly provided args
        if args:
            for arg_name, arg_info in args.items():
                final_args[arg_name] = {
                    "type": arg_info.get("type", "string"),
                    "description": arg_info.get("description", param_docs.get(arg_name, "")),
                    "required": arg_info.get("required", True),
                    "default": arg_info.get("default"),
                    "example": arg_info.get("example"),
                }

        # Add parameters from type hints if not already defined
        for param_name, param in sig.parameters.items():
            if param_name == "self" or param_name in final_args:
                continue

            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                if hasattr(param.annotation, "__name__"):
                    param_type = param.annotation.__name__
                elif hasattr(param.annotation, "_name"):
                    param_type = param.annotation._name or "string"

            final_args[param_name] = {
                "type": param_type,
                "description": param_docs.get(param_name, ""),
                "required": param.default == inspect.Parameter.empty,
                "default": param.default if param.default != inspect.Parameter.empty else None,
            }

        # Process return type
        final_returns = returns or {}
        if not final_returns and "return" in method.__annotations__:
            return_type = method.__annotations__["return"]
            if hasattr(return_type, "__name__"):
                final_returns = {"type": return_type.__name__, "description": ""}

        # Get return description from docstring if available
        if doc and "Returns:" in doc:
            returns_section = doc.split("Returns:")[1]
            if "Raises:" in returns_section:
                returns_section = returns_section.split("Raises:")[0]
            returns_desc = returns_section.strip()
            if returns_desc:
                if not final_returns:
                    final_returns = {"type": "any"}
                final_returns["description"] = returns_desc

        # Create tool metadata
        method._is_tool = True
        method._tool_metadata = {
            "name": name or method.__name__,
            "description": final_description,
            "category": category,
            "args": final_args,
            "returns": final_returns,
            "examples": examples or [],
            "requires_auth": requires_auth,
            "rate_limit": rate_limit or {},
            "docstring": doc,
            "signature": str(sig),
            **kwargs,  # Include any additional metadata
        }

        # Preserve the original function and its attributes
        method._original = method
        method.__signature__ = sig  # For better help() and inspect support

        # Update the docstring to include the tool's metadata
        if not method.__doc__:
            method.__doc__ = final_description

        return method

    return decorator


def event_listener(event_type: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for marking methods as event listeners.

    This decorator registers a method to be called when a specific event occurs in the MCP system.
    The method will receive the event data as its first argument.

    Args:
        event_type: The type of event to listen for. This should be a string that
                   identifies the event, such as 'user_joined' or 'message_received'.

    Example:
        class MyPlugin(Plugin):
            @event_listener('user_joined')
            async def on_user_joined(self, user_data: Dict[str, Any]) -> None:
                # Handle user join events
                logger.info(f"User joined: {user_data['username']}")

    Note:
        The decorated method should be an async function that takes at least one argument
        (the event data) and returns None.
    """

    def decorator(method: Callable[..., Any]) -> Callable[..., Any]:
        if not asyncio.iscoroutinefunction(method):
            raise TypeError("Event listener must be an async function")

        # Get the method's signature to validate parameters
        sig = inspect.signature(method)
        params = list(sig.parameters.values())

        # Ensure the method has at least one parameter (self)
        if len(params) < 1:
            raise TypeError("Event listener must have at least 'self' parameter")

        # Store event listener metadata
        if not hasattr(method, "_event_listeners"):
            method._event_listeners = []

        method._event_listeners.append({"event_type": event_type, "method_name": method.__name__})

        # Preserve the original function's signature and docstring
        method._original = method
        method.__signature__ = sig

        return method

    return decorator
