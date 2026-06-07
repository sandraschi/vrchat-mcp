"""
VRChat MCP Server: SOTA Industrial v14.1.0

Industrialized FastMCP 3.2.0 compliant control plane for VRChat.
Provides unified Portmanteau tools for avatar, OSC, and system orchestration.

PORTMANTEAU PATTERN RATIONALE:
Consolidates fine-grained operations into high-utility entry points.
Reduces cognitive load for agentic orchestrators and ensures SOTA compliance.
"""

import asyncio
import logging
import os
import sys
import time
from collections import deque
from typing import Any

from fastmcp import FastMCP

from .api_client import VRChatAPIClient
from .interpolation import InterpolationSystem
from .osc import OSCManager
from .osc_inspector import OSCInspector
from .pipeline_client import PipelineClient
from .secrets import secrets_manager
from .tools.avatar.tools import AvatarManager

# Import components
from .transport import run_server_async

# Override default fleet port for VRChat MCP (10795)
os.environ.setdefault("MCP_PORT", "10795")

# Setup logging (stderr for MCP compatibility)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

# Create FastMCP app
app = FastMCP(
    "VRChat MCP Server",
    version="14.1.0",
    instructions="You are VRChat MCP Server v14.1.0, an industrialized control plane for VR interaction. "
    "Use manage_avatar for character states, manage_osc for protocol traffic, and manage_system for telemetry.",
)


# --- Internal State ---
class Telemetry:
    """Industrial performance monitoring."""

    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        self.history = deque(maxlen=1000)
        self.lock = asyncio.Lock()

    async def record(self, response_time: float, success: bool):
        async with self.lock:
            self.request_count += 1
            if not success:
                self.error_count += 1
            self.total_response_time += response_time
            self.history.append(response_time)

    async def get_metrics(self) -> dict[str, Any]:
        async with self.lock:
            uptime = time.time() - self.start_time
            avg_rt = self.total_response_time / self.request_count if self.request_count > 0 else 0
            return {
                "uptime_seconds": round(uptime, 2),
                "total_requests": self.request_count,
                "error_rate": round((self.error_count / self.request_count * 100) if self.request_count else 0, 2),
                "avg_response_ms": round(avg_rt * 1000, 2),
                "throughput_rps": round(self.request_count / uptime if uptime > 0 else 0, 2),
            }


telemetry = Telemetry()

# --- Component Initialization ---
osc_inspector = None
avatar_manager = None
osc_manager = None
interpolation = None

try:
    osc_inspector = OSCInspector(client_ip="127.0.0.1", client_port=9000, server_ip="127.0.0.1", server_port=9001)
    osc_manager = OSCManager(
        {"send_host": "127.0.0.1", "send_port": 9000, "receive_host": "127.0.0.1", "receive_port": 9001}
    )
    interpolation = InterpolationSystem()
    avatar_manager = AvatarManager(osc_manager=osc_manager, interpolation_system=interpolation)

    # API Components (Lazy Init via secrets)
    vrchat_api = None
    pipeline = None

    logger.info("VRChat SOTA Components initialized successfully (Port: 10795)")
except Exception as e:
    logger.error(f"Failed to initialize SOTA core: {e}")

# --- Unified Portmanteau Tools ---


@app.tool()
async def manage_avatar(
    operation: str,
    avatar_id: str | None = None,
    parameter: str | None = None,
    value: Any | None = None,
    interpolate: bool = False,
    duration: float = 0.5,
    easing: str = "linear",
) -> dict[str, Any]:
    """
    Unified Portmanteau for Avatar State and Parameter Management.

    Operations:
    - get_state: Retrieve full state (OSC + REST metadata).
    - load: Trigger avatar load by ID.
    - set_param: Set parameter value (supports interpolation).
    - get_param: Retrieve specific parameter value.
    """
    start_time = time.time()
    success = False
    result = {"operation": operation}

    try:
        if not avatar_manager:
            raise RuntimeError("Avatar manager not initialized")

        if operation == "get_state":
            result["data"] = await avatar_manager.get_avatar_state(avatar_id)
            if vrchat_api and avatar_id:
                # Enrich with REST metadata if available
                try:
                    # In VRChat API, we search for avatar detail
                    # result["metadata"] = vrchat_api.avatars_api.get_avatar(avatar_id).to_dict()
                    pass
                except Exception:
                    # Metadata enrichment is optional and may fail periodically
                    ...
        elif operation == "load":
            result["data"] = await avatar_manager.load_avatar(avatar_id)
        elif operation == "set_param":
            result["success"] = await avatar_manager.set_parameter(
                avatar_id, parameter, value, interpolate, duration, easing
            )
        elif operation == "get_param":
            result["value"] = await avatar_manager.get_parameter(avatar_id, parameter)
        else:
            result["error"] = f"Unknown operation: {operation}"
            return result

        success = True
        return result
    except Exception as e:
        result["error"] = str(e)
        return result
    finally:
        await telemetry.record(time.time() - start_time, success)


@app.tool()
async def manage_osc(operation: str, address: str | None = None, args: list[Any] | None = None) -> dict[str, Any]:
    """
    Unified Portmanteau for OSC Protocol Interaction.

    Operations:
    - send: Dispatch OSC message to specific address with args.
    - stats: Retrieve real-time protocol traffic statistics.
    """
    start_time = time.time()
    success = False
    result = {"operation": operation}

    try:
        if operation == "send":
            if not osc_manager:
                raise RuntimeError("OSC manager unavailable")
            from .models import OSCMessage

            msg = OSCMessage(address=address, args=args or [])
            await osc_manager.send_message(msg)
            result["success"] = True
        elif operation == "stats":
            if not osc_inspector:
                raise RuntimeError("OSC inspector unavailable")
            result["data"] = osc_inspector.get_statistics()
        else:
            result["error"] = f"Unknown operation: {operation}"
            return result

        success = True
        return result
    except Exception as e:
        result["error"] = str(e)
        return result
    finally:
        await telemetry.record(time.time() - start_time, success)


@app.tool()
async def manage_world(operation: str, world_id: str | None = None, query: str | None = None) -> dict[str, Any]:
    """
    Unified Portmanteau for World Discovery and Instance Telemetry (REST API REQUIRED).

    Operations:
    - get_info: Fetch metadata for a world ID.
    - search: Search for active worlds by query string.
    """
    start_time = time.time()
    success = False
    result = {"operation": operation}

    try:
        if not vrchat_api:
            raise RuntimeError("REST API Client not initialized. Set secrets first.")

        if operation == "get_info":
            result["data"] = await vrchat_api.get_world_info(world_id)
        elif operation == "search":
            # result["data"] = vrchat_api.worlds_api.search_worlds(search=query).to_dict()
            result["data"] = {"query": query, "results": []}  # Placeholder
        else:
            result["error"] = f"Unknown operation: {operation}"
            return result

        success = True
        return result
    except Exception as e:
        result["error"] = str(e)
        return result
    finally:
        await telemetry.record(time.time() - start_time, success)


@app.tool()
async def manage_economy(operation: str) -> dict[str, Any]:
    """
    Unified Portmanteau for VRChat Creator Economy (REST API REQUIRED).

    Operations:
    - balance: Retrieve current VRChat Credit balance.
    - products: List active Udon products and subscriptions.
    """
    start_time = time.time()
    success = False
    result = {"operation": operation}

    try:
        if not vrchat_api:
            raise RuntimeError("REST API Client not initialized. Set secrets first.")

        if operation == "balance":
            result["data"] = await vrchat_api.get_economy_info()
        elif operation == "products":
            result["data"] = {"products": [], "subscriptions": []}  # Placeholder
        else:
            result["error"] = f"Unknown operation: {operation}"
            return result

        success = True
        return result
    except Exception as e:
        result["error"] = str(e)
        return result
    finally:
        await telemetry.record(time.time() - start_time, success)


@app.tool()
async def manage_input(
    operation: str,
    value: Any | None = None,
    x: float = 0.0,
    y: float = 0.0,
    immediate: bool = True
) -> dict[str, Any]:
    """
    Unified Portmanteau for VRChat Input Simulation (OSC only).

    Operations:
    - chatbox: Send text message (max 144 chars).
    - jump: Trigger jump action.
    - move: Set vertical/horizontal movement (-1.0 to 1.0).
    - look: Set vertical/horizontal looking (-1.0 to 1.0).
    """
    start_time = time.time()
    success = False
    result = {"operation": operation}

    try:
        if not osc_manager:
            raise RuntimeError("OSC manager unavailable")
        from .models import OSCMessage

        if operation == "chatbox":
            msg = OSCMessage(address="/chatbox/input", args=[str(value), immediate])
            await osc_manager.send_message(msg)
        elif operation == "jump":
            await osc_manager.send_message(OSCMessage(address="/input/Jump", args=[1]))
            await asyncio.sleep(0.1)
            await osc_manager.send_message(OSCMessage(address="/input/Jump", args=[0]))
        elif operation == "move":
            await osc_manager.send_message(OSCMessage(address="/input/Vertical", args=[float(y)]))
            await osc_manager.send_message(OSCMessage(address="/input/Horizontal", args=[float(x)]))
        elif operation == "look":
            await osc_manager.send_message(OSCMessage(address="/input/LookVertical", args=[float(y)]))
            await osc_manager.send_message(OSCMessage(address="/input/LookHorizontal", args=[float(x)]))
        else:
            result["error"] = f"Unknown operation: {operation}"
            return result

        success = True
        result["success"] = True
        return result
    except Exception as e:
        result["error"] = str(e)
        return result
    finally:
        await telemetry.record(time.time() - start_time, success)


@app.tool()
async def manage_system(
    operation: str, topic: str = "general", client_id: str = "default", key: str | None = None, value: Any | None = None
) -> dict[str, Any]:
    """
    Unified Portmanteau for System Health, Telemetry, and Auth.

    Operations:
    - status: Full server availability and component check.
    - metrics: Performance telemetry (RPS, error rate, latency).
    - auth_2fa: Verify login with 2FA code.
    - secrets: Manage encrypted configuration (get/set/list).
    """
    start_time = time.time()
    success = False
    result = {"operation": operation}
    global vrchat_api, pipeline

    try:
        if operation == "status":
            result["data"] = {
                "server": "vrchat-mcp",
                "version": "14.1.0",
                "status": "running",
                "components": {
                    "osc": osc_manager is not None,
                    "avatar": avatar_manager is not None,
                    "inspector": osc_inspector is not None,
                    "rest_api": vrchat_api is not None,
                    "pipeline": pipeline is not None,
                },
            }
        elif operation == "metrics":
            result["data"] = await telemetry.get_metrics()
        elif operation == "auth_2fa":
            if not vrchat_api:
                raise RuntimeError("API Client not initialized. Please set secrets first.")
            result["success"] = await vrchat_api.verify_2fa(value)
            if result["success"]:
                # Start Pipeline after 2FA success
                auth_token = vrchat_api.api_client.configuration.api_key.get("auth")
                pipeline = PipelineClient()
                await pipeline.connect(auth_token)
        elif operation == "secrets":
            if key and value:
                result["success"] = secrets_manager.set_secret(key, value)
                # Auto-init API if credentials provided
                if key in ["VRCHAT_USERNAME", "VRCHAT_PASSWORD"]:
                    user = secrets_manager.get_secret("VRCHAT_USERNAME")
                    pw = secrets_manager.get_secret("VRCHAT_PASSWORD")
                    if user and pw:
                        vrchat_api = VRChatAPIClient(user, pw)
                        result["auth_status"] = await vrchat_api.login()
            elif key:
                result["value"] = secrets_manager.get_secret(key)
            else:
                result["list"] = secrets_manager.get_available_secrets()
        else:
            result["error"] = f"Unknown operation: {operation}"
            return result

        success = True
        return result
    except Exception as e:
        result["error"] = str(e)
        return result
    finally:
        await telemetry.record(time.time() - start_time, success)


# --- Lifecycle Management ---

# Expose HTTP app for uvicorn
_mcp_app = app
app = _mcp_app.http_app()


async def main():
    """Industrial Entry Point."""
    logger.info("Initializing VRChat MCP Control Plane (SOTA v14.1.0)...")
    if osc_inspector:
        await osc_inspector.start()

    await run_server_async(_mcp_app, server_name="vrchat-mcp")


if __name__ == "__main__":
    asyncio.run(main())
