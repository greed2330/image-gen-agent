"""Fan-out hub for generation progress events.

Single-user local app: at most one generation runs at a time, so progress is
broadcast to every connected client rather than routed per-request.
"""
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ProgressHub:
    def __init__(self) -> None:
        self._sockets: set[WebSocket] = set()

    async def register(self, ws: WebSocket) -> None:
        await ws.accept()
        self._sockets.add(ws)
        logger.info("progress_hub: client connected (%d total)", len(self._sockets))

    def unregister(self, ws: WebSocket) -> None:
        self._sockets.discard(ws)
        logger.info("progress_hub: client disconnected (%d total)", len(self._sockets))

    async def broadcast(self, message: dict) -> None:
        """Send a JSON message to all connected clients; drop any that fail."""
        dead: list[WebSocket] = []
        for ws in self._sockets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._sockets.discard(ws)
