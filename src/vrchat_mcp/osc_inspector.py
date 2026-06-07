"""OSC Message Inspector for monitoring and debugging OSC traffic in VRChat MCP."""

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

logger = logging.getLogger(__name__)


class MessageDirection(Enum):
    INCOMING = auto()  # From VRChat to MCP
    OUTGOING = auto()  # From MCP to VRChat


@dataclass
class MessageRecord:
    """Record of an OSC message for logging and playback."""

    timestamp: float
    address: str
    args: list[Any]
    direction: MessageDirection

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "time_str": datetime.fromtimestamp(self.timestamp).isoformat(),
            "address": self.address,
            "args": self.args,
            "direction": self.direction.name,
        }


class OSCInspector:
    """OSC Message Inspector for monitoring and debugging OSC traffic."""

    def __init__(
        self,
        server_ip: str = "127.0.0.1",
        server_port: int = 9001,
        client_ip: str = "127.0.0.1",
        client_port: int = 9000,
        max_history: int = 1000,
    ):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_ip = client_ip
        self.client_port = client_port
        self.max_history = max_history

        self.message_history: list[MessageRecord] = []
        self.message_count = 0
        self.bytes_received = 0
        self.bytes_sent = 0

        self.osc_client: SimpleUDPClient | None = None
        self.osc_server: AsyncIOOSCUDPServer | None = None
        self.dispatcher = Dispatcher()
        self.dispatcher.set_default_handler(self._handle_osc_message)

    async def start(self) -> None:
        """Start the OSC message inspector."""
        if self.osc_server is not None:
            return

        self.osc_client = SimpleUDPClient(self.client_ip, self.client_port)

        loop = asyncio.get_running_loop()
        _, protocol = await loop.create_datagram_endpoint(
            lambda: AsyncIOOSCUDPServer((self.server_ip, self.server_port), self.dispatcher, loop),
            local_addr=(self.server_ip, self.server_port),
        )

        self.osc_server = protocol
        logger.info(f"OSC Inspector listening on {self.server_ip}:{self.server_port}")

    async def stop(self) -> None:
        """Stop the OSC message inspector."""
        if self.osc_server:
            self.osc_server.close()
            await self.osc_server.wait_closed()
            self.osc_server = None
        self.osc_client = None
        logger.info("OSC Inspector stopped")

    def _handle_osc_message(self, address: str, *args: Any) -> None:
        """Handle an incoming OSC message."""
        if not address:
            return

        record = MessageRecord(
            timestamp=time.time(), address=address, args=list(args), direction=MessageDirection.INCOMING
        )

        self._add_to_history(record)
        self.message_count += 1
        self.bytes_received += len(address) + sum(len(str(arg)) for arg in args)

    def send_message(self, address: str, *args: Any) -> None:
        """Send an OSC message."""
        if not self.osc_client:
            logger.warning("OSC client not initialized")
            return

        self.osc_client.send_message(address, args)

        record = MessageRecord(
            timestamp=time.time(), address=address, args=list(args), direction=MessageDirection.OUTGOING
        )

        self._add_to_history(record)
        self.bytes_sent += len(address) + sum(len(str(arg)) for arg in args)

    def _add_to_history(self, record: MessageRecord) -> None:
        """Add a message to history, respecting max_history."""
        self.message_history.append(record)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)

    def get_statistics(self) -> dict[str, Any]:
        """Get message statistics."""
        return {
            "total_messages": self.message_count,
            "history_size": len(self.message_history),
            "bytes_received": self.bytes_received,
            "bytes_sent": self.bytes_sent,
        }

    def get_message_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent message history."""
        return [m.to_dict() for m in self.message_history[-limit:]]

    async def record_messages(self, duration: float, output_file: str | Path | None = None) -> list[dict[str, Any]]:
        """Record messages for a specified duration."""
        start_time = time.time()
        start_count = self.message_count

        while time.time() - start_time < duration:
            await asyncio.sleep(0.1)

        recorded = self.message_history[start_count - self.message_count :]

        if output_file:
            with open(output_file, "w") as f:
                json.dump([m.to_dict() for m in recorded], f, indent=2)

        return [m.to_dict() for m in recorded]

    def filter_messages(
        self,
        address_pattern: str = r".*",
        direction: MessageDirection | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> list[dict[str, Any]]:
        """Filter messages by criteria."""
        pattern = re.compile(address_pattern)

        def matches(record: MessageRecord) -> bool:
            if not pattern.search(record.address):
                return False

            if direction is not None and record.direction != direction:
                return False

            if min_value is not None or max_value is not None:
                for arg in record.args:
                    if isinstance(arg, (int, float)):
                        if min_value is not None and arg < min_value:
                            return False
                        if max_value is not None and arg > max_value:
                            return False
            return True

        return [m.to_dict() for m in filter(matches, self.message_history)]
