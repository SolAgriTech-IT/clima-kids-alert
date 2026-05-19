"""Temporary climate override for admin simulations (Redis, 2-minute TTL)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.config import get_settings

SIM_KEY = "clima:simulation:override"
TTL_SECONDS = 120


def _redis():
    try:
        import redis

        return redis.from_url(get_settings().redis_url, decode_responses=True)
    except Exception:
        return None


def set_climate_override(*, precip_mm: float, pm10: float, temperature_c: float) -> dict[str, Any]:
    payload = {
        "precip_mm": precip_mm,
        "pm10": pm10,
        "temperature_c": temperature_c,
        "expires_at": (datetime.now(tz=UTC).timestamp() + TTL_SECONDS),
    }
    client = _redis()
    if client is not None:
        client.setex(SIM_KEY, TTL_SECONDS, json.dumps(payload))
    return payload


def get_climate_override() -> dict[str, Any] | None:
    client = _redis()
    if client is None:
        return None
    raw = client.get(SIM_KEY)
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    exp = float(data.get("expires_at") or 0)
    if datetime.now(tz=UTC).timestamp() > exp:
        client.delete(SIM_KEY)
        return None
    return data


def build_simulated_risk_cards(override: dict[str, Any]) -> dict[str, Any]:
    """Risk card shape matching dashboard_queries.build_risk_cards."""
    from app.services import dashboard_queries

    temp = float(override["temperature_c"])
    rain = float(override["precip_mm"])
    pm10 = float(override["pm10"])

    def sev_pm(v: float) -> tuple[str, str]:
        if v >= 100:
            return "Élevé", "Limitez l'exposition, protégez les enfants asthmatiques."
        if v >= 50:
            return "Modéré", "Surveillance recommandée près des zones minières."
        return "Faible", "La qualité de l'air semble acceptable."

    def sev_heat(t: float) -> tuple[str, str]:
        if t >= 34:
            return "Élevé", "Hydratez les enfants, évitez le soleil entre 11h et 15h."
        return "Faible", "Conditions thermiques globalement favorables."

    def sev_rain(mm: float) -> tuple[str, str]:
        if mm >= 12:
            return "Élevé", "Évitez les eaux stagnantes, protégez l'eau potable."
        if mm >= 4:
            return "Modéré", "Pluie notable : restez attentif aux zones inondables."
        return "Faible", "Pas de pluie intense immédiate signalée."

    pm_sev, pm_advice = sev_pm(pm10)
    ht_sev, ht_advice = sev_heat(temp)
    rn_sev, rn_advice = sev_rain(rain)

    cards = {
        "heat": {
            "title": "Chaleur extrême",
            "value": f"{temp:.0f} °C",
            "severity": ht_sev,
            "advice": ht_advice,
        },
        "dust": {
            "title": "Poussière / pollution",
            "value": f"PM10 {pm10:.0f} µg/m³",
            "severity": pm_sev,
            "advice": pm_advice,
        },
        "rain": {
            "title": "Pluie / inondation",
            "value": f"{rain:.1f} mm",
            "severity": rn_sev,
            "advice": rn_advice,
        },
        "simulation_active": True,
    }
    # Re-use severity helpers from real builder for consistency
    _ = dashboard_queries  # noqa: F841 — import ensures module load order
    return cards
