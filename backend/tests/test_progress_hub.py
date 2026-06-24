"""Tests for ProgressHub fan-out (WebSockets mocked)."""
import pytest
from unittest.mock import AsyncMock

from app.services.progress_hub import ProgressHub


@pytest.mark.asyncio
async def test_register_accepts_and_broadcasts():
    hub = ProgressHub()
    ws = AsyncMock()
    await hub.register(ws)
    ws.accept.assert_awaited_once()

    await hub.broadcast({"type": "progress", "pct": 50})
    ws.send_json.assert_awaited_once_with({"type": "progress", "pct": 50})


@pytest.mark.asyncio
async def test_unregister_stops_delivery():
    hub = ProgressHub()
    ws = AsyncMock()
    await hub.register(ws)
    hub.unregister(ws)

    await hub.broadcast({"pct": 10})
    ws.send_json.assert_not_awaited()


@pytest.mark.asyncio
async def test_broadcast_drops_failed_socket():
    hub = ProgressHub()
    good, bad = AsyncMock(), AsyncMock()
    bad.send_json.side_effect = RuntimeError("closed")
    await hub.register(good)
    await hub.register(bad)

    await hub.broadcast({"pct": 1})       # bad raises → dropped
    await hub.broadcast({"pct": 2})       # only good remains
    assert good.send_json.await_count == 2
    assert bad.send_json.await_count == 1
