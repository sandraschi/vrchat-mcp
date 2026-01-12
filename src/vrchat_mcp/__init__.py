"""
VRChat MCP - A FastMCP 2.10 implementation for controlling VRChat avatars and assets.

This module provides a comprehensive interface for interacting with VRChat avatars,
including OSC control, parameter management, and NPC behavior.
"""

__version__ = "0.1.0"

import asyncio
import logging
import os
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, Optional, Set, List, Union

from fastmcp import FastMCP
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import Tool

# Import submodules
from .osc_inspector import OSCInspector, MessageDirection, MessageRecord
from .tools import AvatarManager, OSCManager
from .interpolation import InterpolationSystem, EasingFunction
from .osc import OSCManager
from .web_interface import WebInterface
from .api_manager import APIManager
from .secrets import secrets_manager
from .debug_ui import DebugUI
from .models import AvatarState, ParameterValue

# Configure logging (MCP servers must use stderr, not stdout)
import sys
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter using sliding window."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(lambda: deque(maxlen=requests_per_minute))
        self.lock = asyncio.Lock()

    async def is_allowed(self, client_id: str = "default") -> bool:
        """Check if request is allowed under rate limit."""
        async with self.lock:
            now = time.time()
            request_times = self.requests[client_id]

            # Remove old requests outside the window
            while request_times and now - request_times[0] > 60:
                request_times.popleft()

            # Check if under limit
            if len(request_times) < self.requests_per_minute:
                request_times.append(now)
                return True

            return False

    async def get_remaining_requests(self, client_id: str = "default") -> int:
        """Get remaining requests allowed in current window."""
        async with self.lock:
            now = time.time()
            request_times = self.requests[client_id]

            # Clean up old requests
            while request_times and now - request_times[0] > 60:
                request_times.popleft()

            return max(0, self.requests_per_minute - len(request_times))


class PerformanceMonitor:
    """Monitor performance metrics for the MCP server."""

    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        self.response_times = deque(maxlen=1000)  # Keep last 1000 response times
        self.start_time = time.time()
        self.lock = asyncio.Lock()

    async def record_request(self, response_time: float, success: bool = True):
        """Record a request with its response time."""
        async with self.lock:
            self.request_count += 1
            if not success:
                self.error_count += 1
            self.total_response_time += response_time
            self.response_times.append(response_time)

    async def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        async with self.lock:
            uptime = time.time() - self.start_time
            avg_response_time = (
                self.total_response_time / self.request_count
                if self.request_count > 0
                else 0
            )
            error_rate = (
                self.error_count / self.request_count * 100
                if self.request_count > 0
                else 0
            )

            return {
                "uptime_seconds": uptime,
                "total_requests": self.request_count,
                "error_count": self.error_count,
                "error_rate_percent": round(error_rate, 2),
                "avg_response_time_ms": round(avg_response_time * 1000, 2),
                "requests_per_second": round(self.request_count / uptime, 2)
                if uptime > 0
                else 0,
                "recent_response_times_count": len(self.response_times),
                "min_recent_response_time_ms": round(min(self.response_times) * 1000, 2)
                if self.response_times
                else 0,
                "max_recent_response_time_ms": round(max(self.response_times) * 1000, 2)
                if self.response_times
                else 0,
            }


# Default configuration
DEFAULT_CONFIG = {
    "rate_limiting": {"requests_per_minute": 60, "enabled": True},
    "osc": {
        "client_ip": "127.0.0.1",
        "client_port": 9000,
        "server_ip": "127.0.0.1",
        "server_port": 9001,
    },
    "debug_ui": {"enabled": True, "host": "0.0.0.0", "port": 8765},
    "logging": {"level": "INFO", "file": None},
}


class VRChatMCP:
    """Main VRChat MCP server class."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, mode: str = "dual"):
        """Initialize the VRChat MCP server.

        Args:
            config: Optional configuration dictionary. If not provided, defaults will be used.
            mode: Server mode - "dual", "mcp" (stdio), or "fastapi" (HTTP)
        """
        self.config = secrets_manager.load_config_with_secrets(
            {**DEFAULT_CONFIG, **(config or {})}
        )
        self.mode = mode

        # Set up logging
        self._setup_logging()

        # Only create HTTP-enabled instance for dual/fastapi modes
        if mode in ["dual", "fastapi"]:
            # Create the main MCP instance with dual interface support
            self.mcp = FastMCP(
                name="vrchat-mcp",
                instructions="MCP server for VRChat avatar and asset control",
            )

            # Add FastAPI endpoints for health and docs (required by production checklist)
            @self.mcp.custom_route("/health", methods=["GET"])
            async def health_endpoint():
                """Health check endpoint returning server status."""
                import time

                return {
                    "status": "healthy",
                    "server": "vrchat-mcp",
                    "version": __version__,
                    "interfaces": ["mcp_stdio", "fastapi_http"],
                    "timestamp": time.time(),
                }

            @self.mcp.custom_route("/api/v1/openapi.json", methods=["GET"])
            async def openapi_json():
                """OpenAPI schema endpoint."""
                return {
                    "openapi": "3.1.0",
                    "info": {"title": "VRChat MCP API", "version": __version__},
                    "paths": {},
                }

            @self.mcp.custom_route("/api/docs", methods=["GET"])
            async def api_docs():
                """OpenAPI documentation endpoint."""
                return {"message": "OpenAPI docs available at /docs"}

            # Initialize web interface
            self.web_interface = WebInterface(self, self.config.get("web", {}))

            # Initialize API Manager
            self.api_manager = APIManager(self.config)
        else:
            # For MCP-only mode, don't create HTTP components
            self.mcp = None
            self.web_interface = None
            self.api_manager = None
        # Initialize components
        self.osc_inspector = OSCInspector(
            client_ip=self.config["osc"]["client_ip"],
            client_port=self.config["osc"]["client_port"],
            server_ip=self.config["osc"]["server_ip"],
            server_port=self.config["osc"]["server_port"],
        )

        # Initialize OSC manager for tools
        osc_config = {
            "send_host": self.config["osc"]["client_ip"],
            "send_port": self.config["osc"]["client_port"],
            "receive_host": self.config["osc"]["server_ip"],
            "receive_port": self.config["osc"]["server_port"],
        }
        self.osc_manager = OSCManager(osc_config)

        self.interpolation = InterpolationSystem()
        self.avatar_manager = AvatarManager(
            osc_manager=self.osc_manager, interpolation_system=self.interpolation
        )

        # Rate limiting and performance monitoring
        rate_limit = self.config.get("rate_limiting", {}).get("requests_per_minute", 60)
        self.rate_limiter = RateLimiter(requests_per_minute=rate_limit)
        self.performance_monitor = PerformanceMonitor()

        # Debug UI
        self.debug_ui = None
        if self.config["debug_ui"]["enabled"]:
            self.debug_ui = DebugUI(
                osc_inspector=self.osc_inspector,
                host=self.config["debug_ui"]["host"],
                port=self.config["debug_ui"]["port"],
            )

        # Register tools on the main instance (only for dual/fastapi modes)
        if self.mcp is not None:
            self._register_tools_on_instance(self.mcp)

    def _setup_logging(self) -> None:
        """Configure logging based on the configuration."""
        level = getattr(logging, self.config["logging"]["level"].upper(), logging.INFO)
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stderr)],
        )

        if self.config["logging"].get("file"):
            file_handler = logging.FileHandler(self.config["logging"]["file"])
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            logging.getLogger().addHandler(file_handler)

    def _register_tools_on_instance(self, mcp_instance) -> None:
        """Register all MCP tools on a specific FastMCP instance."""
        # API Tools
        self._register_api_tools_on_instance(mcp_instance)

        @mcp_instance.tool()
        async def get_avatar_state(avatar_id: str) -> Dict[str, Any]:
            """Get the current state of an avatar."""
            return await self.avatar_manager.get_avatar_state(avatar_id)

        @mcp_instance.tool()
        async def load_avatar(avatar_id: str) -> Dict[str, Any]:
            """Load an avatar by ID."""
            return await self.avatar_manager.load_avatar(avatar_id)

        @mcp_instance.tool()
        async def set_parameter(
            avatar_id: str,
            parameter: str,
            value: Union[bool, float, int, str],
            interpolate: bool = False,
            duration: float = 0.5,
            easing: str = "linear",
        ) -> bool:
            """Set a parameter value for an avatar with optional interpolation."""
            return await self.avatar_manager.set_parameter(
                avatar_id, parameter, value, interpolate, duration, easing
            )

        @mcp_instance.tool()
        async def get_parameter(
            avatar_id: str, parameter: str
        ) -> Optional[Union[bool, float, int, str]]:
            """Get a parameter value for an avatar."""
            return await self.avatar_manager.get_parameter(avatar_id, parameter)

        @mcp_instance.tool()
        async def send_osc_message(
            address: str, args: List[Union[bool, float, int, str]]
        ) -> bool:
            """Send an OSC message.

            Args:
                address: OSC address (e.g., "/avatar/parameters/TestParam")
                args: List of arguments to send with the message

            Returns:
                True if message was sent successfully
            """
            try:
                # Create OSCMessage and send it
                from .models import OSCMessage

                message = OSCMessage(address=address, args=args)
                await self.osc_manager.send_message(message)
                return True
            except Exception as e:
                logger.error(f"Failed to send OSC message: {e}")
                return False

        @mcp_instance.tool()
        async def get_osc_statistics() -> Dict[str, Any]:
            """Get OSC communication statistics."""
            return self.osc_inspector.get_statistics()

        # System and Help Tools (required by MCP Production Checklist)
        @mcp_instance.tool()
        async def get_server_status() -> Dict[str, Any]:
            """Get comprehensive server status information."""
            return {
                "server": "vrchat-mcp",
                "version": __version__,
                "status": "running",
                "interfaces": ["mcp_stdio"],
                "components": {
                    "osc_inspector": self.osc_inspector.is_running()
                    if hasattr(self.osc_inspector, "is_running")
                    else True,
                    "avatar_manager": True,
                    "debug_ui": self.debug_ui is not None,
                    "interpolation": True,
                },
                "config": {
                    "osc_client": f"{self.config['osc']['client_ip']}:{self.config['osc']['client_port']}",
                    "osc_server": f"{self.config['osc']['server_ip']}:{self.config['osc']['server_port']}",
                    "debug_ui_enabled": self.config["debug_ui"]["enabled"],
                },
            }

        @mcp_instance.tool()
        async def get_health_status() -> Dict[str, Any]:
            """Get health check status (returns 200 OK for HTTP health endpoint)."""
            return {
                "status": "healthy",
                "timestamp": asyncio.get_event_loop().time(),
                "services": {
                    "osc": "healthy"
                    if hasattr(self.osc_inspector, "is_running")
                    and self.osc_inspector.is_running()
                    else "unknown",
                    "avatar_manager": "healthy",
                    "interpolation": "healthy",
                },
            }

        @mcp_instance.tool()
        async def get_performance_metrics() -> Dict[str, Any]:
            """Get comprehensive performance metrics for the MCP server.

            Returns:
                Dictionary containing uptime, request counts, response times, and error rates.
            """
            try:
                metrics = await self.performance_monitor.get_metrics()
                return {"status": "success", "metrics": metrics}
            except Exception as e:
                logger.error(f"Failed to get performance metrics: {e}")
                return {"status": "error", "error": str(e)}

        @mcp_instance.tool()
        async def check_rate_limit(client_id: str = "default") -> Dict[str, Any]:
            """Check current rate limit status for a client.

            Args:
                client_id: Identifier for the client (default: "default")

            Returns:
                Dictionary with rate limit status and remaining requests.
            """
            try:
                remaining = await self.rate_limiter.get_remaining_requests(client_id)
                allowed = await self.rate_limiter.is_allowed(client_id)

                return {
                    "status": "success",
                    "client_id": client_id,
                    "requests_remaining": remaining,
                    "can_make_request": allowed,
                    "rate_limit": self.rate_limiter.requests_per_minute,
                }
            except Exception as e:
                logger.error(f"Failed to check rate limit: {e}")
                return {"status": "error", "error": str(e)}

        @mcp_instance.tool()
        async def manage_secrets(
            action: str, key: str = "", value: Any = None, encrypted: bool = False
        ) -> Dict[str, Any]:
            """Manage sensitive configuration secrets.

            Args:
                action: Action to perform ("get", "set", "list", "validate")
                key: Secret key name (required for get/set)
                value: Value to set (required for set)
                encrypted: Whether to encrypt the secret (for set action)

            Returns:
                Dictionary with operation result
            """
            try:
                if action == "get":
                    if not key:
                        return {
                            "status": "error",
                            "error": "Key required for get action",
                        }
                    secret_value = secrets_manager.get_secret(key, encrypted=encrypted)
                    return {
                        "status": "success",
                        "key": key,
                        "value": secret_value,
                        "encrypted": encrypted,
                    }

                elif action == "set":
                    if not key or value is None:
                        return {
                            "status": "error",
                            "error": "Key and value required for set action",
                        }
                    success = secrets_manager.set_secret(
                        key, value, encrypted=encrypted
                    )
                    return {
                        "status": "success" if success else "error",
                        "key": key,
                        "encrypted": encrypted,
                    }

                elif action == "list":
                    secrets = secrets_manager.get_available_secrets()
                    return {"status": "success", "secrets": secrets}

                elif action == "validate":
                    validation = secrets_manager.validate_secrets_access()
                    return {"status": "success", "validation": validation}

                else:
                    return {"status": "error", "error": f"Unknown action: {action}"}

            except Exception as e:
                logger.error(f"Failed to manage secrets: {e}")
                return {"status": "error", "error": str(e)}

        @mcp_instance.tool()
        async def get_help(topic: str = "general") -> Dict[str, Any]:
            """Get multilevel help information about VRChat MCP tools and usage.

            Args:
                topic: Help topic to get information about. Options:
                      - "general": General usage and available tools
                      - "tools": Detailed tool descriptions
                      - "osc": OSC communication help
                      - "avatars": Avatar management help
                      - "config": Configuration help
                      - "api": HTTP API usage
            """
            help_content = {
                "general": {
                    "description": "VRChat MCP Server provides control over VRChat avatars and assets via OSC protocol",
                    "interfaces": ["MCP stdio protocol"],
                    "tools": ["avatar", "parameter", "osc", "system"],
                    "usage": "Use 'get_help' with specific topic for detailed information",
                },
                "tools": {
                    "avatar_tools": [
                        "get_avatar_state",
                        "set_parameter",
                        "get_parameter",
                    ],
                    "osc_tools": ["send_osc_message", "get_osc_statistics"],
                    "system_tools": [
                        "get_server_status",
                        "get_health_status",
                        "get_help",
                    ],
                    "description": "Tools are organized by functionality categories",
                },
                "osc": {
                    "description": "OSC (Open Sound Control) communication with VRChat",
                    "default_ports": "Client: 9000, Server: 9001",
                    "addresses": "VRChat parameters start with /avatar/parameters/",
                    "monitoring": "Use get_osc_statistics() to monitor communication",
                },
                "avatars": {
                    "description": "Avatar state and parameter management",
                    "loading": "Use set_parameter() to change avatar parameters",
                    "interpolation": "Parameters support smooth interpolation with easing",
                    "monitoring": "Use get_avatar_state() to check current values",
                },
                "config": {
                    "description": "Server configuration options",
                    "osc_settings": "IP addresses and ports for OSC communication",
                    "debug_ui": "Web-based debug interface (default port 8765)",
                    "logging": "Configurable logging levels and file output",
                },
                "api": {
                    "description": "HTTP API access via FastAPI",
                    "note": "HTTP API not available in MCP-only mode",
                },
            }

            return help_content.get(
                topic,
                {
                    "error": f"Unknown help topic: {topic}",
                    "available_topics": list(help_content.keys()),
                },
            )

    def _register_api_tools_on_instance(self, mcp_instance) -> None:
        """Register API-related tools on a specific FastMCP instance."""
        # Stub implementation - API tools can be added here later
        pass

    async def _run_pure_mcp_stdio(self) -> None:
        """Run a pure MCP stdio server without FastMCP HTTP components."""
        server = Server(
            name="vrchat-mcp",
            instructions="MCP server for VRChat avatar and asset control",
        )

        # Register tools using raw MCP API
        @server.call_tool()
        async def get_avatar_state(avatar_id: str) -> Dict[str, Any]:
            """Get the current state of an avatar."""
            return await self.avatar_manager.get_avatar_state(avatar_id)

        @server.call_tool()
        async def load_avatar(avatar_id: str) -> Dict[str, Any]:
            """Load an avatar by ID."""
            return await self.avatar_manager.load_avatar(avatar_id)

        @server.call_tool()
        async def set_parameter(
            avatar_id: str,
            parameter: str,
            value: Union[bool, float, int, str],
            interpolate: bool = False,
            duration: float = 0.5,
            easing: str = "linear",
        ) -> bool:
            """Set a parameter value for an avatar with optional interpolation."""
            return await self.avatar_manager.set_parameter(
                avatar_id, parameter, value, interpolate, duration, easing
            )

        @server.call_tool()
        async def get_parameter(
            avatar_id: str, parameter: str
        ) -> Optional[Union[bool, float, int, str]]:
            """Get a parameter value for an avatar."""
            return await self.avatar_manager.get_parameter(avatar_id, parameter)

        @server.call_tool()
        async def send_osc_message(
            address: str, args: List[Union[bool, float, int, str]]
        ) -> bool:
            """Send an OSC message.

            Args:
                address: OSC address (e.g., "/avatar/parameters/TestParam")
                args: List of arguments to send with the message

            Returns:
                True if message was sent successfully
            """
            try:
                # Create OSCMessage and send it
                from .models import OSCMessage

                message = OSCMessage(address=address, args=args)
                await self.osc_manager.send_message(message)
                return True
            except Exception as e:
                logger.error(f"Failed to send OSC message: {e}")
                return False

        @server.call_tool()
        async def get_osc_statistics() -> Dict[str, Any]:
            """Get OSC communication statistics."""
            return self.osc_inspector.get_statistics()

        # System and Help Tools (required by MCP Production Checklist)
        @server.call_tool()
        async def get_server_status() -> Dict[str, Any]:
            """Get comprehensive server status information."""
            return {
                "server": "vrchat-mcp",
                "version": __version__,
                "status": "running",
                "interfaces": ["mcp_stdio"],
                "components": {
                    "osc_inspector": self.osc_inspector.is_running()
                    if hasattr(self.osc_inspector, "is_running")
                    else True,
                    "avatar_manager": True,
                    "debug_ui": self.debug_ui is not None,
                    "interpolation": True,
                },
                "config": {
                    "osc_client": f"{self.config['osc']['client_ip']}:{self.config['osc']['client_port']}",
                    "osc_server": f"{self.config['osc']['server_ip']}:{self.config['osc']['server_port']}",
                    "debug_ui_enabled": self.config["debug_ui"]["enabled"],
                },
            }

        @server.call_tool()
        async def get_health_status() -> Dict[str, Any]:
            """Get health check status (returns 200 OK for HTTP health endpoint)."""
            return {
                "status": "healthy",
                "timestamp": asyncio.get_event_loop().time(),
                "services": {
                    "osc": "healthy"
                    if hasattr(self.osc_inspector, "is_running")
                    and self.osc_inspector.is_running()
                    else "unknown",
                    "avatar_manager": "healthy",
                    "interpolation": "healthy",
                },
            }

        @server.call_tool()
        async def get_performance_metrics() -> Dict[str, Any]:
            """Get comprehensive performance metrics for the MCP server.

            Returns:
                Dictionary containing uptime, request counts, response times, and error rates.
            """
            try:
                metrics = await self.performance_monitor.get_metrics()
                return {"status": "success", "metrics": metrics}
            except Exception as e:
                logger.error(f"Failed to get performance metrics: {e}")
                return {"status": "error", "error": str(e)}

        @server.call_tool()
        async def check_rate_limit(client_id: str = "default") -> Dict[str, Any]:
            """Check current rate limit status for a client.

            Args:
                client_id: Identifier for the client (default: "default")

            Returns:
                Dictionary with rate limit status and remaining requests.
            """
            try:
                remaining = await self.rate_limiter.get_remaining_requests(client_id)
                allowed = await self.rate_limiter.is_allowed(client_id)

                return {
                    "status": "success",
                    "client_id": client_id,
                    "requests_remaining": remaining,
                    "can_make_request": allowed,
                    "rate_limit": self.rate_limiter.requests_per_minute,
                }
            except Exception as e:
                logger.error(f"Failed to check rate limit: {e}")
                return {"status": "error", "error": str(e)}

        @server.call_tool()
        async def manage_secrets(
            action: str, key: str = "", value: Any = None, encrypted: bool = False
        ) -> Dict[str, Any]:
            """Manage sensitive configuration secrets.

            Args:
                action: Action to perform ("get", "set", "list", "validate")
                key: Secret key name (required for get/set)
                value: Value to set (required for set)
                encrypted: Whether to encrypt the secret (for set action)

            Returns:
                Dictionary with operation result
            """
            try:
                if action == "get":
                    if not key:
                        return {
                            "status": "error",
                            "error": "Key required for get action",
                        }
                    secret_value = secrets_manager.get_secret(key, encrypted=encrypted)
                    return {
                        "status": "success",
                        "key": key,
                        "value": secret_value,
                        "encrypted": encrypted,
                    }

                elif action == "set":
                    if not key or value is None:
                        return {
                            "status": "error",
                            "error": "Key and value required for set action",
                        }
                    success = secrets_manager.set_secret(
                        key, value, encrypted=encrypted
                    )
                    return {
                        "status": "success" if success else "error",
                        "key": key,
                        "encrypted": encrypted,
                    }

                elif action == "list":
                    secrets = secrets_manager.get_available_secrets()
                    return {"status": "success", "secrets": secrets}

                elif action == "validate":
                    validation = secrets_manager.validate_secrets_access()
                    return {"status": "success", "validation": validation}

                else:
                    return {"status": "error", "error": f"Unknown action: {action}"}

            except Exception as e:
                logger.error(f"Failed to manage secrets: {e}")
                return {"status": "error", "error": str(e)}

        @server.call_tool()
        async def get_help(topic: str = "general") -> Dict[str, Any]:
            """Get multilevel help information about VRChat MCP tools and usage.

            Args:
                topic: Help topic to get information about. Options:
                      - "general": General usage and available tools
                      - "tools": Detailed tool descriptions
                      - "osc": OSC communication help
                      - "avatars": Avatar management help
                      - "config": Configuration help
                      - "api": HTTP API usage
            """
            help_content = {
                "general": {
                    "description": "VRChat MCP Server provides control over VRChat avatars and assets via OSC protocol",
                    "interfaces": ["MCP stdio protocol"],
                    "tools": ["avatar", "parameter", "osc", "system"],
                    "usage": "Use 'get_help' with specific topic for detailed information",
                },
                "tools": {
                    "avatar_tools": [
                        "get_avatar_state",
                        "set_parameter",
                        "get_parameter",
                    ],
                    "osc_tools": ["send_osc_message", "get_osc_statistics"],
                    "system_tools": [
                        "get_server_status",
                        "get_health_status",
                        "get_help",
                    ],
                    "description": "Tools are organized by functionality categories",
                },
                "osc": {
                    "description": "OSC (Open Sound Control) communication with VRChat",
                    "default_ports": "Client: 9000, Server: 9001",
                    "addresses": "VRChat parameters start with /avatar/parameters/",
                    "monitoring": "Use get_osc_statistics() to monitor communication",
                },
                "avatars": {
                    "description": "Avatar state and parameter management",
                    "loading": "Use set_parameter() to change avatar parameters",
                    "interpolation": "Parameters support smooth interpolation with easing",
                    "monitoring": "Use get_avatar_state() to check current values",
                },
                "config": {
                    "description": "Server configuration options",
                    "osc_settings": "IP addresses and ports for OSC communication",
                    "debug_ui": "Web-based debug interface (default port 8765)",
                    "logging": "Configurable logging levels and file output",
                },
                "api": {
                    "description": "HTTP API access via FastAPI",
                    "note": "HTTP API not available in MCP-only mode",
                },
            }

            return help_content.get(
                topic,
                {
                    "error": f"Unknown help topic: {topic}",
                    "available_topics": list(help_content.keys()),
                },
            )

        # Run the server with stdio transport
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )

    def _register_tools(self) -> None:
        """Register all MCP tools on the main instance."""
        self._register_tools_on_instance(self.mcp)

    async def start(
        self, mode: str = "dual", host: str = "127.0.0.1", port: int = 8000
    ) -> None:
        """Start the VRChat MCP server and all components.

        Args:
            mode: Server mode - "dual", "mcp" (stdio), or "fastapi" (HTTP)
            host: Host for HTTP server
            port: Port for HTTP server
        """
        logger.info(f"Starting VRChat MCP server in {mode} mode...")

        # Start OSC inspector (optional for HTTP server)
        try:
            await self.osc_inspector.start()
        except Exception as e:
            logger.warning(
                f"Failed to start OSC inspector: {e}. HTTP server will work without OSC functionality."
            )

        # Start debug UI if enabled
        if self.debug_ui:
            await self.debug_ui.start()

        # Start the MCP server based on mode
        if mode in ["dual", "fastapi"]:
            # For dual/fastapi mode, start HTTP server
            logger.info(f"Starting FastAPI HTTP server on {host}:{port}")
            await self.mcp.run_http_async(host=host, port=port)
        elif mode == "mcp":
            # For MCP-only mode, use pure MCP stdio server without FastMCP
            logger.info("Starting pure MCP stdio server")
            await self._run_pure_mcp_stdio()
        else:
            raise ValueError(f"Unknown server mode: {mode}")

    async def stop(self) -> None:
        """Stop the VRChat MCP server and all components."""
        logger.info("Stopping VRChat MCP server...")

        # Stop the MCP server
        if hasattr(self, "mcp") and self.mcp is not None:
            await self.mcp.stop()

        # Stop debug UI if enabled
        if hasattr(self, "debug_ui") and self.debug_ui:
            await self.debug_ui.stop()

        # Stop OSC inspector
        if hasattr(self, "osc_inspector") and self.osc_inspector.is_running():
            await self.osc_inspector.stop()

        logger.info("VRChat MCP server stopped")


# Create a default instance for convenience
mcp = VRChatMCP()

# Export commonly used types and classes
__all__ = [
    "VRChatMCP",
    "OSCInspector",
    "MessageDirection",
    "MessageRecord",
    "AvatarManager",
    "AvatarState",
    "ParameterValue",
    "InterpolationSystem",
    "EasingFunction",
    "DebugUI",
    "mcp",
]
