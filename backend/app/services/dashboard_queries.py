"""Read-model helpers for dashboard KPIs and tables."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.alerting import Alert, Notification, NotificationStatus, RiskSeverity, ZoneRiskScore
from app.models.geo import HealthCenter, School, Zone


def _latest_scores(db: Session) -> dict[int, ZoneRiskScore]:
    rows = db.execute(select(ZoneRiskScore).order_by(ZoneRiskScore.computed_at.desc())).scalars().all()
    best: dict[int, ZoneRiskScore] = {}
    for r in rows:
        best.setdefault(r.zone_id, r)
    return best


def build_dashboard_summary(db: Session) -> dict[str, Any]:
    latest = _latest_scores(db)
    high_risk = sum(1 for r in latest.values() if r.severity in (RiskSeverity.high, RiskSeverity.critical))

    schools = db.execute(select(func.count(School.id))).scalar_one()
    centers = db.execute(select(func.count(HealthCenter.id))).scalar_one()

    exposed_schools = 0
    children = 0
    for sid, zr in latest.items():
        if zr.severity in (RiskSeverity.high, RiskSeverity.critical):
            cnt = db.execute(select(func.count(School.id)).where(School.zone_id == sid)).scalar_one()
            exposed_schools += int(cnt or 0)
            total_students = db.execute(
                select(func.coalesce(func.sum(School.student_count_estimate), 0)).where(School.zone_id == sid),
            ).scalar_one()
            children += int(total_students or 0)

    start_day = datetime.now(tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    alerts_today = db.execute(select(func.count(Alert.id)).where(Alert.created_at >= start_day)).scalar_one()

    notif_today = db.execute(select(Notification).where(Notification.created_at >= start_day)).scalars().all()
    sent = sum(1 for n in notif_today if n.status == NotificationStatus.sent)
    failed = sum(1 for n in notif_today if n.status == NotificationStatus.failed)
    denom = sent + failed
    reception = int(round(100 * sent / denom)) if denom else 0

    sev_rank = {RiskSeverity.low: 0, RiskSeverity.moderate: 1, RiskSeverity.high: 2, RiskSeverity.critical: 3}
    worst = RiskSeverity.low
    for r in latest.values():
        if sev_rank[r.severity] > sev_rank[worst]:
            worst = r.severity

    return {
        "high_risk_zones": high_risk,
        "schools_exposed": exposed_schools,
        "health_centers": int(centers),
        "children_potentially_exposed": children,
        "alerts_sent_today": int(alerts_today),
        "reception_rate_percent": reception,
        "global_severity": worst.value,
        "updated_at": datetime.now(tz=UTC),
    }


def build_risk_cards(db: Session) -> dict[str, Any]:
    """Map latest Open-Meteo-derived signals to the three French UI cards."""
    from app.models.alerting import EnvironmentalReading

    row = db.execute(select(EnvironmentalReading).order_by(EnvironmentalReading.observed_at.desc())).scalars().first()
    payload: dict[str, Any] = row.payload if row else {}
    w = (payload.get("weather") or {}).get("current") or {}
    aq = (payload.get("air_quality") or {}).get("current") or {}
    temp = w.get("temperature_2m")
    rain = w.get("precipitation") or w.get("rain") or 0
    pm10 = aq.get("pm10")

    def sev_pm(v: float | None) -> tuple[str, str]:
        if v is None:
            return "Modéré", "Données limitées : surveillez les enfants près des axes poussiéreux."
        if v >= 150:
            return "Élevé", "Limitez l'exposition, protégez les enfants asthmatiques."
        if v >= 100:
            return "Élevé", "Limitez l'exposition, protégez les enfants asthmatiques."
        if v >= 50:
            return "Modéré", "Surveillance recommandée près des zones minières et des routes non revêtues."
        return "Faible", "La qualité de l'air semble acceptable sur les indicateurs disponibles."

    def sev_heat(t: float | None) -> tuple[str, str]:
        if t is None:
            return "Modéré", "Hydratez les enfants et évitez le soleil entre 11h et 15h."
        if t >= 34:
            return "Élevé", "Hydratez les enfants, évitez le soleil entre 11h et 15h."
        if t <= 18:
            return "Modéré", "Conditions modérées : adaptez les vêtements des enfants."
        return "Faible", "Conditions thermiques globalement favorables."

    def sev_rain(mm: float) -> tuple[str, str]:
        if mm >= 12:
            return "Élevé", "Évitez les eaux stagnantes, protégez l'eau potable."
        if mm >= 4:
            return "Modéré", "Pluie notable : restez attentif aux zones inondables."
        return "Faible", "Pas de pluie intense immédiate signalée."

    pm_sev, pm_advice = sev_pm(float(pm10) if pm10 is not None else None)
    ht_sev, ht_advice = sev_heat(float(temp) if temp is not None else None)
    rn_sev, rn_advice = sev_rain(float(rain or 0))

    return {
        "heat": {
            "title": "Chaleur extrême",
            "value": f"{float(temp):.0f} °C" if temp is not None else "—",
            "severity": ht_sev,
            "advice": ht_advice,
        },
        "dust": {
            "title": "Poussière / pollution",
            "value": f"PM10 {float(pm10):.0f} µg/m³" if pm10 is not None else "PM10 —",
            "severity": pm_sev,
            "advice": pm_advice,
        },
        "rain": {
            "title": "Pluie / inondation",
            "value": f"{float(rain):.1f} mm (instantané)",
            "severity": rn_sev,
            "advice": rn_advice,
        },
    }


def build_zone_score_rows(db: Session) -> list[dict[str, Any]]:
    latest = _latest_scores(db)
    rows: list[dict[str, Any]] = []
    for z in db.execute(select(Zone)).scalars().all():
        zr = latest.get(z.id)
        score = int(zr.score) if zr else 0
        level = zr.severity.value if zr else "low"
        fr_level = {
            "low": "Faible",
            "moderate": "Modéré",
            "high": "Élevé",
            "critical": "Critique",
        }.get(level, level)
        action = {
            "low": "Surveillance habituelle",
            "moderate": "Informer les parents",
            "high": "Renforcer la prévention",
            "critical": "Alerte immédiate",
        }.get(level, "Surveillance")
        rows.append({"zone": z.name, "score": score, "level": fr_level, "action": action})
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows


def build_recent_alerts(db: Session, limit: int = 12) -> list[dict[str, Any]]:
    alerts = (
        db.execute(select(Alert).order_by(Alert.created_at.desc()).limit(limit)).scalars().all()
    )
    out: list[dict[str, Any]] = []
    for a in alerts:
        zone_name = "Kolwezi"
        if a.zone_id:
            z = db.get(Zone, a.zone_id)
            if z:
                zone_name = z.name
        # Channel summary from notifications
        chans = db.execute(select(Notification).where(Notification.alert_id == a.id)).scalars().all()
        uniq = sorted({n.channel.value for n in chans}) if chans else ["système"]
        channel_fr = ", ".join(
            {"email": "Email", "sms": "SMS", "whatsapp": "WhatsApp"}.get(c, c) for c in uniq
        )
        status = "Envoyé" if any(n.status == NotificationStatus.sent for n in chans) else "En attente"
        out.append(
            {
                "date": a.created_at.astimezone(UTC).strftime("%d/%m/%Y %H:%M"),
                "zone": zone_name,
                "risk": a.title_fr,
                "channel": channel_fr,
                "status": status,
            },
        )
    return out


def zones_geojson(db: Session) -> dict[str, Any]:
    """GeoJSON FeatureCollection for Leaflet with latest risk score properties."""
    from geoalchemy2.functions import ST_AsGeoJSON

    latest = _latest_scores(db)
    feats: list[dict[str, Any]] = []
    for z in db.execute(select(Zone)).scalars().all():
        gj = db.scalar(select(ST_AsGeoJSON(z.geom)))
        zr = latest.get(z.id)
        props = {
            "slug": z.slug,
            "name": z.name,
            "score": int(zr.score) if zr else None,
            "severity": zr.severity.value if zr else None,
        }
        import json

        geom = json.loads(gj) if isinstance(gj, str) else gj
        feats.append({"type": "Feature", "geometry": geom, "properties": props})
    return {"type": "FeatureCollection", "features": feats}
