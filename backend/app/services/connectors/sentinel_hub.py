"""Optional Sentinel Hub / Copernicus integration (OAuth2 + STAC catalog search).

This connector is intentionally defensive: if credentials are missing or the
upstream API changes, failures are captured in the merged payload under
``sentinel_hub`` without breaking ingestion.

Official references:
- Sentinel Hub documentation (OAuth2 client credentials, Catalog API)
- STAC search endpoint on ``services.sentinel-hub.com``
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.config import get_settings


def _oauth_token(base: str, client_id: str, client_secret: str) -> str:
    url = f"{base.rstrip('/')}/oauth/token"
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        r.raise_for_status()
        return str(r.json()["access_token"])


def fetch_sentinel_hub_context(lat: float, lon: float) -> dict[str, Any]:
    """Return a JSON-serializable object suitable for ``environmental_readings.payload``."""
    settings = get_settings()
    if not settings.sentinel_hub_enabled:
        return {
            "configured": False,
            "note": "Enable with SENTINEL_HUB_ENABLED=true and OAuth client credentials.",
        }

    cid = settings.sentinel_hub_client_id.strip()
    csec = settings.sentinel_hub_client_secret.strip()
    base = settings.sentinel_hub_base_url.rstrip("/")
    if not cid or not csec:
        return {"configured": False, "error": "Missing SENTINEL_HUB_CLIENT_ID / SENTINEL_HUB_CLIENT_SECRET"}

    try:
        token = _oauth_token(base, cid, csec)
        end = datetime.now(tz=UTC)
        start = end - timedelta(days=14)
        # Small bbox around the city centroid (degrees)
        pad = 0.06
        bbox = [lon - pad, lat - pad, lon + pad, lat + pad]
        body = {
            "bbox": bbox,
            "datetime": f"{start.isoformat()}/{end.isoformat()}",
            "collections": ["sentinel-2-l2a"],
            "limit": 5,
        }
        search_url = f"{base}/api/v1/catalog/1.0.0/search"
        with httpx.Client(timeout=45.0) as client:
            r = client.post(
                search_url,
                json=body,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
            r.raise_for_status()
            data = r.json()
        return {
            "configured": True,
            "provider": "sentinel_hub",
            "stac": data,
        }
    except Exception as exc:  # noqa: BLE001 — must never break ingestion
        return {"configured": True, "provider": "sentinel_hub", "error": str(exc)[:2000]}
