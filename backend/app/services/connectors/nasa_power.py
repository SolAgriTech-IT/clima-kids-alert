"""NASA POWER daily precipitation context (public API, no key).

Used as a complementary rainfall signal alongside Open-Meteo nowcasts.
Docs: https://power.larc.nasa.gov/docs/services/api/
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.config import get_settings


def fetch_nasa_power_daily_precip(lat: float, lon: float) -> dict[str, Any] | None:
    settings = get_settings()
    if not settings.nasa_power_enabled:
        return None
    end = datetime.now(tz=UTC).date()
    start = end - timedelta(days=3)
    fmt = "%Y%m%d"
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        "parameters": "PRECTOTCORR",
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "start": start.strftime(fmt),
        "end": end.strftime(fmt),
        "format": "JSON",
    }
    with httpx.Client(timeout=45.0) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
    return {"nasa_power": r.json(), "provider": "nasa_power"}
