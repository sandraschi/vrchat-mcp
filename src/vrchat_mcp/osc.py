"""
OSC (Open Sound Control) client and server implementation for VRChat MCP.

This module provides an asynchronous wrapper around python-osc for communicating
with VRChat using the OSC protocol.
"""

import asyncio
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

logger = logging.getLogger(__name__)

# Type aliases
OSCHandler = Callable[[str, list[Any]], None]
OSCAddress = str
OSCValue = bool | float | int | str | bytes | None


class ConnectionState(Enum):
    """Represents the connection state of the OSC manager."""

    DISCONNECTED = auto()  # Not connected and not trying to connect
    CONNECTING = auto()  # Attempting to establish initial connection
    CONNECTED = auto()  # Successfully connected and active
    RECONNECTING = auto()  # Attempting to reconnect after disconnection
    DISCONNECTING = auto()  # Gracefully shutting down
    ERROR = auto()  # Error state, manual intervention may be required


@dataclass
class ConnectionStats:
    """Tracks connection statistics."""

    connection_attempts: int = 0  # Total connection attempts
    successful_connections: int = 0  # Number of successful connections
    disconnections: int = 0  # Number of disconnections
    reconnection_attempts: int = 0  # Total reconnection attempts
    last_connected: float | None = None  # Timestamp of last successful connection
    last_disconnected: float | None = None  # Timestamp of last disconnection
    last_error: str | None = None  # Last error message
    error_count: int = 0  # Total number of errors
    messages_sent: int = 0  # Total messages sent
    messages_received: int = 0  # Total messages received
    avg_reconnect_time: float = 0.0  # Average reconnection time in seconds
    total_uptime: float = 0.0  # Total connection uptime in seconds
    last_heartbeat: float | None = None  # Timestamp of last successful heartbeat


class OSCManager:
    """Manages OSC communication with VRChat."""

    def __init__(
        self,
        listen_ip: str = "127.0.0.1",
        listen_port: int = 9001,
        send_ip: str = "127.0.0.1",
        send_port: int = 9000,
        auto_reconnect: bool = True,
        max_reconnect_attempts: int = 10,
        initial_reconnect_delay: float = 1.0,
        max_reconnect_delay: float = 30.0,
        connection_timeout: float = 5.0,
        heartbeat_interval: float = 5.0,
        heartbeat_timeout: float = 10.0,
        jitter_factor: float = 0.1,
    ):
        """Initialize the OSC manager.

        Args:
            listen_ip: IP address to listen for OSC messages on
            listen_port: Port to listen for OSC messages on
            send_ip: IP address to send OSC messages to
            send_port: Port to send OSC messages to
            auto_reconnect: Whether to automatically reconnect on disconnection
            max_reconnect_attempts: Maximum number of reconnection attempts (0 for unlimited)
            initial_reconnect_delay: Initial delay between reconnection attempts in seconds
            max_reconnect_delay: Maximum delay between reconnection attempts in seconds
            connection_timeout: Timeout for connection attempts in seconds
        """
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.send_ip = send_ip
        self.send_port = send_port

        # Connection settings
        self.auto_reconnect = auto_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts
        self.initial_reconnect_delay = initial_reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self.connection_timeout = connection_timeout
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.jitter_factor = jitter_factor

        # OSC client for sending messages
        self._client: SimpleUDPClient | None = None

        # OSC server for receiving messages
        self._dispatcher = Dispatcher()
        self._server: AsyncIOOSCUDPServer | None = None
        self._server_task: asyncio.Task | None = None
        self._reconnect_task: asyncio.Task | None = None
        self._background_tasks: set[asyncio.Task] = set()

        # Connection state tracking
        self._state = ConnectionState.DISCONNECTED
        self._state_lock = asyncio.Lock()
        self._connection_handlers: list[Callable[[ConnectionState, ConnectionState | None], None]] = []
        self._connection_stats = ConnectionStats()
        self._reconnect_attempts = 0
        self._reconnect_delay = initial_reconnect_delay
        self._connection_timeout_handle: asyncio.TimerHandle | None = None
        self._heartbeat_task: asyncio.Task | None = None

        # Message queue for when disconnected
        self._message_queue: list[tuple[str, list[Any]]] = []
        self._message_queue_task: asyncio.Task | None = None

        # Track registered handlers
        self._handlers: dict[OSCAddress, list[OSCHandler]] = {}

        # Track avatar changes
        self.current_avatar: str | None = None

        # Track connection health
        self._last_heartbeat_time: float = 0
        self._last_message_time: float = 0
        self._connection_start_time: float | None = None
        self._reconnect_start_time: float | None = None

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default OSC message handlers for VRChat communication.

        This method sets up the default message handlers for:
        - Avatar change notifications
        - Parameter updates
        - Avatar parameter changes
        - Input state changes
        """
        logger.debug("Registering default OSC message handlers")

        # Avatar change detection - triggered when the local or remote avatar changes
        self._dispatcher.map("/avatar/change", self._handle_avatar_change)

        # Parameter updates - handles all avatar parameter changes
        self._dispatcher.map("/avatar/parameters/*", self._handle_parameter_update)

        # Register a wildcard handler for all avatar-related messages
        # This allows catching any avatar-related OSC messages that don't have specific handlers
        self._dispatcher.set_default_handler(self._handle_default_message)

        logger.debug("Default OSC message handlers registered")

    @property
    def state(self) -> ConnectionState:
        """Get the current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if the OSC server is connected."""
        return self._state == ConnectionState.CONNECTED

    @property
    def stats(self) -> ConnectionStats:
        """Get connection statistics."""
        return self._connection_stats

    async def _set_state(self, new_state: ConnectionState) -> None:
        """Safely update the connection state and notify handlers.

        Args:
            new_state: The new connection state to transition to.

        Raises:
            RuntimeError: If an invalid state transition is attempted.
        """
        async with self._state_lock:
            old_state = self._state

            # Validate state transition
            valid_transitions = {
                ConnectionState.DISCONNECTED: [ConnectionState.CONNECTING, ConnectionState.ERROR],
                ConnectionState.CONNECTING: [
                    ConnectionState.CONNECTED,
                    ConnectionState.DISCONNECTED,
                    ConnectionState.ERROR,
                ],
                ConnectionState.CONNECTED: [
                    ConnectionState.DISCONNECTING,
                    ConnectionState.DISCONNECTED,
                    ConnectionState.ERROR,
                ],
                ConnectionState.RECONNECTING: [
                    ConnectionState.CONNECTED,
                    ConnectionState.DISCONNECTED,
                    ConnectionState.ERROR,
                ],
                ConnectionState.DISCONNECTING: [ConnectionState.DISCONNECTED, ConnectionState.ERROR],
                ConnectionState.ERROR: [ConnectionState.DISCONNECTED],
            }

            if new_state != old_state and new_state not in valid_transitions.get(old_state, []):
                raise RuntimeError(f"Invalid state transition: {old_state.name} -> {new_state.name}")

            # Update state
            self._state = new_state
            now = time.time()

            # Update statistics and handle state-specific logic
            if new_state == ConnectionState.CONNECTED:
                if old_state != ConnectionState.CONNECTED:
                    self._connection_stats.successful_connections += 1
                    self._connection_stats.last_connected = now
                    self._connection_start_time = now
                    self._reconnect_attempts = 0
                    self._reconnect_delay = self.initial_reconnect_delay

                    # Calculate average reconnection time if we were reconnecting
                    if self._reconnect_start_time is not None:
                        reconnect_time = now - self._reconnect_start_time
                        self._connection_stats.avg_reconnect_time = (
                            self._connection_stats.avg_reconnect_time
                            * (self._connection_stats.reconnection_attempts - 1)
                            + reconnect_time
                        ) / self._connection_stats.reconnection_attempts
                        self._reconnect_start_time = None

                    # Start heartbeat when connected
                    if self._heartbeat_task is None or self._heartbeat_task.done():
                        self._heartbeat_task = asyncio.create_task(self._heartbeat())

            elif new_state == ConnectionState.DISCONNECTED:
                if old_state == ConnectionState.CONNECTED:
                    self._connection_stats.disconnections += 1
                    self._connection_stats.last_disconnected = now

                    # Update total uptime
                    if self._connection_start_time is not None:
                        self._connection_stats.total_uptime += now - self._connection_start_time
                        self._connection_start_time = None

                    # Start reconnection if enabled
                    if self.auto_reconnect and old_state != ConnectionState.DISCONNECTING:
                        task = asyncio.create_task(self._start_reconnect())
                        self._background_tasks.add(task)
                        task.add_done_callback(self._background_tasks.discard)

                # Stop heartbeat when disconnected
                if self._heartbeat_task and not self._heartbeat_task.done():
                    self._heartbeat_task.cancel()
                    try:
                        await self._heartbeat_task
                    except asyncio.CancelledError:
                        pass
                    self._heartbeat_task = None

            # Cancel any pending connection timeout
            if self._connection_timeout_handle:
                self._connection_timeout_handle.cancel()
                self._connection_timeout_handle = None

        # Notify state change outside the lock to avoid deadlocks
        self._notify_state_change(new_state, old_state)

    def _notify_state_change(self, new_state: ConnectionState, old_state: ConnectionState) -> None:
        """Notify all state change handlers."""
        if new_state != old_state:
            logger.debug(f"Connection state changed: {old_state.name} -> {new_state.name}")

            # Notify handlers
            for handler in self._connection_handlers:
                try:
                    handler(new_state, old_state)
                except Exception as e:
                    logger.error(f"Error in connection state handler: {e}")

    async def _heartbeat(self) -> None:
        """Periodically check the connection status.

        This sends periodic heartbeat messages to verify the connection is still alive.
        If no response is received within the heartbeat timeout, the connection is considered dead.
        """
        time.time()

        try:
            while self._state == ConnectionState.CONNECTED:
                try:
                    # Send a ping message to check connection
                    self._last_heartbeat_time = time.time()
                    self.send_message("/avatar/parameters/VRCEmote", 0)

                    # Wait for next heartbeat, but check more frequently for timeouts
                    wait_until = self._last_heartbeat_time + self.heartbeat_interval
                    while time.time() < wait_until and self._state == ConnectionState.CONNECTED:
                        # Check if we've missed too many heartbeats
                        time_since_heartbeat = time.time() - self._last_heartbeat_time
                        if time_since_heartbeat > self.heartbeat_timeout:
                            raise TimeoutError("Heartbeat timeout - no response from VRChat")

                        # Short sleep to avoid busy waiting
                        await asyncio.sleep(0.1)

                except asyncio.CancelledError:
                    # Normal shutdown
                    raise
                except Exception as e:
                    logger.warning(f"Heartbeat failed: {e}")
                    # If we can't send or receive heartbeats, assume connection is lost
                    await self._handle_connection_error(f"Heartbeat failed: {e}")
                    break

        except asyncio.CancelledError:
            # Normal shutdown
            pass
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            await self._handle_connection_error(f"Heartbeat error: {e}")

    async def _handle_connection_error(self, error: str) -> None:
        """Handle a connection error and attempt to reconnect if needed.

        Args:
            error: Description of the error that occurred.
        """
        logger.error(f"Connection error: {error}")

        # Update error statistics
        self._connection_stats.error_count += 1
        self._connection_stats.last_error = error

        # Only try to reconnect if we were previously connected or connecting
        if self._state not in (ConnectionState.CONNECTED, ConnectionState.CONNECTING):
            return

        # Set error state
        await self._set_state(ConnectionState.ERROR)

        # Stop the current connection
        try:
            await self.stop()
        except Exception as e:
            logger.error(f"Error during connection cleanup: {e}")

        # Start reconnection process if enabled
        if self.auto_reconnect:
            await self._start_reconnect()

    async def _start_reconnect(self) -> None:
        """Start the reconnection process.

        This creates a new reconnection task if one isn't already running.
        """
        if self._reconnect_task and not self._reconnect_task.done():
            logger.debug("Reconnection already in progress")
            return  # Already reconnecting

        # Reset reconnection state
        self._reconnect_attempts = 0
        self._reconnect_delay = self.initial_reconnect_delay
        self._reconnect_start_time = time.time()

        # Start reconnection loop
        self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Attempt to reconnect with exponential backoff and jitter.

        This implements a robust reconnection strategy with the following features:
        - Exponential backoff to prevent overwhelming the server
        - Jitter to prevent thundering herd problem
        - Maximum reconnection attempts
        - Graceful cancellation
        """
        await self._set_state(ConnectionState.RECONNECTING)
        self._connection_stats.reconnection_attempts += 1

        try:
            while self.auto_reconnect and self._state == ConnectionState.RECONNECTING:
                # Check if we've exceeded max reconnection attempts
                if self.max_reconnect_attempts > 0 and self._reconnect_attempts >= self.max_reconnect_attempts:
                    logger.error(f"Max reconnection attempts ({self.max_reconnect_attempts}) reached")
                    await self._set_state(ConnectionState.ERROR)
                    return

                # Calculate delay with exponential backoff and jitter
                base_delay = min(
                    self.initial_reconnect_delay * (2 ** (self._reconnect_attempts - 1)), self.max_reconnect_delay
                )

                # Add jitter to prevent thundering herd
                jitter = random.uniform(1 - self.jitter_factor, 1 + self.jitter_factor)  # noqa: S311
                delay = min(base_delay * jitter, self.max_reconnect_delay)

                logger.info(
                    f"Attempting to reconnect in {delay:.1f}s "
                    f"(attempt {self._reconnect_attempts + 1}/{self.max_reconnect_attempts or '∞'})"
                )

                try:
                    # Wait for the delay or until cancelled
                    await asyncio.sleep(delay)

                    # Try to connect
                    self._reconnect_attempts += 1
                    self._connection_stats.connection_attempts += 1

                    logger.debug(f"Starting reconnection attempt {self._reconnect_attempts}")

                    # Set up connection timeout
                    try:
                        async with asyncio.timeout(self.connection_timeout):
                            await self._start_server()

                        # If we get here, connection was successful
                        logger.info("Reconnection successful")
                        return

                    except TimeoutError:
                        logger.warning("Connection attempt timed out")
                        await self._handle_connection_error("Connection timeout")

                except asyncio.CancelledError:
                    # Reconnect was cancelled
                    logger.info("Reconnection cancelled")
                    await self._set_state(ConnectionState.DISCONNECTED)
                    return

                except Exception as e:
                    logger.error(f"Reconnection attempt failed: {e}")
                    # Continue to next attempt

        except Exception as e:
            logger.error(f"Unexpected error in reconnection loop: {e}")
            await self._set_state(ConnectionState.ERROR)

        finally:
            # Clean up if we exit the loop
            if self._state == ConnectionState.RECONNECTING:
                await self._set_state(ConnectionState.DISCONNECTED)
                # Update error stats
                self._connection_stats.error_count += 1
                self._connection_stats.last_error = "Reconnection failed"

    async def _start_server(self) -> None:
        """Start the OSC server with connection timeout."""
        if self._server is not None:
            return

        try:
            # Set connecting state
            await self._set_state(ConnectionState.CONNECTING)

            # Create the OSC client
            self._client = SimpleUDPClient(self.send_ip, self.send_port)

            # Create and start the OSC server
            loop = asyncio.get_running_loop()
            self._server = AsyncIOOSCUDPServer((self.listen_ip, self.listen_port), self._dispatcher, loop)

            # Start the server in a background task
            self._server_task = asyncio.create_task(self._server.create_serve())

            # Set a connection timeout
            self._connection_timeout_handle = loop.call_later(
                self.connection_timeout,
                lambda: self._background_tasks.add(
                    asyncio.create_task(self._handle_connection_timeout())
                    .add_done_callback(self._background_tasks.discard)  # type: ignore
                ),
            )

            # Update connection state
            await self._set_state(ConnectionState.CONNECTED)

            logger.info(
                f"OSC server started on {self.listen_ip}:{self.listen_port}, sending to {self.send_ip}:{self.send_port}"
            )

            # Process any queued messages
            await self._process_message_queue()

        except Exception:
            # Clean up on error
            if self._server:
                self._server.close()
                self._server = None
            self._client = None

            if self._server_task and not self._server_task.done():
                self._server_task.cancel()
                try:
                    await self._server_task
                except asyncio.CancelledError:
                    pass
                self._server_task = None

            await self._set_state(ConnectionState.ERROR)
            raise

    async def _handle_connection_timeout(self) -> None:
        """Handle connection timeout."""
        if self._state == ConnectionState.CONNECTING:
            logger.error("Connection timed out")
            await self._handle_connection_error("Connection timed out")

    async def _process_message_queue(self) -> None:
        """Process any messages that were queued while disconnected."""
        if not self._message_queue:
            return

        logger.info(f"Processing {len(self._message_queue)} queued messages")

        # Process messages in the order they were received
        while self._message_queue and self._state == ConnectionState.CONNECTED:
            address, args = self._message_queue.pop(0)
            try:
                self._send_message_internal(address, args)
            except Exception as e:
                logger.warning(f"Failed to send queued message to {address}: {e}")

    async def start(self) -> None:
        """Start the OSC server."""
        if self._state != ConnectionState.DISCONNECTED:
            logger.warning(f"Cannot start OSC server: already {self._state.name}")
            return

        try:
            await self._start_server()
        except Exception as e:
            logger.error(f"Failed to start OSC server: {e}")
            await self._handle_connection_error(str(e))
            raise

    async def stop(self) -> None:
        """Stop the OSC server and client."""
        # If already stopping or stopped, do nothing
        if self._state in (ConnectionState.DISCONNECTING, ConnectionState.DISCONNECTED):
            return

        # Set disconnecting state
        await self._set_state(ConnectionState.DISCONNECTING)

        try:
            # Cancel any ongoing reconnection attempts
            if self._reconnect_task and not self._reconnect_task.done():
                logger.debug("Cancelling reconnection task")
                self._reconnect_task.cancel()
                try:
                    await self._reconnect_task
                except asyncio.CancelledError:
                    logger.debug("Reconnection task cancelled")
                except Exception as e:
                    logger.error(f"Error cancelling reconnection task: {e}")
                finally:
                    self._reconnect_task = None

            # Stop the heartbeat
            if self._heartbeat_task and not self._heartbeat_task.done():
                logger.debug("Stopping heartbeat")
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    logger.debug("Heartbeat stopped")
                except Exception as e:
                    logger.error(f"Error stopping heartbeat: {e}")
                finally:
                    self._heartbeat_task = None

            # Stop the server if it's running
            if self._server:
                logger.debug("Stopping OSC server")
                try:
                    self._server.close()
                    if self._server_task and not self._server_task.done():
                        self._server_task.cancel()
                        try:
                            await self._server_task
                        except asyncio.CancelledError:
                            logger.debug("Server task cancelled")
                except Exception as e:
                    logger.error(f"Error stopping OSC server: {e}")
                finally:
                    self._server = None
                    self._server_task = None

            # Clear the client
            logger.debug("Clearing OSC client")
            self._client = None

            # Clear any queued messages
            self._message_queue.clear()

            # Update statistics
            if self._connection_start_time is not None:
                self._connection_stats.total_uptime += time.time() - self._connection_start_time
                self._connection_start_time = None

            logger.info("OSC manager stopped")

        except Exception as e:
            logger.error(f"Error during stop: {e}")
            await self._set_state(ConnectionState.ERROR)
            raise

        finally:
            # Always ensure we end in a clean state
            await self._set_state(ConnectionState.DISCONNECTED)

    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.stop()

    @property
    def server_running(self) -> bool:
        """Check if the OSC server is running."""
        return self._is_connected

    def add_connection_handler(self, handler: Callable[[ConnectionState, ConnectionState | None], None]) -> None:
        """Add a handler for connection state changes.

        Args:
            handler: A function that takes the new state and previous state as arguments.
        """
        if handler not in self._connection_handlers:
            self._connection_handlers.append(handler)

    def remove_connection_handler(self, handler: Callable[[ConnectionState, ConnectionState | None], None]) -> None:
        """Remove a connection state change handler."""
        if handler in self._connection_handlers:
            self._connection_handlers.remove(handler)

    def add_handler(self, address: str, handler: OSCHandler) -> None:
        """Add a handler for a specific OSC address pattern.

        Args:
            address: The OSC address pattern to match (supports wildcards)
            handler: The handler function to call when a matching message is received
        """
        if address not in self._handlers:
            self._handlers[address] = []

            # Register with the dispatcher if this is a new address pattern
            self._dispatcher.map(address, self._create_dispatch_handler(address))

        if handler not in self._handlers[address]:
            self._handlers[address].append(handler)

    def remove_handler(self, address: str, handler: OSCHandler) -> None:
        """Remove a handler for a specific OSC address pattern."""
        if address in self._handlers and handler in self._handlers[address]:
            self._handlers[address].remove(handler)

            # If no more handlers for this address, remove it from the dispatcher
            if not self._handlers[address]:
                del self._handlers[address]
                self._dispatcher.unmap(address)

    def _create_dispatch_handler(self, address: str) -> Callable[[str, list[Any]], None]:
        """Create a dispatch handler for the given address pattern."""

        def handler(osc_address: str, *args: Any) -> None:
            # Get the actual OSC values (args is a tuple of (values,), so we take the first element)
            values = args[0] if args else []

            # Call all registered handlers for this address pattern
            for h in self._handlers.get(address, []):
                try:
                    h(osc_address, values)
                except Exception as e:
                    logger.error(f"Error in OSC handler for {osc_address}: {e}")

        return handler

    # === OSC Message Sending ===

    def send_message(self, address: str, *args: OSCValue) -> None:
        """Send an OSC message.

        Args:
            address: The OSC address to send the message to
            *args: The values to send (bool, float, int, str, bytes, or None)
        """
        if not address.startswith("/"):
            logger.warning(f"Invalid OSC address: {address}")
            return

        # Convert Python types to OSC-compatible types
        osc_args = []
        for arg in args:
            if isinstance(arg, bool):
                # Convert bool to int (0 or 1) since VRChat expects int for boolean parameters
                osc_args.append(1 if arg else 0)
            elif arg is None:
                # Skip None values
                continue
            else:
                # Pass through other types as-is
                osc_args.append(arg)

        # Send the message or queue it if not connected
        if self._state == ConnectionState.CONNECTED and self._client is not None:
            try:
                self._send_message_internal(address, osc_args)
                self._connection_stats.messages_sent += 1
            except Exception as e:
                logger.error(f"Failed to send OSC message to {address}: {e}")
                task = asyncio.create_task(self._handle_connection_error(f"Send failed: {e}"))
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
        elif self.auto_reconnect and self._state in (ConnectionState.RECONNECTING, ConnectionState.CONNECTING):
            # Queue the message if we're trying to reconnect
            self._message_queue.append((address, osc_args))
            if len(self._message_queue) > 100:  # Prevent unbounded queue growth
                logger.warning("Message queue too large, discarding oldest message")
                self._message_queue.pop(0)
        else:
            logger.warning(f"Cannot send OSC message: Not connected to {self.send_ip}:{self.send_port}")

    def _send_message_internal(self, address: str, args: list[Any]) -> None:
        """Internal method to send an OSC message without connection checks."""
        if self._client is None:
            raise RuntimeError("OSC client not initialized")

        try:
            self._client.send_message(address, args)
        except Exception as e:
            logger.error(f"Failed to send OSC message to {address}: {e}")
            raise

    def send_parameter(self, parameter_name: str, value: OSCValue) -> None:
        """Send a parameter update to VRChat.

        Args:
            parameter_name: The name of the parameter to update
            value: The value to set (bool, float, int, str, or None)
        """
        self.send_message(f"/avatar/parameters/{parameter_name}", value)

    def load_avatar(self, avatar_id: str) -> None:
        """Load an avatar by ID.

        This method sends an OSC message to VRChat to change the current avatar.
        The actual avatar change happens asynchronously in VRChat.

        Args:
            avatar_id: The ID of the avatar to load. This should be a valid avatar ID
                     that exists in the user's VRChat account.

        Raises:
            ValueError: If avatar_id is empty or None
            RuntimeError: If there's an issue sending the OSC message
        """
        if not avatar_id:
            raise ValueError("Avatar ID cannot be empty or None")

        logger.info(f"Requesting avatar change to: {avatar_id}")

        try:
            # Send the avatar change message
            self.send_message("/avatar/change", avatar_id)

            # Update statistics
            self._connection_stats.messages_sent += 1
            logger.debug(f"Sent avatar change request for: {avatar_id}")

        except Exception as e:
            error_msg = f"Failed to send avatar change request for {avatar_id}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    # === OSC Message Handlers ===

    def _handle_avatar_change(self, address: str, *args: Any) -> None:
        """Handle avatar change notifications from VRChat.

        This method is called when VRChat notifies us of an avatar change.
        It updates the current avatar and notifies any registered handlers.

        Args:
            address: The OSC address that triggered this handler
            *args: The arguments sent with the OSC message. The first argument
                  should be the avatar ID.
        """
        if not args or not args[0]:
            logger.warning("Received empty avatar change notification")
            return

        # Extract the new avatar ID from the arguments
        new_avatar = args[0][0] if isinstance(args[0], (list, tuple)) else args[0]

        # Ensure the avatar ID is a string
        if isinstance(new_avatar, (str, bytes)):
            new_avatar = new_avatar.decode("utf-8") if isinstance(new_avatar, bytes) else new_avatar

            # Only process if the avatar has actually changed
            if new_avatar != self.current_avatar:
                old_avatar = self.current_avatar
                self.current_avatar = new_avatar

                # Update statistics
                self._connection_stats.messages_received += 1

                # Log the avatar change
                logger.info(f"Avatar changed from '{old_avatar}' to '{new_avatar}'")

                # Prepare the handler arguments
                handler_args = {
                    "old_avatar": old_avatar,
                    "new_avatar": new_avatar,
                    "timestamp": time.time(),
                    "source": "vrchat",
                }

                # Notify any registered handlers
                for handler in self._handlers.get("/avatar/change", []):
                    try:
                        handler(address, [new_avatar, handler_args])
                        logger.debug(f"Notified handler for avatar change: {handler}")
                    except Exception as e:
                        logger.error(f"Error in avatar change handler {handler}: {e}", exc_info=True)

                # Also notify any wildcard handlers
                wildcard_address = "/avatar/*"
                if wildcard_address in self._handlers and wildcard_address != address:
                    for handler in self._handlers[wildcard_address]:
                        try:
                            handler(address, ["change", new_avatar, handler_args])
                            logger.debug(f"Notified wildcard handler for avatar change: {handler}")
                        except Exception as e:
                            logger.error(f"Error in wildcard avatar handler {handler}: {e}", exc_info=True)
            else:
                logger.debug(f"Received duplicate avatar change notification for: {new_avatar}")
        else:
            logger.warning(f"Received invalid avatar ID type: {type(new_avatar).__name__}")

    def _handle_default_message(self, address: str, *args: Any) -> None:
        """Handle any OSC messages that don't have a specific handler.

        This method is called for any OSC message that doesn't match a registered
        handler pattern. It's useful for debugging and logging unexpected messages.

        Args:
            address: The OSC address of the unhandled message
            *args: The arguments sent with the OSC message
        """
        # Skip empty messages
        if not args:
            return

        # Log the unhandled message for debugging
        logger.debug(f"Received unhandled OSC message: {address} {args}")

        # Check if this is an avatar-related message we might want to handle
        if address.startswith("/avatar/"):
            # Log avatar-related messages at a higher level since they might be important
            logger.info(f"Unhandled avatar message: {address} {args}")

            # If we have a wildcard handler for avatar messages, notify it
            wildcard_address = "/avatar/*"
            if wildcard_address in self._handlers:
                for handler in self._handlers[wildcard_address]:
                    try:
                        handler(address, args)
                    except Exception as e:
                        logger.error(f"Error in wildcard avatar handler for {address}: {e}", exc_info=True)

    def _handle_parameter_update(self, address: str, *args: Any) -> None:
        """Handle parameter update notifications from VRChat.

        This method is called when VRChat sends parameter updates for the current avatar.
        It processes the parameter updates and notifies any registered handlers.

        Args:
            address: The OSC address of the parameter (e.g., "/avatar/parameters/MyParam")
            *args: The new value(s) of the parameter
        """
        if not args or not args[0]:
            logger.debug(f"Received empty parameter update for {address}")
            return

        try:
            # Extract the parameter name from the address
            param_name = address.split("/")[-1]

            # Extract the parameter value, handling different argument formats
            param_value = args[0][0] if (args and isinstance(args[0], (list, tuple))) else args[0]

            # Log the parameter update at debug level
            logger.debug(f"Parameter update - {param_name}: {param_value} (type: {type(param_value).__name__})")

            # Update statistics
            self._connection_stats.messages_received += 1

            # Prepare the handler arguments
            handler_args = {
                "name": param_name,
                "value": param_value,
                "timestamp": time.time(),
                "source": "vrchat",
                "address": address,
            }

            # Notify any specific handlers for this parameter
            for handler in self._handlers.get(address, []):
                try:
                    handler(address, [param_value, handler_args])
                    logger.debug(f"Notified handler for parameter {param_name}")
                except Exception as e:
                    logger.error(f"Error in parameter handler for {address}: {e}", exc_info=True)

            # Also notify any wildcard parameter handlers
            param_wildcard = "/avatar/parameters/*"
            if param_wildcard in self._handlers and param_wildcard != address:
                for handler in self._handlers[param_wildcard]:
                    try:
                        handler(address, [param_name, param_value, handler_args])
                        logger.debug(f"Notified wildcard handler for parameter {param_name}")
                    except Exception as e:
                        logger.error(f"Error in wildcard parameter handler for {address}: {e}", exc_info=True)

            # Also notify any general avatar wildcard handlers
            avatar_wildcard = "/avatar/*"
            if avatar_wildcard in self._handlers and avatar_wildcard != address:
                for handler in self._handlers[avatar_wildcard]:
                    try:
                        handler(address, ["parameter", param_name, param_value, handler_args])
                        logger.debug(f"Notified avatar wildcard handler for parameter {param_name}")
                    except Exception as e:
                        logger.error(f"Error in avatar wildcard handler for {address}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error processing parameter update for {address}: {e}", exc_info=True)
