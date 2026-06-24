"""WebSocket endpoint that streams generation progress to the frontend."""
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/progress")
async def ws_progress(ws: WebSocket) -> None:
    """Client connects here to receive {type:'progress', value, max, pct} events.
    Inbound messages are ignored — the socket exists only to keep the connection open.
    """
    from app.deps import progress_hub
    await progress_hub.register(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        progress_hub.unregister(ws)
