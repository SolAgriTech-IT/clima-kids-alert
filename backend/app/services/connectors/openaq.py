"""OpenAQ v2 latest measurements near Kolwezi (optional API token).

Docs: https://docs.openaq.org/
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings


def fetch_openaq_latest(lat: float, lon: float) -> dict[str, Any] | None:
    settings = get_settings()
    headers: dict[str, str] = {}
    token = settings.openaq_api_key.strip()
    if token:
        headers["X-API-Key"] = token
    url = "https://api.openaq.org/v2/latest"
    params = {"coordinates": f"{lat},{lon}", "radius": 50000, "limit": 10}
    with httpx.Client(timeout=30.0, headers=headers) as client:
        r = client.get(url, params=params)
        if r.status_code >= 400:
            r.raise_for_status()
        data = r.json()
    return {"openaq": data, "provider": "openaq"}
