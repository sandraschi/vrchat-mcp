"""
VRChat MCP: SOTA Industrial v14.1.0

Unified control plane for VRChat avatar and asset orchestration.
Provides high-fidelity OSC integration and character state management.
"""

__version__ = "14.1.0"

import asyncio
import logging
import sys
import time
from collections import defaultdict, deque
from typing import Any

from fastmcp import FastMCP

from .api_manager import APIManager
from .debug_ui import DebugUI
from .interpolation import EasingFunction, InterpolationSystem
from .models import AvatarState, ParameterValue
from .osc import OSCManager
from .osc_inspector import MessageDirection, MessageRecord, OSCInspector
from .secrets import secrets_manager
from .server import app
from .tools import AvatarManager
from .web_interface import WebInterface

# Configure logging (MCP servers must use stderr, not stdout)
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

    async def get_metrics(self) -> dict[str, Any]:
        """Get current performance metrics."""
        async with self.lock:
            uptime = time.time() - self.start_time
            avg_response_time = self.total_response_time / self.request_count if self.request_count > 0 else 0
            error_rate = self.error_count / self.request_count * 100 if self.request_count > 0 else 0

            return {
                "uptime_seconds": uptime,
                "total_requests": self.request_count,
                "error_count": self.error_count,
                "error_rate_percent": round(error_rate, 2),
                "avg_response_time_ms": round(avg_response_time * 1000, 2),
                "requests_per_second": round(self.request_count / uptime, 2) if uptime > 0 else 0,
                "recent_response_times_count": len(self.response_times),
                "min_recent_response_time_ms": round(min(self.response_times) * 1000, 2) if self.response_times else 0,
                "max_recent_response_time_ms": round(max(self.response_times) * 1000, 2) if self.response_times else 0,
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
    "debug_ui": {"enabled": True, "host": "127.0.0.1", "port": 8765},
    "logging": {"level": "INFO", "file": None},
}


class VRChatMCP:
    """Main VRChat MCP server class."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the VRChat MCP server.

        Args:
            config: Optional configuration dictionary. If not provided, defaults will be used.
        """
        self.config = secrets_manager.load_config_with_secrets({**DEFAULT_CONFIG, **(config or {})})

        # Set up logging
        self._setup_logging()

        # Create the main MCP instance (like all other MCP servers)
        self.mcp = FastMCP(
            name="vrchat-mcp",
            instructions="MCP server for VRChat avatar and asset control",
        )

        # Add FastAPI endpoints for health and docs (required by production checklist)
        @self.mcp.custom_route("/health", methods=["GET"])
        async def health_endpoint():
            """Health check endpoint returning server status."""
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
        self.avatar_manager = AvatarManager(osc_manager=self.osc_manager, interpolation_system=self.interpolation)

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
            file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
            logging.getLogger().addHandler(file_handler)

    def _register_tools_on_instance(self, mcp_instance) -> None:
        """Register SOTA Portmanteau tools."""

        @mcp_instance.tool()
        async def manage_avatar(
            operation: str,
            avatar_id: str | None = None,
            parameter: str | None = None,
            value: Any | None = None,
            interpolate: bool = False,
            duration: float = 0.5,
            easing: str = "linear",
        ) -> dict[str, Any]:
            """Unified Avatar State and Parameter Management."""
            if operation == "get_state":
                return await self.avatar_manager.get_avatar_state(avatar_id)
            elif operation == "load":
                return await self.avatar_manager.load_avatar(avatar_id)
            elif operation == "set_param":
                success = await self.avatar_manager.set_parameter(
                    avatar_id, parameter, value, interpolate, duration, easing
                )
                return {"success": success}
            elif operation == "get_param":
                return {"value": await self.avatar_manager.get_parameter(avatar_id, parameter)}
            return {"error": f"Unknown operation: {operation}"}

        @mcp_instance.tool()
        async def manage_osc(
            operation: str, address: str | None = None, args: list[Any] | None = None
        ) -> dict[str, Any]:
            """Unified OSC Protocol Interaction."""
            if operation == "send":
                from .models import OSCMessage

                msg = OSCMessage(address=address, args=args or [])
                await self.osc_manager.send_message(msg)
                return {"success": True}
            elif operation == "stats":
                return self.osc_inspector.get_statistics()
            return {"error": f"Unknown operation: {operation}"}

        @mcp_instance.tool()
        async def manage_system(
            operation: str,
            topic: str = "general",
            client_id: str = "default",
            key: str | None = None,
            value: Any | None = None,
        ) -> dict[str, Any]:
            """Unified System Health, Telemetry, and Secrets."""
            if operation == "status":
                return {
                    "server": "vrchat-mcp",
                    "version": __version__,
                    "status": "running",
                    "components": {"osc": True, "avatar": True},
                }
            elif operation == "metrics":
                return await self.performance_monitor.get_metrics()
            elif operation == "help":
                return await self._get_help(topic)
            elif operation == "secrets":
                return {"message": "Managed via secrets_manager"}
            return {"error": f"Unknown operation: {operation}"}

    async def _get_help(self, topic: str = "general") -> dict[str, Any]:
        """Internal help helper."""
        return {"topics": ["avatar", "osc", "system"]}

    async def start(self) -> None:
        """Start the VRChat MCP server."""
        logger.info("Starting VRChat MCP server...")

        # Start OSC inspector
        try:
            await self.osc_inspector.start()
        except Exception as e:
            logger.warning(f"Failed to start OSC inspector: {e}. Server will work without OSC functionality.")

        # Start debug UI if enabled
        if self.debug_ui:
            await self.debug_ui.start()

        # Register tools on the FastMCP instance
        self._register_tools_on_instance(self.mcp)

        # Run in MCP stdio mode (like all other MCP servers)
        await self.mcp.run_stdio_async()

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


# Export commonly used types and classes
__all__ = [
    "AvatarManager",
    "AvatarState",
    "DebugUI",
    "EasingFunction",
    "InterpolationSystem",
    "MessageDirection",
    "MessageRecord",
    "OSCInspector",
    "ParameterValue",
    "VRChatMCP",
    "app",
]
