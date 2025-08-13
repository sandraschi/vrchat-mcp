"""
VRChat MCP - A FastMCP 2.10 implementation for controlling VRChat avatars and assets.

This module provides a comprehensive interface for interacting with VRChat avatars,
including OSC control, parameter management, and NPC behavior.
"""

__version__ = "0.1.0"

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Set, List, Union

from fastmcp import FastMCP, JSONRPCRequest, JSONRPCResponse, JSONRPCError

# Import submodules
from .osc_inspector import OSCInspector, MessageDirection, MessageRecord
from .avatar_manager import AvatarManager
from .interpolation import InterpolationSystem, EasingFunction
from .debug_ui import DebugUI
from .models import AvatarState, ParameterValue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "osc": {
        "client_ip": "127.0.0.1",
        "client_port": 9000,
        "server_ip": "127.0.0.1",
        "server_port": 9001,
    },
    "debug_ui": {
        "enabled": True,
        "host": "0.0.0.0",
        "port": 8765
    },
    "logging": {
        "level": "INFO",
        "file": None
    }
}

class VRChatMCP:
    """Main VRChat MCP server class."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the VRChat MCP server.
        
        Args:
            config: Optional configuration dictionary. If not provided, defaults will be used.
        """
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        
        # Set up logging
        self._setup_logging()
        
        # Create the main MCP instance
        self.mcp = FastMCP(
            name="vrchat-mcp",
            version=__version__,
            description="MCP server for VRChat avatar and asset control",
            protocol=["stdio", "http"]
        )
        
        # Initialize components
        self.osc_inspector = OSCInspector(
            client_ip=self.config["osc"]["client_ip"],
            client_port=self.config["osc"]["client_port"],
            server_ip=self.config["osc"]["server_ip"],
            server_port=self.config["osc"]["server_port"]
        )
        
        self.interpolation = InterpolationSystem()
        self.avatar_manager = AvatarManager(
            osc_inspector=self.osc_inspector,
            interpolation=self.interpolation
        )
        
        # Debug UI
        self.debug_ui = None
        if self.config["debug_ui"]["enabled"]:
            self.debug_ui = DebugUI(
                osc_inspector=self.osc_inspector,
                host=self.config["debug_ui"]["host"],
                port=self.config["debug_ui"]["port"]
            )
        
        # Register tools
        self._register_tools()
    
    def _setup_logging(self) -> None:
        """Configure logging based on the configuration."""
        level = getattr(logging, self.config["logging"]["level"].upper(), logging.INFO)
        logging.basicConfig(level=level)
        
        if self.config["logging"].get("file"):
            file_handler = logging.FileHandler(self.config["logging"]["file"])
            file_handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ))
            logging.getLogger().addHandler(file_handler)
    
    def _register_tools(self) -> None:
        """Register all MCP tools."""
        @self.mcp.tool()
        async def get_avatar_state(avatar_id: str) -> Dict[str, Any]:
            """Get the current state of an avatar."""
            return await self.avatar_manager.get_avatar_state(avatar_id)
        
        @self.mcp.tool()
        async def set_parameter(avatar_id: str, parameter: str, value: float, interpolate: bool = False, duration: float = 0.5, easing: str = "linear") -> bool:
            """Set a parameter value for an avatar."""
            return await self.avatar_manager.set_parameter(
                avatar_id, parameter, value, interpolate, duration, easing
            )
        
        @self.mcp.tool()
        async def get_parameter(avatar_id: str, parameter: str) -> Optional[float]:
            """Get a parameter value for an avatar."""
            return await self.avatar_manager.get_parameter(avatar_id, parameter)
        
        @self.mcp.tool()
        async def send_osc_message(address: str, *args) -> bool:
            """Send an OSC message."""
            return await self.osc_inspector.send_message(address, *args)
        
        @self.mcp.tool()
        async def get_osc_statistics() -> Dict[str, Any]:
            """Get OSC communication statistics."""
            return self.osc_inspector.get_statistics()
    
    async def start(self) -> None:
        """Start the VRChat MCP server and all components."""
        logger.info("Starting VRChat MCP server...")
        
        # Start OSC inspector
        await self.osc_inspector.start()
        
        # Start debug UI if enabled
        if self.debug_ui:
            await self.debug_ui.start()
        
        # Start the MCP server
        await self.mcp.start()
    
    async def stop(self) -> None:
        """Stop the VRChat MCP server and all components."""
        logger.info("Stopping VRChat MCP server...")
        
        # Stop the MCP server
        if hasattr(self, 'mcp'):
            await self.mcp.stop()
        
        # Stop debug UI if enabled
        if hasattr(self, 'debug_ui') and self.debug_ui:
            await self.debug_ui.stop()
        
        # Stop OSC inspector
        if hasattr(self, 'osc_inspector') and self.osc_inspector.is_running():
            await self.osc_inspector.stop()
        
        logger.info("VRChat MCP server stopped")

# Create a default instance for convenience
mcp = VRChatMCP()

# Export commonly used types and classes
__all__ = [
    'VRChatMCP',
    'OSCInspector',
    'MessageDirection',
    'MessageRecord',
    'AvatarManager',
    'AvatarState',
    'ParameterValue',
    'InterpolationSystem',
    'EasingFunction',
    'DebugUI',
    'mcp'
]
