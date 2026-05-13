"""Open-Meteo weather and air-quality ingestion (no API key required).

Documentation: https://open-meteo.com/en/docs
"""

from __future__ import annotations

from typing import Any

import httpx

OPEN_METEO_WEATHER = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_AIR = "https://air-quality-api.open-meteo.com/v1/air-quality"


def fetch_open_meteo_bundle(lat: float, lon: float) -> dict[str, Any]:
    """Return merged current weather + air quality payloads for a point."""
    params_weather = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "rain",
            "showers",
            "weather_code",
            "cloud_cover",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
        ],
        "wind_speed_unit": "kmh",
        "timezone": "Africa/Lubumbashi",
    }
    params_air = {
        "latitude": lat,
        "longitude": lon,
        "current": ["pm10", "pm2_5", "carbon_monoxide", "nitrogen_dioxide", "ozone"],
        "timezone": "Africa/Lubumbashi",
    }
    with httpx.Client(timeout=30.0) as client:
        w = client.get(OPEN_METEO_WEATHER, params=params_weather)
        w.raise_for_status()
        a = client.get(OPEN_METEO_AIR, params=params_air)
        a.raise_for_status()
    return {
        "weather": w.json(),
        "air_quality": a.json(),
        "provider": "open_meteo",
    }
