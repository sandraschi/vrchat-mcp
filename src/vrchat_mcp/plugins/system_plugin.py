"""
System Plugin for VRChat MCP.

Provides system-level utilities and management functions.
"""

import asyncio
import logging
import platform
import time
from typing import Any

import psutil

from ..plugins import Plugin, tool

logger = logging.getLogger(__name__)


class SystemPlugin(Plugin):
    """Plugin for system utilities and management."""

    def __init__(self):
        self.start_time = time.time()
        self.metrics = {"cpu_usage": [], "memory_usage": [], "network_io": {"sent": [], "recv": []}}
        self.max_metrics = 1000
        self._monitor_task = None
        self._background_tasks: set[asyncio.Task] = set()

    @property
    def name(self) -> str:
        return "system"

    @property
    def description(self) -> str:
        return "Provides system utilities and monitoring"

    async def on_load(self, mcp):
        """Initialize the plugin with the MCP instance."""
        self.mcp = mcp
        logger.info("System plugin loaded")

        # Start system monitoring
        self._monitor_task = asyncio.create_task(self._monitor_system())
        self._background_tasks.add(self._monitor_task)
        self._monitor_task.add_done_callback(self._background_tasks.discard)

    async def on_unload(self):
        """Clean up resources."""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

    async def _monitor_system(self):
        """Background task to monitor system metrics."""
        net_io = psutil.net_io_counters()
        last_sent = net_io.bytes_sent
        last_recv = net_io.bytes_recv

        while True:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.metrics["cpu_usage"].append((time.time(), cpu_percent))

                # Memory usage
                mem = psutil.virtual_memory()
                self.metrics["memory_usage"].append((time.time(), mem.percent))

                # Network I/O
                net_io = psutil.net_io_counters()
                sent = net_io.bytes_sent - last_sent
                recv = net_io.bytes_recv - last_recv
                last_sent = net_io.bytes_sent
                last_recv = net_io.bytes_recv

                self.metrics["network_io"]["sent"].append((time.time(), sent))
                self.metrics["network_io"]["recv"].append((time.time(), recv))

                # Trim old metrics
                for key in ["cpu_usage", "memory_usage"]:
                    if len(self.metrics[key]) > self.max_metrics:
                        self.metrics[key] = self.metrics[key][-self.max_metrics :]

                for key in ["sent", "recv"]:
                    if len(self.metrics["network_io"][key]) > self.max_metrics:
                        self.metrics["network_io"][key] = self.metrics["network_io"][key][-self.max_metrics :]

                await asyncio.sleep(5)  # Update every 5 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in system monitor: {e}")
                await asyncio.sleep(10)  # Wait a bit longer on error

    @tool(
        name="system_info",
        description="Get system information",
        category="System",
        returns={
            "platform": "string",
            "python_version": "string",
            "cpu_count": "number",
            "total_memory": "string",
            "uptime": "number",
            "process": {"pid": "number", "memory_usage": "string", "threads": "number"},
        },
        examples=[{"description": "Get system info", "code": "system_info()"}],
    )
    async def get_system_info(self) -> dict[str, Any]:
        """Get system information."""
        process = psutil.Process()
        mem_info = process.memory_info()

        return {
            "platform": f"{platform.system()} {platform.release()} {platform.machine()}",
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "total_memory": f"{psutil.virtual_memory().total / (1024**3):.2f} GB",
            "uptime": time.time() - self.start_time,
            "process": {
                "pid": process.pid,
                "memory_usage": f"{mem_info.rss / (1024**2):.2f} MB",
                "threads": process.num_threads(),
            },
        }

    @tool(
        name="system_metrics",
        description="Get system metrics history",
        category="System",
        args={
            "metric": {
                "type": "string",
                "description": "Metric to retrieve (cpu_usage, memory_usage, network_io)",
                "default": "cpu_usage",
            },
            "limit": {"type": "number", "description": "Maximum number of data points to return", "default": 100},
        },
        returns={"metric": "string", "data": "list[tuple[number, number]]"},
        examples=[
            {"description": "Get CPU usage history", "code": "system_metrics('cpu_usage')"},
            {"description": "Get last 10 memory readings", "code": "system_metrics('memory_usage', 10)"},
        ],
    )
    async def get_system_metrics(self, metric: str = "cpu_usage", limit: int = 100) -> dict[str, Any]:
        """Get system metrics history."""
        if metric == "network_io":
            data = {
                "sent": self.metrics["network_io"]["sent"][-limit:],
                "recv": self.metrics["network_io"]["recv"][-limit:],
            }
        elif metric in self.metrics:
            data = self.metrics[metric][-limit:]
        else:
            return {"error": f"Unknown metric: {metric}"}

        return {"metric": metric, "data": data}

    @tool(
        name="shutdown",
        description="Shutdown the MCP server",
        category="System",
        args={
            "restart": {"type": "boolean", "description": "Whether to restart after shutdown", "default": False},
            "delay": {"type": "number", "description": "Seconds to wait before shutting down", "default": 0},
        },
        returns={"success": "boolean", "message": "string"},
        examples=[
            {"description": "Graceful shutdown", "code": "shutdown()"},
            {"description": "Restart after delay", "code": "shutdown(restart=True, delay=5)"},
        ],
    )
    async def shutdown_server(self, restart: bool = False, delay: int = 0) -> dict[str, Any]:
        """Shutdown the MCP server."""
        if delay > 0:
            action = "restarting" if restart else "shutting down"
            logger.info(f"{action.capitalize()} server in {delay} seconds...")
            await asyncio.sleep(delay)

        if restart:
            logger.info("Restarting server...")
            # In a real implementation, we would restart the server
            return {"success": True, "message": "Server restart requested"}
        else:
            logger.info("Shutting down server...")
            # Signal the main loop to exit
            if hasattr(self.mcp, "stop"):
                task = asyncio.create_task(self.mcp.stop())
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
            return {"success": True, "message": "Server shutdown requested"}

    @tool(
        name="list_plugins",
        description="List all loaded plugins",
        category="System",
        args={"include_tools": {"type": "boolean", "description": "Whether to include tool details", "default": False}},
        returns={"plugins": "list[dict]"},
        examples=[
            {"description": "List plugins", "code": "list_plugins()"},
            {"description": "List with tool details", "code": "list_plugins(include_tools=True)"},
        ],
    )
    async def list_plugins(self, include_tools: bool = False) -> dict[str, Any]:
        """List all loaded plugins."""
        if not hasattr(self.mcp, "plugin_manager"):
            return {"error": "Plugin manager not available"}

        plugins = []
        for name, plugin in self.mcp.plugin_manager.plugins.items():
            plugin_info = {
                "name": name,
                "version": getattr(plugin, "version", "1.0.0"),
                "description": getattr(plugin, "description", ""),
            }

            if include_tools:
                tools = []
                for attr_name in dir(plugin):
                    attr = getattr(plugin, attr_name)
                    if hasattr(attr, "_tool_metadata"):
                        tools.append(attr._tool_metadata)
                plugin_info["tools"] = tools

            plugins.append(plugin_info)

        return {"plugins": plugins}


# This allows the plugin to be auto-discovered
PLUGIN_CLASS = SystemPlugin
