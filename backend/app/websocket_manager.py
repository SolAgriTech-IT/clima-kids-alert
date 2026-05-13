"""In-memory WebSocket hub for broadcasting dashboard events.

For horizontal scaling, replace the broadcast implementation with a Redis pub/sub
fan-out so every API replica receives the same events.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState


class ConnectionManager:
    """Tracks active dashboard WebSocket clients."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def register(self, websocket: WebSocket) -> None:
        """Register an already-accepted WebSocket client."""
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast_json(self, payload: dict[str, Any]) -> None:
        """Send JSON to all connected clients; prune dead sockets."""
        text = json.dumps(payload, default=str)
        async with self._lock:
            targets = list(self._connections)
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(text)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.discard(ws)


manager = ConnectionManager()
