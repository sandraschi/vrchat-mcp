"""
Monitoring Plugin for VRChat MCP.

Provides error recovery, monitoring, and connection health features.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from enum import Enum, auto
from typing import Any

from ..plugins import Plugin, tool

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state enumeration."""

    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    RECONNECTING = auto()
    ERROR = auto()


class ConnectionStatus:
    """Status of a monitored connection."""

    def __init__(self, name: str):
        self.name = name
        self.state = ConnectionState.DISCONNECTED
        self.last_error: str | None = None
        self.last_connected: float | None = None
        self.last_disconnected: float | None = None
        self.reconnect_attempts: int = 0
        self.total_errors: int = 0
        self.total_reconnects: int = 0
        self._state_handlers: dict[ConnectionState, Callable[[], Awaitable[bool]]] = {}

    def set_state_handler(self, state: ConnectionState, handler: Callable[[], Awaitable[bool]]) -> None:
        """Set a handler for state changes."""
        self._state_handlers[state] = handler

    async def handle_state(self, state: ConnectionState, error: str | None = None) -> bool:
        """Handle a state change."""
        old_state = self.state
        if old_state == state and not error:
            return True

        self.state = state
        now = time.time()

        # Update state-specific attributes
        if state == ConnectionState.CONNECTED:
            self.last_connected = now
            self.reconnect_attempts = 0
            if old_state == ConnectionState.RECONNECTING:
                self.total_reconnects += 1
        elif state in (ConnectionState.DISCONNECTED, ConnectionState.ERROR):
            self.last_disconnected = now
            if error:
                self.last_error = error
                self.total_errors += 1

        logger.info(
            f"Connection '{self.name}' state changed: {old_state.name} -> {state.name}"
            + (f" (Error: {error})" if error else "")
        )

        # Call state handler if registered
        if state in self._state_handlers:
            return await self._state_handlers[state]()
        return True


class MonitoringPlugin(Plugin):
    """Plugin for monitoring and error recovery."""

    def __init__(self):
        self.connections: dict[str, ConnectionStatus] = {}
        self.auto_reconnect = True
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5.0  # seconds
        self._background_tasks: set[asyncio.Task] = set()

    @property
    def name(self) -> str:
        return "monitoring"

    @property
    def description(self) -> str:
        return "Provides error recovery and connection monitoring"

    async def on_load(self, mcp):
        """Initialize the plugin with the MCP instance."""
        self.mcp = mcp
        logger.info("Monitoring plugin loaded")

    async def on_unload(self):
        """Cleanup plugin tasks."""
        for task in self._background_tasks:
            task.cancel()
        logger.info("Monitoring plugin unloaded")

    def register_connection(self, name: str) -> ConnectionStatus:
        """Register a new connection to monitor."""
        if name not in self.connections:
            self.connections[name] = ConnectionStatus(name)
        return self.connections[name]

    async def update_connection_state(self, name: str, state: ConnectionState, error: str | None = None) -> bool:
        """Update the state of a monitored connection."""
        if name not in self.connections:
            self.register_connection(name)

        status = self.connections[name]
        success = await status.handle_state(state, error)

        # Handle reconnection if needed
        if (
            self.auto_reconnect
            and state == ConnectionState.DISCONNECTED
            and status.reconnect_attempts < self.max_reconnect_attempts
        ):
            # Guard against garbage collection (RUF006)
            task = asyncio.create_task(self._handle_reconnection(name))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        return success

    async def _handle_reconnection(self, name: str) -> None:
        """Handle automatic reconnection for a connection."""
        if name not in self.connections:
            return

        status = self.connections[name]

        # Skip if already reconnecting or connected
        if status.state in (ConnectionState.CONNECTING, ConnectionState.RECONNECTING, ConnectionState.CONNECTED):
            return

        # Don't exceed max attempts
        if status.reconnect_attempts >= self.max_reconnect_attempts:
            logger.warning(f"Max reconnection attempts ({self.max_reconnect_attempts}) reached for {name}")
            return

        # Calculate delay with exponential backoff
        delay = min(self.reconnect_delay * (2**status.reconnect_attempts), 300)  # Cap at 5 minutes
        status.reconnect_attempts += 1

        logger.info(
            f"Attempting to reconnect {name} (attempt "
            f"{status.reconnect_attempts}/{self.max_reconnect_attempts}) in {delay:.1f}s..."
        )

        await asyncio.sleep(delay)

        # Check if we should still try to reconnect
        if name not in self.connections:
            return

        status = self.connections[name]
        if status.state == ConnectionState.CONNECTED:
            return  # Already reconnected by another process

        try:
            # Update state to reconnecting
            await self.update_connection_state(
                name, ConnectionState.RECONNECTING, f"Reconnection attempt {status.reconnect_attempts}"
            )

            # Try to reconnect using the state handler
            success = await status.handle_state(ConnectionState.CONNECTING)

            if success:
                logger.info(f"Successfully reconnected {name}")
                await self.update_connection_state(name, ConnectionState.CONNECTED)
            else:
                logger.warning(f"Failed to reconnect {name}")
                await self.update_connection_state(
                    name, ConnectionState.DISCONNECTED, f"Reconnection attempt {status.reconnect_attempts} failed"
                )

        except Exception as e:
            logger.error(f"Error during reconnection of {name}: {e}", exc_info=True)
            await self.update_connection_state(name, ConnectionState.ERROR, f"Reconnection error: {e!s}")

    @tool(
        name="get_connection_status",
        description="Get the status of monitored connections",
        category="Monitoring",
        args={"name": {"type": "string", "description": "Name of the connection (omit for all)", "default": None}},
        returns={"connections": "list[dict]"},
        examples=[
            {"description": "Get all connection statuses", "code": "get_connection_status()"},
            {"description": "Get specific connection status", "code": "get_connection_status('osc_server')"},
        ],
    )
    async def get_connection_status(self, name: str | None = None) -> dict[str, Any]:
        """Get the status of monitored connections."""
        if name:
            if name not in self.connections:
                return {"error": f"No such connection: {name}"}
            return {"connections": [self._connection_to_dict(self.connections[name])]}

        return {"connections": [self._connection_to_dict(conn) for conn in self.connections.values()]}

    def _connection_to_dict(self, conn: ConnectionStatus) -> dict[str, Any]:
        """Convert a ConnectionStatus to a dictionary."""
        now = time.time()
        uptime = None
        if conn.last_connected:
            if conn.state == ConnectionState.CONNECTED:
                uptime = now - conn.last_connected
            elif conn.last_disconnected:
                uptime = conn.last_disconnected - conn.last_connected

        return {
            "name": conn.name,
            "state": conn.state.name,
            "last_error": conn.last_error,
            "last_connected": conn.last_connected,
            "uptime": uptime,
            "reconnect_attempts": conn.reconnect_attempts,
            "total_errors": conn.total_errors,
            "total_reconnects": conn.total_reconnects,
            "next_reconnect_attempt": (
                conn.last_disconnected + min(self.reconnect_delay * (2**conn.reconnect_attempts), 300)
                if conn.state == ConnectionState.DISCONNECTED and conn.reconnect_attempts < self.max_reconnect_attempts
                else None
            ),
        }

    @tool(
        name="set_auto_reconnect",
        description="Enable or disable automatic reconnection",
        category="Monitoring",
        args={"enabled": {"type": "boolean", "description": "Whether to enable auto-reconnect"}},
        returns={"success": "boolean", "auto_reconnect": "boolean"},
        examples=[
            {"description": "Enable auto-reconnect", "code": "set_auto_reconnect(True)"},
            {"description": "Disable auto-reconnect", "code": "set_auto_reconnect(False)"},
        ],
    )
    async def set_auto_reconnect(self, enabled: bool) -> dict[str, Any]:
        """Enable or disable automatic reconnection."""
        self.auto_reconnect = enabled
        logger.info(f"Auto-reconnect {'enabled' if enabled else 'disabled'}")
        return {"success": True, "auto_reconnect": self.auto_reconnect}


# This allows the plugin to be auto-discovered
PLUGIN_CLASS = MonitoringPlugin
