"""
VRChat Pipeline Client: SOTA Industrial v14.1.0

Websocket client for real-time VRChat notifications (Invites, Friends, Notifications).
Implements the VRChat "Pipeline" protocol with automatic reconnection and async event dispatching.
"""

import asyncio
import json
import logging
from collections import deque
from collections.abc import Callable
from datetime import UTC, datetime

import websockets

logger = logging.getLogger(__name__)

_MAX_RECENT_EVENTS = 50
_MAX_RECONNECT_ATTEMPTS = 5


class PipelineClient:
    def __init__(self, auth_cookie: str = ""):
        self.auth_cookie = auth_cookie
        self.url = "wss://pipeline.vrchat.cloud/?authToken="
        self.ws = None
        self.handlers: dict[str, list[Callable]] = {}
        self.is_running = False
        self._background_tasks: set[asyncio.Task] = set()
        self._auth_token: str = ""
        self._reconnect_attempts = 0
        # Bounded event history so anything received with no registered handler is still
        # queryable (get_recent_events()) instead of being silently dropped after a debug
        # log line - fixed 2026-09-03, nothing previously read from `handlers` unless a
        # caller had registered one via on() before the event arrived.
        self.recent_events: deque[dict] = deque(maxlen=_MAX_RECENT_EVENTS)

    def on(self, event_type: str, callback: Callable):
        """Register an event handler."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(callback)

    def get_recent_events(self, event_type: str | None = None, limit: int = 20) -> list[dict]:
        """Return the most recent received events, newest first. Works even with zero
        registered handlers - this is the buffer everything lands in regardless."""
        events = list(self.recent_events)
        if event_type:
            events = [e for e in events if e.get("type") == event_type]
        return list(reversed(events))[:limit]

    async def connect(self, auth_token: str):
        """Connect to the pipeline websocket."""
        self._auth_token = auth_token
        try:
            full_url = f"{self.url}{auth_token}"
            logger.info("Connecting to VRChat Pipeline...")
            self.ws = await websockets.connect(full_url)
            self.is_running = True
            self._reconnect_attempts = 0
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

                self.recent_events.append(
                    {"type": event_type, "received_at": datetime.now(UTC).isoformat(), **data}
                )

                if event_type in self.handlers:
                    for handler in self.handlers[event_type]:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(data)
                        else:
                            handler(data)

                logger.debug(f"Pipeline Event: {event_type}")

            except websockets.ConnectionClosed:
                # Fixed 2026-09-03: this used to log "Reconnecting..." and then just give up
                # (is_running = False; break) - the log line promised behavior the code never
                # did. Now actually attempts reconnection, bounded, with backoff.
                logger.warning("Pipeline connection closed.")
                if not await self._attempt_reconnect():
                    self.is_running = False
                    break
            except Exception as e:
                logger.error(f"Error in Pipeline loop: {e}")
                await asyncio.sleep(5)

    async def _attempt_reconnect(self) -> bool:
        """Bounded reconnect with linear backoff. Returns True once `self.ws` has been
        replaced with a live connection - the same _listen_loop task's `while self.is_running`
        loop then just continues with the new socket, no new task needed. Recurses on failure
        up to _MAX_RECONNECT_ATTEMPTS."""
        if self._reconnect_attempts >= _MAX_RECONNECT_ATTEMPTS or not self._auth_token:
            logger.error("Pipeline reconnect abandoned after %d attempts.", self._reconnect_attempts)
            return False

        self._reconnect_attempts += 1
        delay = min(self._reconnect_attempts * 2, 10)
        logger.info(
            "Pipeline reconnect attempt %d/%d in %ds...", self._reconnect_attempts, _MAX_RECONNECT_ATTEMPTS, delay
        )
        await asyncio.sleep(delay)

        try:
            full_url = f"{self.url}{self._auth_token}"
            self.ws = await websockets.connect(full_url)
            logger.info("Pipeline reconnected.")
            self._reconnect_attempts = 0
            return True
        except Exception as e:
            logger.error(f"Pipeline reconnect attempt failed: {e}")
            return await self._attempt_reconnect()

    async def disconnect(self):
        """Gracefully disconnect."""
        self.is_running = False
        self._auth_token = ""
        if self.ws:
            await self.ws.close()
            logger.info("Disconnected from Pipeline.")
