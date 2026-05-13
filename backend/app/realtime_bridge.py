"""Redis pub/sub bridge so Celery workers can signal live dashboard clients.

The FastAPI process subscribes to ``clima:events`` and forwards JSON payloads to
connected WebSocket clients. This keeps the system horizontally scalable: any
publisher (worker, admin script) can trigger UI refreshes without sharing memory.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.config import get_settings
from app.websocket_manager import manager

log = logging.getLogger(__name__)
CHANNEL = "clima:events"


async def redis_subscriber_loop() -> None:
    """Background task: listen for ingestion/risk events and broadcast to WS."""
    settings = get_settings()
    backoff = 1.0
    while True:
        try:
            client = aioredis.from_url(settings.redis_url, decode_responses=True)
            pubsub = client.pubsub()
            await pubsub.subscribe(CHANNEL)
            backoff = 1.0
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                data = message.get("data")
                if not data:
                    continue
                try:
                    payload: dict[str, Any] = json.loads(data)
                except json.JSONDecodeError:
                    continue
                await manager.broadcast_json(payload)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            log.warning("Redis subscriber error: %s — retrying", exc)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30.0)


def publish_event(payload: dict[str, Any]) -> None:
    """Synchronous publish for Celery tasks."""
    settings = get_settings()
    if not settings.use_redis:
        return

    import redis as redis_sync

    client = redis_sync.Redis.from_url(settings.redis_url)
    client.publish(CHANNEL, json.dumps(payload, default=str))
