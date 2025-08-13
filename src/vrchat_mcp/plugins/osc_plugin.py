"""
OSC Tools Plugin for VRChat MCP.

Provides tools for monitoring and debugging OSC communication.
"""

import asyncio
import logging
import time
import re
from typing import Dict, List, Optional, Any, Union, Callable, Awaitable, Set
from dataclasses import dataclass, field
from datetime import datetime

from ..models import MessageRecord, MessageDirection
from ..plugins import Plugin, tool, event_listener

logger = logging.getLogger(__name__)

@dataclass
class OSCFilter:
    """Filter criteria for OSC messages."""
    address_pattern: str = "*"
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    direction: Optional[MessageDirection] = None
    include_undef: bool = True

class OSCPlugin(Plugin):
    """Plugin for OSC monitoring and debugging."""
    
    def __init__(self):
        self.message_history: List[MessageRecord] = []
        self.max_history: int = 1000
        self.active_filters: Dict[str, OSCFilter] = {}
        self.subscribers: Set[Callable[[MessageRecord], Awaitable[None]]] = set()
        self.message_counters: Dict[str, int] = {
            "incoming": 0,
            "outgoing": 0,
            "errors": 0
        }
        self.byte_counters: Dict[str, int] = {
            "incoming": 0,
            "outgoing": 0
        }
        self.start_time: float = time.time()
        self._message_lock = asyncio.Lock()
    
    @property
    def name(self) -> str:
        return "osc_tools"
    
    @property
    def description(self) -> str:
        return "Provides OSC monitoring and debugging tools"
    
    async def on_load(self, mcp):
        """Initialize the plugin with the MCP instance."""
        self.mcp = mcp
        logger.info("OSC Tools plugin loaded")
    
    def _match_pattern(self, address: str, pattern: str) -> bool:
        """Check if an OSC address matches a pattern."""
        # Convert OSC pattern to regex
        regex = re.escape(pattern).replace('\*', '.*?').replace('\?', '.')
        return bool(re.fullmatch(regex, address))
    
    async def _add_message(self, message: MessageRecord) -> None:
        """Add a message to history and notify subscribers."""
        async with self._message_lock:
            # Add to history
            self.message_history.append(message)
            
            # Update counters
            direction = message.direction.value.lower()
            self.message_counters[direction] = self.message_counters.get(direction, 0) + 1
            
            # Estimate message size (roughly)
            msg_size = len(str(message.address)) + sum(len(str(arg)) for arg in message.args) + 20
            self.byte_counters[direction] = self.byte_counters.get(direction, 0) + msg_size
            
            # Trim history if needed
            if len(self.message_history) > self.max_history * 1.5:
                self.message_history = self.message_history[-self.max_history:]
        
        # Notify subscribers
        await self._notify_subscribers(message)
    
    async def _notify_subscribers(self, message: MessageRecord) -> None:
        """Notify all subscribers about a new message."""
        for callback in list(self.subscribers):
            try:
                await callback(message)
            except Exception as e:
                logger.error(f"Error in OSC subscriber: {e}", exc_info=True)
    
    @tool(
        name="monitor_osc",
        description="Monitor OSC messages with filtering",
        category="OSC",
        args={
            "address_pattern": {"type": "string", "description": "OSC address pattern to match", "default": "*"},
            "min_value": {"type": "number", "description": "Minimum parameter value to include", "default": None},
            "max_value": {"type": "number", "description": "Maximum parameter value to include", "default": None},
            "direction": {"type": "string", "description": "Direction filter (incoming/outgoing)", "default": None},
            "limit": {"type": "number", "description": "Maximum number of messages to return", "default": 100}
        },
        returns={"messages": "list[dict]", "count": "number"},
        examples=[
            {"description": "Monitor all messages", "code": "monitor_osc()"},
            {"description": "Monitor specific parameter", "code": "monitor_osc(address_pattern='/avatar/parameters/*')"}
        ]
    )
    async def monitor_osc(
        self,
        address_pattern: str = "*",
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        direction: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Monitor OSC messages with filtering."""
        filtered = []
        count = 0
        
        # Convert direction string to enum if provided
        direction_enum = None
        if direction:
            try:
                direction_enum = MessageDirection[direction.upper()]
            except KeyError:
                pass
        
        async with self._message_lock:
            # Check messages in reverse order (newest first)
            for msg in reversed(self.message_history):
                # Check address pattern
                if address_pattern != "*" and not self._match_pattern(msg.address, address_pattern):
                    continue
                    
                # Check direction
                if direction_enum is not None and msg.direction != direction_enum:
                    continue
                    
                # Check value range if args exist
                if msg.args and (min_value is not None or max_value is not None):
                    arg = msg.args[0]
                    if isinstance(arg, (int, float)):
                        if min_value is not None and arg < min_value:
                            continue
                        if max_value is not None and arg > max_value:
                            continue
                
                filtered.append(msg.to_dict())
                count += 1
                
                if count >= limit:
                    break
        
        return {
            "messages": filtered,
            "count": count
        }
    
    @tool(
        name="osc_stats",
        description="Get OSC communication statistics",
        category="OSC",
        args={
            "reset": {"type": "boolean", "description": "Whether to reset counters after reading", "default": False}
        },
        returns={
            "message_count": {"type": "object", "description": "Count of messages by direction"},
            "byte_count": {"type": "object", "description": "Bytes transferred by direction"},
            "uptime": {"type": "number", "description": "Seconds since plugin start"},
            "messages_per_second": {"type": "number", "description": "Average messages per second"}
        },
        examples=[
            {"description": "Get current stats", "code": "osc_stats()"},
            {"description": "Get and reset stats", "code": "osc_stats(reset=True)"}
        ]
    )
    async def get_osc_stats(self, reset: bool = False) -> Dict[str, Any]:
        """Get OSC communication statistics."""
        uptime = time.time() - self.start_time
        total_messages = sum(self.message_counters.values())
        mps = total_messages / uptime if uptime > 0 else 0
        
        stats = {
            "message_count": self.message_counters.copy(),
            "byte_count": self.byte_counters.copy(),
            "uptime": uptime,
            "messages_per_second": mps
        }
        
        if reset:
            self.message_counters = {"incoming": 0, "outgoing": 0, "errors": 0}
            self.byte_counters = {"incoming": 0, "outgoing": 0}
            self.start_time = time.time()
        
        return stats
    
    @tool(
        name="subscribe_osc",
        description="Subscribe to OSC messages in real-time",
        category="OSC",
        args={
            "address_pattern": {"type": "string", "description": "OSC address pattern to match", "default": "*"},
            "min_value": {"type": "number", "description": "Minimum parameter value to include", "default": None},
            "max_value": {"type": "number", "description": "Maximum parameter value to include", "default": None},
            "direction": {"type": "string", "description": "Direction filter (incoming/outgoing)", "default": None}
        },
        returns={"success": "boolean", "subscription_id": "string"},
        examples=[
            {"description": "Subscribe to all messages", "code": "subscribe_osc()"},
            {"description": "Subscribe to specific parameter", "code": "subscribe_osc(address_pattern='/avatar/parameters/*')"}
        ]
    )
    async def subscribe_osc(
        self,
        address_pattern: str = "*",
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        direction: Optional[str] = None
    ) -> Dict[str, Any]:
        """Subscribe to OSC messages that match the given criteria."""
        # Convert direction string to enum if provided
        direction_enum = None
        if direction:
            try:
                direction_enum = MessageDirection[direction.upper()]
            except KeyError:
                pass
        
        # Create a filter
        filter_id = f"sub_{len(self.active_filters)}_{int(time.time())}"
        self.active_filters[filter_id] = OSCFilter(
            address_pattern=address_pattern,
            min_value=min_value,
            max_value=max_value,
            direction=direction_enum
        )
        
        return {
            "success": True,
            "subscription_id": filter_id,
            "message": f"Subscribed to OSC messages with filter {filter_id}"
        }
    
    @tool(
        name="unsubscribe_osc",
        description="Unsubscribe from OSC messages",
        category="OSC",
        args={
            "subscription_id": {"type": "string", "description": "ID of the subscription to remove"}
        },
        returns={"success": "boolean", "message": "string"},
        examples=[
            {"description": "Unsubscribe from messages", "code": "unsubscribe_osc(subscription_id='sub_0_1234567890')"}
        ]
    )
    async def unsubscribe_osc(self, subscription_id: str) -> Dict[str, Any]:
        """Unsubscribe from OSC messages."""
        if subscription_id in self.active_filters:
            del self.active_filters[subscription_id]
            return {"success": True, "message": f"Unsubscribed from {subscription_id}"}
        
        return {"success": False, "message": f"Subscription {subscription_id} not found"}
    
    @tool(
        name="send_osc",
        description="Send an OSC message",
        category="OSC",
        args={
            "address": {"type": "string", "description": "OSC address"},
            "args": {"type": "array", "description": "Arguments to send", "default": []}
        },
        returns={"success": "boolean", "message": "string"},
        examples=[
            {"description": "Send a float parameter", "code": "send_osc('/avatar/parameters/MyParam', [0.5])"},
            {"description": "Send a boolean parameter", "code": "send_osc('/avatar/parameters/MyBool', [True])"}
        ]
    )
    async def send_osc(self, address: str, args: List[Any] = None) -> Dict[str, Any]:
        """Send an OSC message."""
        if args is None:
            args = []
        
        try:
            if hasattr(self.mcp, 'osc_inspector'):
                await self.mcp.osc_inspector.send_message(address, *args)
                
                # Record the outgoing message
                message = MessageRecord(
                    address=address,
                    args=args,
                    direction=MessageDirection.OUTGOING
                )
                await self._add_message(message)
                
                return {"success": True, "message": f"Sent OSC: {address} {args}"}
            else:
                return {"success": False, "message": "OSC inspector not available"}
        except Exception as e:
            logger.error(f"Error sending OSC message: {e}", exc_info=True)
            self.message_counters["errors"] += 1
            return {"success": False, "message": f"Error sending OSC message: {e}"}
    
    @event_listener("osc_message_received")
    async def on_osc_message(self, message: MessageRecord) -> None:
        """Handle incoming OSC messages."""
        # Add to history
        await self._add_message(message)
        
        # Update counters
        direction = message.direction.value.lower()
        self.message_counters[direction] = self.message_counters.get(direction, 0) + 1
        
        # Estimate message size (roughly)
        msg_size = len(str(message.address)) + sum(len(str(arg)) for arg in message.args) + 20
        self.byte_counters[direction] = self.byte_counters.get(direction, 0) + msg_size

# This allows the plugin to be auto-discovered
PLUGIN_CLASS = OSCPlugin
