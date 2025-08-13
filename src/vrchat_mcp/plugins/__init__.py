"""
Plugin system for VRChat MCP.

This module provides a plugin architecture for extending VRChat MCP functionality.
"""

from typing import Type, Dict, List, Any, Optional, TypeVar, Generic
from abc import ABC, abstractmethod
from dataclasses import dataclass
import importlib
import inspect
import pkgutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

T = TypeVar('T')

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
    
    async def on_load(self, mcp: Any) -> None:
        """Called when the plugin is loaded."""
        pass
    
    async def on_unload(self) -> None:
        """Called when the plugin is unloaded."""
        pass

class PluginManager:
    """Manages the loading and unloading of plugins."""
    
    def __init__(self, mcp: Any):
        """Initialize the plugin manager."""
        self.mcp = mcp
        self.plugins: Dict[str, Plugin] = {}
        self._discovered_plugins: Dict[str, Type[Plugin]] = {}
    
    async def discover_plugins(self, package: str = 'vrchat_mcp.plugins') -> None:
        """Discover all plugins in the specified package."""
        try:
            package = importlib.import_module(package)
            package_path = Path(package.__file__).parent if hasattr(package, '__file__') else None
            
            if not package_path:
                logger.warning(f"Could not find path for package: {package}")
                return
            
            for _, name, is_pkg in pkgutil.iter_modules([str(package_path)]):
                if is_pkg or name.startswith('_'):
                    continue
                
                try:
                    module = importlib.import_module(f"{package.__name__}.{name}")
                    for _, obj in inspect.getmembers(module, inspect.isclass):
                        if (issubclass(obj, Plugin) and 
                                obj != Plugin and 
                                not inspect.isabstract(obj)):
                            plugin_name = obj.name if hasattr(obj, 'name') else obj.__name__
                            self._discovered_plugins[plugin_name] = obj
                            logger.debug(f"Discovered plugin: {plugin_name}")
                except ImportError as e:
                    logger.error(f"Error importing plugin module {name}: {e}")
        except ImportError as e:
            logger.error(f"Error discovering plugins: {e}")
    
    async def load_plugin(self, plugin_class: Type[Plugin], *args, **kwargs) -> Optional[Plugin]:
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
    
    async def load_plugin_by_name(self, name: str, *args, **kwargs) -> Optional[Plugin]:
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
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get a loaded plugin by name."""
        return self.plugins.get(name)
    
    def get_plugins(self) -> List[Plugin]:
        """Get all loaded plugins."""
        return list(self.plugins.values())
    
    def get_discovered_plugins(self) -> Dict[str, Type[Plugin]]:
        """Get all discovered plugin classes."""
        return self._discovered_plugins.copy()

# Plugin decorators
def tool(
    name: Optional[str] = None,
    description: str = "",
    category: str = "General",
    args: Optional[Dict[str, Any]] = None,
    returns: Optional[Dict[str, Any]] = None,
    examples: Optional[List[Dict[str, Any]]] = None
):
    """Decorator for creating MCP tools from plugin methods.
    
    Args:
        name: Tool name (defaults to method name)
        description: Tool description
        category: Tool category for organization
        args: Dictionary describing the tool's arguments
        returns: Dictionary describing the tool's return value
        examples: List of example usages
    """
    def decorator(method):
        method._is_tool = True
        method._tool_metadata = {
            'name': name or method.__name__,
            'description': description or method.__doc__ or "",
            'category': category,
            'args': args or {},
            'returns': returns or {},
            'examples': examples or []
        }
        return method
    return decorator

def event_listener(event_type: str):
    """Decorator for marking methods as event listeners."""
    def decorator(method):
        if not hasattr(method, '_event_listeners'):
            method._event_listeners = []
        method._event_listeners.append(event_type)
        return method
    return decorator
