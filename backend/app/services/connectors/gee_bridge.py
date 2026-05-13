"""Optional Google Earth Engine integration via a small HTTP sidecar.

Running the full Earth Engine Python client inside the API container is possible
but heavy (extra native deps, service accounts, batching). For production
systems, a common pattern is a dedicated **GEE bridge** service that executes
Earth Engine computations and exposes a narrow HTTP API.

This connector POSTs ``{"lat","lon","requested_at"}`` to ``GEE_BRIDGE_URL`` and
merges the JSON response under ``earth_engine`` in ``environmental_readings.payload``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from app.config import get_settings


def fetch_earth_engine_bridge(lat: float, lon: float) -> dict[str, Any]:
    settings = get_settings()
    url = settings.gee_bridge_url.strip()
    if not url:
        return {
            "configured": False,
            "note": "Set GEE_BRIDGE_URL to a trusted internal service that returns JSON summaries.",
        }

    headers: dict[str, str] = {"Content-Type": "application/json"}
    token = settings.gee_bridge_token.strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {"lat": lat, "lon": lon, "requested_at": datetime.now(tz=UTC).isoformat()}
    try:
        with httpx.Client(timeout=45.0) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        if not isinstance(data, dict):
            return {"configured": True, "provider": "earth_engine_bridge", "error": "Bridge returned non-object JSON"}
        return {"configured": True, "provider": "earth_engine_bridge", "data": data}
    except Exception as exc:  # noqa: BLE001
        return {"configured": True, "provider": "earth_engine_bridge", "error": str(exc)[:2000]}
