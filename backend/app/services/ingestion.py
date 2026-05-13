"""Environmental data ingestion orchestration.

This module aggregates connectors (Open-Meteo, OpenAQ, NASA POWER, climate
archive) into a single JSON document persisted in ``environmental_readings``.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.alerting import ApiFetchLog, EnvironmentalReading
from app.services.connectors import (
    climate_context,
    gee_bridge,
    nasa_power,
    open_meteo,
    openaq,
    openweather,
    sentinel_hub,
)

log = logging.getLogger(__name__)


def _log_fetch(db: Session, source: str, success: bool, http_status: int | None, message: str | None) -> None:
    db.add(ApiFetchLog(source=source, success=success, http_status=http_status, message=message))


def fetch_and_store_reading(db: Session) -> EnvironmentalReading:
    """Pull all enabled sources, merge payloads, persist a reading + logs."""
    settings = get_settings()
    lat, lon = settings.default_lat, settings.default_lon
    merged: dict[str, Any] = {"fetched_at": datetime.now(tz=UTC).isoformat()}

    # Open-Meteo (required baseline)
    try:
        merged.update(open_meteo.fetch_open_meteo_bundle(lat, lon))
        _log_fetch(db, "open_meteo", True, 200, None)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        log.exception("Open-Meteo ingestion failed")
        _log_fetch(db, "open_meteo", False, None, str(exc))
        merged.setdefault("weather", {})
        merged.setdefault("air_quality", {})

    # Optional OpenWeatherMap
    try:
        ow = openweather.fetch_openweather_current(lat, lon)
        if ow:
            merged.update(ow)
            _log_fetch(db, "openweather", True, 200, None)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        _log_fetch(db, "openweather", False, None, str(exc))

    # OpenAQ (best-effort)
    try:
        oa = openaq.fetch_openaq_latest(lat, lon)
        if oa:
            merged["openaq"] = oa["openaq"]
            _log_fetch(db, "openaq", True, 200, None)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        _log_fetch(db, "openaq", False, None, str(exc))

    # NASA POWER
    try:
        np = nasa_power.fetch_nasa_power_daily_precip(lat, lon)
        if np:
            merged["nasa_power"] = np["nasa_power"]
            _log_fetch(db, "nasa_power", True, 200, None)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        _log_fetch(db, "nasa_power", False, None, str(exc))

    # Climate archive (Open-Meteo Climate API)
    try:
        cl = climate_context.fetch_climate_precip_series(lat, lon)
        merged["climate"] = cl["climate"]
        _log_fetch(db, "open_meteo_climate", True, 200, None)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        _log_fetch(db, "open_meteo_climate", False, None, str(exc))

    # Optional Sentinel Hub (Copernicus) STAC context (never raises)
    merged["sentinel_hub"] = sentinel_hub.fetch_sentinel_hub_context(lat, lon)
    sh_ok = merged["sentinel_hub"].get("error") is None
    _log_fetch(db, "sentinel_hub", sh_ok, 200 if sh_ok else None, merged["sentinel_hub"].get("error"))

    # Optional Earth Engine bridge (HTTP sidecar; never raises)
    merged["earth_engine"] = gee_bridge.fetch_earth_engine_bridge(lat, lon)
    gee_ok = merged["earth_engine"].get("error") is None
    _log_fetch(db, "earth_engine_bridge", gee_ok, 200 if gee_ok else None, merged["earth_engine"].get("error"))

    row = EnvironmentalReading(
        observed_at=datetime.now(tz=UTC),
        source="aggregate",
        lat=lat,
        lon=lon,
        payload=merged,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
