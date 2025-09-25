"""
WebSocket-based debug interface for VRChat MCP.

Provides a real-time web interface for monitoring and interacting with
OSC messages, avatar states, and system status.
"""

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable, Awaitable, Union
from pathlib import Path
import aiohttp
from aiohttp import web
import websockets
from websockets import WebSocketServerProtocol

from .osc_inspector import OSCInspector, MessageDirection, MessageRecord

logger = logging.getLogger(__name__)

class DebugUI:
    """WebSocket-based debug interface for VRChat MCP."""
    
    def __init__(
        self,
        osc_inspector: OSCInspector,
        host: str = "0.0.0.0",
        port: int = 8765,
        web_root: Optional[Union[str, Path]] = None
    ):
        """Initialize the debug interface.
        
        Args:
            osc_inspector: OSCInspector instance to monitor
            host: Host to bind the web server to
            port: Port to bind the web server to
            web_root: Path to web assets (for custom UI)
        """
        self.osc_inspector = osc_inspector
        self.host = host
        self.port = port
        self.web_root = web_root or Path(__file__).parent / "web"
        
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.websockets: Set[WebSocketServerProtocol] = set()
        
        # Set up routes
        self.app.router.add_get("/ws", self.websocket_handler)
        
        # Serve static files if web root exists
        if self.web_root.exists():
            self.app.router.add_static("/", self.web_root, show_index=True)
    
    async def start(self) -> None:
        """Start the debug web server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        logger.info(f"Debug UI available at http://{self.host}:{self.port}")
    
    async def stop(self) -> None:
        """Stop the debug web server."""
        # Close all WebSocket connections
        for ws in list(self.websockets):
            await ws.close(code=1000, reason="Server shutting down")
        
        # Stop the web server
        if self.runner:
            await self.runner.cleanup()
        
        logger.info("Debug UI stopped")
    
    async def websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # Add to active connections
        self.websockets.add(ws)
        logger.debug(f"New WebSocket connection from {request.remote}")
        
        try:
            # Send initial state
            await self.send_system_status(ws)
            
            # Handle messages
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        await self.handle_ws_message(ws, json.loads(msg.data))
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON received: {msg.data}")
                    except Exception as e:
                        logger.error(f"Error handling WebSocket message: {e}", exc_info=True)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        finally:
            # Clean up
            self.websockets.discard(ws)
            logger.debug("WebSocket connection closed")
        
        return ws
    
    async def handle_ws_message(
        self, 
        ws: web.WebSocketResponse, 
        message: Dict[str, Any]
    ) -> None:
        """Handle incoming WebSocket messages."""
        msg_type = message.get("type")
        
        if msg_type == "get_messages":
            # Send recent message history
            limit = message.get("limit", 100)
            messages = self.osc_inspector.get_message_history(limit)
            await self.send(ws, {
                "type": "messages",
                "messages": messages
            })
            
        elif msg_type == "filter_messages":
            # Filter messages by criteria
            filtered = self.osc_inspector.filter_messages(
                address_pattern=message.get("address_pattern", r".*"),
                direction=MessageDirection[message["direction"]] if "direction" in message else None,
                min_value=message.get("min_value"),
                max_value=message.get("max_value")
            )
            await self.send(ws, {
                "type": "filtered_messages",
                "messages": filtered
            })
            
        elif msg_type == "send_message":
            # Send an OSC message
            try:
                self.osc_inspector.send_message(
                    message["address"],
                    *message.get("args", [])
                )
                await self.send(ws, {"type": "message_sent"})
            except Exception as e:
                await self.send(ws, {
                    "type": "error",
                    "message": f"Failed to send message: {e}"
                })
    
    async def send_system_status(self, ws: web.WebSocketResponse) -> None:
        """Send current system status to a WebSocket client."""
        stats = self.osc_inspector.get_statistics()
        await self.send(ws, {
            "type": "status",
            "status": {
                "osc": {
                    "server": f"{self.osc_inspector.server_ip}:{self.osc_inspector.server_port}",
                    "client": f"{self.osc_inspector.client_ip}:{self.osc_inspector.client_port}",
                    **stats
                },
                "server_time": time.time(),
                "uptime": time.time() - (stats.get("start_time", time.time()))
            }
        })
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Send a message to all connected WebSocket clients."""
        if not self.websockets:
            return
            
        message_str = json.dumps(message)
        for ws in list(self.websockets):
            try:
                await ws.send_str(message_str)
            except Exception as e:
                logger.error(f"Error sending WebSocket message: {e}")
    
    async def send(self, ws: web.WebSocketResponse, message: Dict[str, Any]) -> None:
        """Send a message to a specific WebSocket client."""
        try:
            await ws.send_json(message)
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
    
    # Event handlers for OSC inspector
    
    def on_osc_message(self, record: MessageRecord) -> None:
        """Handle a new OSC message."""
        asyncio.create_task(self.broadcast({
            "type": "new_message",
            "message": record.to_dict()
        }))
    
    def on_status_update(self) -> None:
        """Handle status updates."""
        asyncio.create_task(self.broadcast({
            "type": "status_update",
            "status": self.osc_inspector.get_statistics()
        }))
