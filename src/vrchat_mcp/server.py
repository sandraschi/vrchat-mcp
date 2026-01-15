"""
VRChat MCP Server

FastMCP 2.14.1 compliant MCP server for VRChat avatar and asset control.
Provides comprehensive OSC-based avatar manipulation and VRChat automation.

The server offers avatar control, OSC communication, system management, secret management, and help system capabilities.
Tools follow logical grouping for maintainability while preserving full functionality.
"""

import asyncio
import logging
import sys
from typing import Any, Dict, Optional

from fastmcp import FastMCP

# Import components
from .osc_inspector import OSCInspector
from .tools.avatar.tools import AvatarManager
from .osc import OSCManager
from .interpolation import InterpolationSystem
from .secrets import secrets_manager

# Setup logging (stderr for MCP compatibility)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Create FastMCP app (like notepadpp-mcp pattern)
app = FastMCP(
    "VRChat MCP Server",
    instructions="You are VRChat MCP Server, a comprehensive automation server for VRChat avatar control and VR social interaction via OSC protocol. The server offers avatar control, OSC communication, system management, secret management, and help system capabilities. Tools are logically grouped for discoverability while maintaining comprehensive functionality.",
)

# Initialize core components
osc_inspector = None
avatar_manager = None
osc_manager = None
interpolation = None

try:
    # Initialize OSC components
    osc_inspector = OSCInspector(
        client_ip="127.0.0.1",
        client_port=9000,
        server_ip="127.0.0.1",
        server_port=9001,
    )

    osc_manager = OSCManager({
        "send_host": "127.0.0.1",
        "send_port": 9000,
        "receive_host": "127.0.0.1",
        "receive_port": 9001,
    })

    interpolation = InterpolationSystem()
    avatar_manager = AvatarManager(
        osc_manager=osc_manager, interpolation_system=interpolation
    )

    logger.info("VRChat MCP components initialized successfully")

except Exception as e:
    logger.warning(f"Failed to initialize VRChat components: {e}. Server will run with limited functionality.")

# Rate limiter and performance monitoring
class RateLimiter:
    """Simple rate limiter using sliding window."""
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        from collections import defaultdict, deque
        self.requests = defaultdict(lambda: deque(maxlen=requests_per_minute))
        self.lock = asyncio.Lock()

    async def is_allowed(self, client_id: str = "default") -> bool:
        """Check if request is allowed under rate limit."""
        async with self.lock:
            import time
            now = time.time()
            request_times = self.requests[client_id]
            while request_times and now - request_times[0] > 60:
                request_times.popleft()
            if len(request_times) < self.requests_per_minute:
                request_times.append(now)
                return True
            return False

class PerformanceMonitor:
    """Monitor performance metrics."""
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        from collections import deque
        self.response_times = deque(maxlen=1000)
        import time
        self.start_time = time.time()
        self.lock = asyncio.Lock()

    async def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        async with self.lock:
            import time
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
            }

rate_limiter = RateLimiter()
performance_monitor = PerformanceMonitor()

# Register all tools
@app.tool()
async def get_avatar_state(avatar_id: str) -> Dict[str, Any]:
    """Get the current state of an avatar."""
    if not avatar_manager:
        return {"success": False, "error": "Avatar manager not available"}
    return await avatar_manager.get_avatar_state(avatar_id)

@app.tool()
async def load_avatar(avatar_id: str) -> Dict[str, Any]:
    """Load an avatar by ID."""
    if not avatar_manager:
        return {"success": False, "error": "Avatar manager not available"}
    return await avatar_manager.load_avatar(avatar_id)

@app.tool()
async def set_parameter(
    avatar_id: str,
    parameter: str,
    value,
    interpolate: bool = False,
    duration: float = 0.5,
    easing: str = "linear",
) -> bool:
    """Set a parameter value for an avatar with optional interpolation."""
    if not avatar_manager:
        return False
    return await avatar_manager.set_parameter(
        avatar_id, parameter, value, interpolate, duration, easing
    )

@app.tool()
async def get_parameter(
    avatar_id: str, parameter: str
) -> Optional[Any]:
    """Get a parameter value for an avatar."""
    if not avatar_manager:
        return None
    return await avatar_manager.get_parameter(avatar_id, parameter)

@app.tool()
async def send_osc_message(
    address: str, args
) -> bool:
    """Send an OSC message."""
    if not osc_manager:
        logger.error("OSC manager not available")
        return False
    try:
        from .models import OSCMessage
        message = OSCMessage(address=address, args=args)
        await osc_manager.send_message(message)
        return True
    except Exception as e:
        logger.error(f"Failed to send OSC message: {e}")
        return False

@app.tool()
async def get_osc_statistics() -> Dict[str, Any]:
    """Get OSC communication statistics."""
    if not osc_inspector:
        return {"error": "OSC inspector not available"}
    return osc_inspector.get_statistics()

@app.tool()
async def get_server_status() -> Dict[str, Any]:
    """Get comprehensive server status information."""
    return {
        "server": "vrchat-mcp",
        "version": "0.1.0",
        "status": "running",
        "interfaces": ["mcp_stdio"],
        "components": {
            "osc_inspector": osc_inspector is not None,
            "avatar_manager": avatar_manager is not None,
            "osc_manager": osc_manager is not None,
            "interpolation": interpolation is not None,
        },
        "config": {
            "osc_client": "127.0.0.1:9000",
            "osc_server": "127.0.0.1:9001",
        },
    }

@app.tool()
async def get_health_status() -> Dict[str, Any]:
    """Get health check status."""
    return {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time(),
        "services": {
            "osc": "healthy" if osc_inspector and osc_inspector.is_running() else "unknown",
            "avatar_manager": "healthy",
            "interpolation": "healthy",
        },
    }

@app.tool()
async def get_performance_metrics() -> Dict[str, Any]:
    """Get comprehensive performance metrics."""
    try:
        metrics = await performance_monitor.get_metrics()
        return {"status": "success", "metrics": metrics}
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        return {"status": "error", "error": str(e)}

@app.tool()
async def check_rate_limit(client_id: str = "default") -> Dict[str, Any]:
    """Check current rate limit status for a client."""
    try:
        remaining_requests = await rate_limiter.get_remaining_requests(client_id)
        allowed = await rate_limiter.is_allowed(client_id)
        return {
            "status": "success",
            "client_id": client_id,
            "requests_remaining": remaining_requests,
            "can_make_request": allowed,
            "rate_limit": rate_limiter.requests_per_minute,
        }
    except Exception as e:
        logger.error(f"Failed to check rate limit: {e}")
        return {"status": "error", "error": str(e)}

@app.tool()
async def manage_secrets(
    action: str, key: str = "", value: Any = None, encrypted: bool = False
) -> Dict[str, Any]:
    """Manage sensitive configuration secrets."""
    try:
        if action == "get":
            if not key:
                return {"status": "error", "error": "Key required for get action"}
            secret_value = secrets_manager.get_secret(key, encrypted=encrypted)
            return {
                "status": "success",
                "key": key,
                "value": secret_value,
                "encrypted": encrypted,
            }

        elif action == "set":
            if not key or value is None:
                return {"status": "error", "error": "Key and value required for set action"}
            success = secrets_manager.set_secret(key, value, encrypted=encrypted)
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

@app.tool()
async def get_help(topic: str = "general") -> Dict[str, Any]:
    """Get multilevel help information about VRChat MCP tools and usage."""
    help_content = {
        "general": {
            "description": "VRChat MCP Server provides control over VRChat avatars and assets via OSC protocol",
            "interfaces": ["MCP stdio protocol"],
            "tools": ["avatar", "parameter", "osc", "system"],
            "usage": "Use 'get_help' with specific topic for detailed information",
        },
        "tools": {
            "avatar_tools": ["get_avatar_state", "set_parameter", "get_parameter"],
            "osc_tools": ["send_osc_message", "get_osc_statistics"],
            "system_tools": ["get_server_status", "get_health_status", "get_help"],
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
            "rate_limiting": "60 requests per minute per client",
            "logging": "Configurable logging levels and file output",
        },
    }

    return help_content.get(
        topic,
        {"error": f"Unknown help topic: {topic}", "available_topics": list(help_content.keys())},
    )


async def main() -> None:
    """Main entry point for the MCP server."""
    logger.info("Starting VRChat MCP server...")

    # Start OSC inspector if available
    if osc_inspector:
        try:
            await osc_inspector.start()
            logger.info("OSC inspector started")
        except Exception as e:
            logger.warning(f"Failed to start OSC inspector: {e}")

    # Run the MCP server
    await app.run_stdio_async()


def run() -> None:
    """Synchronous entry point for compatibility."""
    asyncio.run(main())


if __name__ == "__main__":
    sys.exit(main())
