"""
VRChat Pipeline Client: SOTA Industrial v14.1.0

Websocket client for real-time VRChat notifications (Invites, Friends, Notifications).
Implements the VRChat "Pipeline" protocol with automatic reconnection and async event dispatching.
"""

import asyncio
import json
import logging
from collections.abc import Callable

import websockets

logger = logging.getLogger(__name__)

class PipelineClient:
    def __init__(self, auth_cookie: str = ""):
        self.auth_cookie = auth_cookie
        self.url = "wss://pipeline.vrchat.cloud/?authToken="
        self.ws = None
        self.handlers: dict[str, list[Callable]] = {}
        self.is_running = False
        self._background_tasks: set[asyncio.Task] = set()

    def on(self, event_type: str, callback: Callable):
        """Register an event handler."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(callback)

    async def connect(self, auth_token: str):
        """Connect to the pipeline websocket."""
        try:
            full_url = f"{self.url}{auth_token}"
            logger.info("Connecting to VRChat Pipeline...")
            self.ws = await websockets.connect(full_url)
            self.is_running = True
            task = asyncio.create_task(self._listen_loop())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
            logger.info("Successfully connected to Pipeline.")
        except Exception as e:
            logger.error(f"Failed to connect to Pipeline: {e}")
            self.is_running = False

    async def _listen_loop(self):
        """Main listening loop for websocket messages."""
        while self.is_running:
            try:
                message = await self.ws.recv()
                data = json.loads(message)
                event_type = data.get("type")

                if event_type in self.handlers:
                    for handler in self.handlers[event_type]:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(data)
                        else:
                            handler(data)

                logger.debug(f"Pipeline Event: {event_type}")

            except websockets.ConnectionClosed:
                logger.warning("Pipeline connection closed. Reconnecting...")
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"Error in Pipeline loop: {e}")
                await asyncio.sleep(5)

    async def disconnect(self):
        """Gracefully disconnect."""
        self.is_running = False
        if self.ws:
            await self.ws.close()
            logger.info("Disconnected from Pipeline.")
