"""Climate archive context (Open-Meteo Climate API) — CHIRPS/CAMS-style situational awareness.

The Climate API aggregates multiple reanalysis/ensemble sources; we use it to
estimate recent accumulated precipitation for flood heuristics when radar is
unavailable. Sentinel Hub / Google Earth Engine can replace this layer later
without changing the risk engine interface.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

CLIMATE_API = "https://climate-api.open-meteo.com/v1/climate"


def fetch_climate_precip_series(lat: float, lon: float) -> dict[str, Any]:
    end = datetime.now(tz=UTC).date()
    start = end - timedelta(days=14)
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "models": "EC_Earth3_ensemble",
        "daily": "precipitation_sum",
        "timezone": "Africa/Lubumbashi",
    }
    with httpx.Client(timeout=45.0) as client:
        r = client.get(CLIMATE_API, params=params)
        r.raise_for_status()
    return {"climate": r.json(), "provider": "open_meteo_climate"}
