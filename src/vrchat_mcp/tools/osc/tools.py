"""
OSC (Open Sound Control) Manager for VRChat MCP.

This module handles all OSC communication with VRChat, including sending and receiving
parameters, handling avatar changes, and managing the OSC connection state.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union

from pythonosc import udp_client, osc_server, dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

from ...models import OSCMessage, OSCBundle
from ..shared.fastsearch import fast_search

logger = logging.getLogger(__name__)

class OSCManager:
    """
    Manages OSC communication with VRChat.

    Handles sending and receiving OSC messages, managing connection state,
    and providing a clean interface for avatar parameter control.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize the OSC manager with configuration."""
        self.config = {
            'send_host': config.get('send_host', '127.0.0.1'),
            'send_port': config.get('send_port', 9000),
            'receive_host': config.get('receive_host', '127.0.0.1'),
            'receive_port': config.get('receive_port', 9001),
            'auto_connect': config.get('auto_connect', True),
            'default_avatar_id': config.get('default_avatar_id', 'avatar1'),
            'auto_index_parameters': config.get('auto_index_parameters', True),
            'search_threshold': config.get('search_threshold', 50)
        }

        self.client: Optional[SimpleUDPClient] = None
        self.server: Optional[AsyncIOOSCUDPServer] = None
        self.dispatcher = dispatcher.Dispatcher()
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop running, will get it later when needed
            self.loop = None

        # Track avatar state
        self.avatars: Dict[str, Dict[str, Any]] = {}
        self.current_avatar_id: Optional[str] = None

        # Track discovered parameters and endpoints
        self._discovered_parameters: Set[str] = set()
        self._discovered_endpoints: Set[str] = set()

        # Register default handlers
        self._register_default_handlers()

        # Initialize search integration
        self._init_search()

    def _init_search(self) -> None:
        """Initialize search integration."""
        # Register searchable OSC endpoints
        self._index_osc_endpoint("/avatar/parameters/*", "Avatar parameters")
        self._index_osc_endpoint("/avatar/change", "Avatar change event")
        self._index_osc_endpoint("/avatar/parameters/VRCEmote", "VRChat emote parameter")
        self._index_osc_endpoint("/avatar/parameters/VRCGestures", "VRChat gestures parameter")

    def _index_parameter(self, param_name: str, param_type: str = "Float") -> None:
        """Index a parameter in the search system."""
        if not self.config['auto_index_parameters'] or not param_name:
            return

        if param_name not in self._discovered_parameters:
            self._discovered_parameters.add(param_name)

            # Add to FastSearch (will be awaited when in async context)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(
                        fast_search.index_parameter(
                            param_name=param_name,
                            param_type=param_type,
                            source="discovered",
                            first_seen=loop.time()
                        )
                    )
            except RuntimeError:
                # No event loop, skip async indexing for now
                pass

            logger.debug("Indexed parameter", extra={"parameter": param_name})

    def _index_osc_endpoint(self, endpoint: str, description: str = "") -> None:
        """Index an OSC endpoint in the search system."""
        if not endpoint or endpoint in self._discovered_endpoints:
            return

        self._discovered_endpoints.add(endpoint)

        # Add to FastSearch (will be awaited when in async context)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    fast_search.index_osc_endpoint(
                        endpoint=endpoint,
                        description=description,
                        first_seen=loop.time()
                    )
                )
        except RuntimeError:
            # No event loop, skip async indexing for now
            pass

        logger.debug("Indexed OSC endpoint", extra={"endpoint": endpoint})

    def _register_default_handlers(self) -> None:
        """Register default OSC message handlers."""
        # Avatar parameter changes
        self.dispatcher.map("/avatar/parameters/*", self._handle_parameter_change)

        # Avatar change events
        self.dispatcher.map("/avatar/change", self._handle_avatar_change)

        # Health/status updates
        self.dispatcher.map("/avatar/parameters/VRCEmote", self._handle_emote_change)
        self.dispatcher.map("/avatar/parameters/VRCGestures", self._handle_gesture_change)

    async def connect(self) -> None:
        """Establish OSC connections to VRChat."""
        if self.client is None:
            self.client = udp_client.SimpleUDPClient(
                self.config['send_host'],
                self.config['send_port']
            )
            logger.info(
                "OSC client connected",
                extra={"host": self.config['send_host'], "port": self.config['send_port']}
            )

        if self.server is None:
            # Get event loop if not set during initialization
            if self.loop is None:
                self.loop = asyncio.get_event_loop()

            server = osc_server.AsyncIOOSCUDPServer(
                (self.config['receive_host'], self.config['receive_port']),
                self.dispatcher,
                self.loop
            )
            self.server = server
            transport, _ = await server.create_serve_endpoint()
            logger.info(
                "OSC server started",
                extra={
                    "host": self.config['receive_host'],
                    "port": self.config['receive_port']
                }
            )

    async def disconnect(self) -> None:
        """Disconnect OSC connections."""
        if self.server is not None:
            self.server.close()
            self.server = None
            logger.info("OSC server stopped")

        self.client = None

    async def send_message(self, message: OSCMessage) -> None:
        """Send an OSC message to VRChat."""
        if self.client is None:
            raise RuntimeError("OSC client not connected")

        self.client.send_message(message.address, message.args)
        logger.debug("Sent OSC message", extra={"address": message.address, "args": message.args})

    async def send_bundle(self, bundle: OSCBundle) -> None:
        """Send an OSC bundle to VRChat."""
        if self.client is None:
            raise RuntimeError("OSC client not connected")

        # Implementation for sending bundles would go here
        # This is a simplified example
        for item in bundle.content:
            if isinstance(item, OSCMessage):
                await self.send_message(item)

    async def send_parameter(
        self,
        parameter_name: str,
        value: Union[bool, float, int, str],
        avatar_id: Optional[str] = None
    ) -> None:
        """Send a parameter update to VRChat."""
        avatar_id = avatar_id or self.current_avatar_id or self.config['default_avatar_id']
        address = f"/avatar/parameters/{parameter_name}"

        if isinstance(value, bool):
            value_int = 1 if value else 0
            await self.send_message(OSCMessage(address=address, args=[value_int]))
        elif isinstance(value, (int, float)):
            await self.send_message(OSCMessage(address=address, args=[float(value)]))
        elif isinstance(value, str):
            await self.send_message(OSCMessage(address=address, args=[value]))
        else:
            raise ValueError(f"Unsupported parameter type: {type(value).__name__}")

        logger.debug(
            "Sent parameter update",
            extra={
                "avatar_id": avatar_id,
                "parameter": parameter_name,
                "value": value
            }
        )

    # Handler methods for incoming OSC messages
    def _handle_parameter_change(self, address: str, *args) -> None:
        """Handle incoming parameter changes from VRChat."""
        parameter_name = address.split('/')[-1]
        value = args[0] if args else None

        if self.current_avatar_id and self.current_avatar_id in self.avatars:
            self.avatars[self.current_avatar_id]['parameters'][parameter_name] = value

            logger.debug(
                "Parameter changed",
                extra={
                    "avatar_id": self.current_avatar_id,
                    "parameter": parameter_name,
                    "value": value
                }
            )

    def _handle_avatar_change(self, address: str, avatar_id: str) -> None:
        """Handle avatar change events from VRChat."""
        self.current_avatar_id = avatar_id

        if avatar_id not in self.avatars:
            self.avatars[avatar_id] = {
                'parameters': {},
                'last_seen': asyncio.get_event_loop().time()
            }

        logger.info("Avatar changed", extra={"avatar_id": avatar_id})

    def _handle_emote_change(self, address: str, emote_id: int) -> None:
        """Handle emote change events."""
        logger.debug("Emote changed", extra={"emote_id": emote_id})

    def _handle_gesture_change(self, address: str, gesture_id: int) -> None:
        """Handle gesture change events."""
        logger.debug("Gesture changed", extra={"gesture_id": gesture_id})

    # Utility methods
    def get_avatar_parameters(self, avatar_id: Optional[str] = None) -> Dict[str, Any]:
        """Get all parameters for an avatar."""
        avatar_id = avatar_id or self.current_avatar_id
        if avatar_id and avatar_id in self.avatars:
            return self.avatars[avatar_id].get('parameters', {})
        return {}

    def get_parameter_value(self, parameter_name: str, avatar_id: Optional[str] = None, default: Any = None) -> Any:
        """Get the current value of a parameter."""
        avatar_id = avatar_id or self.current_avatar_id
        if avatar_id and avatar_id in self.avatars:
            return self.avatars[avatar_id].get('parameters', {}).get(parameter_name, default)
        return default