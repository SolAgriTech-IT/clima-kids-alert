"""Optional OpenWeatherMap enrichment (requires OPENWEATHERMAP_API_KEY).

Used when a key is configured; otherwise skipped by the ingestion pipeline.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings


def fetch_openweather_current(lat: float, lon: float) -> dict[str, Any] | None:
    settings = get_settings()
    key = settings.openweathermap_api_key.strip()
    if not key:
        return None
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": key, "units": "metric"}
    with httpx.Client(timeout=30.0) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
    return {"openweather": r.json(), "provider": "openweather"}
