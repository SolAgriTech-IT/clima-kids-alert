"""Shared SlowAPI limiter instance.

By default SlowAPI uses in-memory counters (fine for a single process). For
multi-replica deployments, set ``RATE_LIMIT_STORAGE_URI`` to a Redis DSN so every
API instance shares the same counters.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings


def _build_limiter() -> Limiter:
    settings = get_settings()
    uri = (settings.rate_limit_storage_uri or "").strip()
    if uri:
        return Limiter(key_func=get_remote_address, storage_uri=uri)
    return Limiter(key_func=get_remote_address)


limiter = _build_limiter()
