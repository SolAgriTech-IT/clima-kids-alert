"""Child health risk engine for Kolwezi-scale deployments (generic inputs).

The engine consumes a merged environmental payload produced by the ingestion
layer and emits per-zone scores plus structured factors for visualization.

Thresholds reference widely used public-health guardrails (WHO air-quality
interim targets for PM, UNICEF-style heat/cold child protection messaging).
Local calibration (mining dust, unpaved roads) is applied via configurable
spatial hazard overlays stored in PostGIS.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Sequence

from geoalchemy2.functions import ST_Contains, ST_Intersects, ST_MakePoint, ST_SetSRID
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.alerting import (
    Alert,
    AlertCooldownState,
    Notification,
    NotificationChannel,
    NotificationStatus,
    RiskSeverity,
    RiskType,
    ZoneRiskScore,
)
from app.models.geo import HazardArea
from app.models.geo import HazardKind, School, Zone
from app.models.subscriber import AlertSubscriber
from app.models.user import User
from app.realtime_bridge import publish_event


@dataclass
class EnvSignals:
    temperature_c: float | None
    precip_mm_h: float | None
    wind_kmh: float | None
    pm10: float | None
    pm25: float | None
    precip_sum_7d_mm: float | None


def parse_signals(payload: dict[str, Any]) -> EnvSignals:
    """Normalize heterogeneous provider JSON into comparable scalars."""
    temp = precip = wind = pm10 = pm25 = None
    w = payload.get("weather") or {}
    cur_w = w.get("current") or {}
    if cur_w:
        temp = cur_w.get("temperature_2m")
        precip = cur_w.get("precipitation") or cur_w.get("rain") or 0.0
        wind = cur_w.get("wind_speed_10m") or cur_w.get("wind_gusts_10m")

    aq = payload.get("air_quality") or {}
    cur_a = aq.get("current") or {}
    if cur_a:
        pm10 = cur_a.get("pm10")
        pm25 = cur_a.get("pm2_5")

    # Optional OpenAQ enrichment (station measurements)
    oa = payload.get("openaq") or {}
    try:
        for loc in oa.get("results") or []:
            for m in loc.get("measurements") or []:
                if m.get("parameter") == "pm10" and pm10 is None:
                    pm10 = float(m["value"])
                if m.get("parameter") in ("pm25", "pm2.5") and pm25 is None:
                    pm25 = float(m["value"])
    except (KeyError, TypeError, ValueError):
        pass

    precip_7d = None
    climate = payload.get("climate") or {}
    daily = (climate.get("daily") or {}).get("precipitation_sum") or {}
    vals = daily.get("EC_Earth3_ensemble") or daily.get(list(daily.keys())[0]) if daily else None
    if isinstance(vals, list) and vals:
        precip_7d = float(sum(float(x or 0) for x in vals[-7:]))

    nasa = payload.get("nasa_power") or {}
    try:
        props = nasa["properties"]["parameter"]["PRECTOTCORR"]
        # NASA returns one value per day; sum last entries as coarse check
        if isinstance(props, dict) and props:
            precip_7d = precip_7d or float(sum(float(v) for v in list(props.values())[-7:]))
    except (KeyError, TypeError, ValueError):
        pass

    return EnvSignals(
        temperature_c=float(temp) if temp is not None else None,
        precip_mm_h=float(precip) if precip is not None else None,
        wind_kmh=float(wind) if wind is not None else None,
        pm10=float(pm10) if pm10 is not None else None,
        pm25=float(pm25) if pm25 is not None else None,
        precip_sum_7d_mm=float(precip_7d) if precip_7d is not None else None,
    )


def _base_factors(sig: EnvSignals) -> dict[str, Any]:
    factors: dict[str, Any] = {}
    if sig.temperature_c is not None:
        if sig.temperature_c < 10:
            factors["cold"] = {"value_c": sig.temperature_c, "weight": 25}
        if sig.temperature_c >= 34:
            factors["heat"] = {"value_c": sig.temperature_c, "weight": 30}
    if sig.wind_kmh is not None and sig.wind_kmh >= 40:
        factors["wind_dust"] = {"wind_kmh": sig.wind_kmh, "weight": 20}
    if sig.pm10 is not None:
        if sig.pm10 >= 150:
            factors["pm10"] = {"ug_m3": sig.pm10, "weight": 35}
        elif sig.pm10 >= 100:
            factors["pm10"] = {"ug_m3": sig.pm10, "weight": 25}
        elif sig.pm10 >= 50:
            factors["pm10"] = {"ug_m3": sig.pm10, "weight": 15}
    if sig.pm25 is not None and sig.pm25 >= 55:
        factors["pm25"] = {"ug_m3": sig.pm25, "weight": 15}
    if sig.precip_mm_h is not None and sig.precip_mm_h >= 12:
        factors["heavy_rain"] = {"mm_h": sig.precip_mm_h, "weight": 35}
    if sig.precip_sum_7d_mm is not None and sig.precip_sum_7d_mm >= 120:
        factors["wet_antecedent"] = {"mm_7d": sig.precip_sum_7d_mm, "weight": 15}
    return factors


def _spatial_weights(db: Session, zone_id: int) -> dict[str, float]:
    """Boost scores using static hazard intersections (mining, dust, flood)."""
    z = db.get(Zone, zone_id)
    if z is None:
        return {}
    weights: dict[str, float] = {}
    stmt: Select[tuple[HazardKind, int]] = (
        select(HazardArea.kind, func.count())
        .where(ST_Intersects(z.geom, HazardArea.geom))
        .group_by(HazardArea.kind)
    )
    for kind, cnt in db.execute(stmt).all():
        if kind == HazardKind.mine_site and cnt:
            weights["mining_proximity"] = 12.0
        if kind == HazardKind.dusty_corridor and cnt:
            weights["dust_corridor"] = 10.0
        if kind == HazardKind.flood_prone and cnt:
            weights["flood_prone"] = 18.0
    return weights


def _score_from_factors(factors: dict[str, Any], spatial: dict[str, float]) -> tuple[int, RiskSeverity]:
    total = sum(float(v.get("weight", 0)) for v in factors.values() if isinstance(v, dict))
    total += sum(spatial.values())
    total = int(max(0, min(100, round(total))))
    if total >= 85:
        sev = RiskSeverity.critical
    elif total >= 65:
        sev = RiskSeverity.high
    elif total >= 40:
        sev = RiskSeverity.moderate
    else:
        sev = RiskSeverity.low
    return total, sev


def _fingerprint(risk_type: RiskType, severity: RiskSeverity, zone_id: int | None, flood: bool) -> str:
    key = json.dumps(
        {"t": risk_type.value, "s": severity.value, "z": zone_id, "f": flood},
        sort_keys=True,
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:40]


def _cooldown_allows(db: Session, scope_key: str, fingerprint: str, cooldown: timedelta) -> bool:
    row = db.scalars(
        select(AlertCooldownState).where(AlertCooldownState.scope_key == scope_key),
    ).first()
    now = datetime.now(tz=UTC)
    if row is None:
        return True
    if row.last_fingerprint != fingerprint:
        return True
    return now - row.last_sent_at > cooldown


def _touch_cooldown(db: Session, scope_key: str, fingerprint: str) -> None:
    now = datetime.now(tz=UTC)
    row = db.scalars(
        select(AlertCooldownState).where(AlertCooldownState.scope_key == scope_key),
    ).first()
    if row is None:
        db.add(AlertCooldownState(scope_key=scope_key, last_fingerprint=fingerprint, last_sent_at=now))
    else:
        row.last_fingerprint = fingerprint
        row.last_sent_at = now


def _french_message_for_alert(
    risk_type: RiskType,
    severity: RiskSeverity,
    zone: Zone | None,
    flood_broadcast: bool,
    sig: EnvSignals,
) -> tuple[str, str]:
    zname = zone.name if zone else "Kolwezi"
    if flood_broadcast:
        return (
            "Risque d'inondation",
            "De fortes pluies ont été détectées ou prévues à Kolwezi. Veuillez assurer la sécurité des enfants et éviter les zones inondables.",
        )
    if risk_type == RiskType.reassurance:
        return (
            "Situation sous surveillance",
            "Tout va bien actuellement. Aucun risque climatique majeur détecté pour les enfants dans les zones suivies.",
        )
    if risk_type == RiskType.air_quality:
        return (
            "Pollution de l'air",
            f"Attention : pollution (poussière/PM) élevée autour de {zname}. Limitez l'exposition des enfants, surtout pour les asthmatiques.",
        )
    if risk_type == RiskType.heat:
        return (
            "Chaleur",
            f"Chaleur marquée à {zname}. Hydratez les enfants et évitez le soleil entre 11h et 15h.",
        )
    if risk_type == RiskType.cold:
        return (
            "Froid",
            f"Températures basses à {zname}. Protégez les nourrissons et les jeunes enfants du froid.",
        )
    if risk_type == RiskType.wind_dust:
        return (
            "Vent et poussière",
            f"Vents forts à {zname} : risque accru de dispersion des poussières liées au transport et à l'activité minière. Réduisez les activités extérieures.",
        )
    if risk_type == RiskType.flood:
        return (
            "Pluie intense",
            f"Pluie importante à {zname}. Évitez les eaux stagnantes et protégez l'eau potable.",
        )
    return (
        "Risque environnemental",
        f"Un risque pour la santé des enfants a été identifié à {zname}. Restez informé et appliquez les consignes locales.",
    )


def evaluate_and_persist(db: Session, merged_payload: dict[str, Any]) -> list[ZoneRiskScore]:
    """Compute per-zone scores, persist rows, emit alerts with cooldown + routing."""
    sig = parse_signals(merged_payload)
    zones = db.execute(select(Zone)).scalars().all()
    outputs: list[ZoneRiskScore] = []
    for z in zones:
        base = _base_factors(sig)
        spatial = _spatial_weights(db, z.id)
        merged_factors = {**base, "spatial": spatial}
        score, severity = _score_from_factors(base, spatial)
        zrs = ZoneRiskScore(zone_id=z.id, score=score, severity=severity, factors=merged_factors)
        db.add(zrs)
        outputs.append(zrs)
    db.flush()

    # Global flood broadcast heuristic
    flood_city = False
    if sig.precip_mm_h is not None and sig.precip_mm_h >= 12:
        flood_city = True
    if sig.precip_sum_7d_mm is not None and sig.precip_sum_7d_mm >= 160 and (sig.precip_mm_h or 0) >= 4:
        flood_city = True

    if flood_city:
        fp = _fingerprint(RiskType.flood, RiskSeverity.high, None, True)
        if _cooldown_allows(db, "flood:broadcast", fp, timedelta(minutes=45)):
            title, msg = _french_message_for_alert(RiskType.flood, RiskSeverity.high, None, True, sig)
            alert = Alert(
                title_fr=title,
                message_fr=msg,
                severity=RiskSeverity.high,
                risk_type=RiskType.flood,
                zone_id=None,
                flood_broadcast=True,
                metadata_json={"signals": sig.__dict__},
            )
            db.add(alert)
            db.flush()
            _dispatch_notifications(db, alert, broadcast_all=True)
            _touch_cooldown(db, "flood:broadcast", fp)
    else:
        # Zone-targeted alerts for elevated scores (use freshly computed rows)
        for z, latest in zip(zones, outputs, strict=True):
            if latest.severity in (RiskSeverity.high, RiskSeverity.critical):
                dominant = RiskType.composite
                if "pm10" in (latest.factors or {}) or "pm25" in (latest.factors or {}):
                    dominant = RiskType.air_quality
                elif "heat" in (latest.factors or {}):
                    dominant = RiskType.heat
                elif "cold" in (latest.factors or {}):
                    dominant = RiskType.cold
                elif "wind_dust" in (latest.factors or {}):
                    dominant = RiskType.wind_dust
                elif "heavy_rain" in (latest.factors or {}):
                    dominant = RiskType.flood

                fp = _fingerprint(dominant, latest.severity, z.id, False)
                scope = f"zone:{z.id}:{dominant.value}"
                if _cooldown_allows(db, scope, fp, timedelta(minutes=60)):
                    title, msg = _french_message_for_alert(dominant, latest.severity, z, False, sig)
                    alert = Alert(
                        title_fr=title,
                        message_fr=msg,
                        severity=latest.severity,
                        risk_type=dominant,
                        zone_id=z.id,
                        flood_broadcast=False,
                        metadata_json={"score": latest.score, "factors": latest.factors},
                    )
                    db.add(alert)
                    db.flush()
                    _dispatch_notifications(db, alert, broadcast_all=False, zone_id=z.id)
                    _touch_cooldown(db, scope, fp)

        # Reassurance when all zones are low/moderate and no flood
        if all(o.severity in (RiskSeverity.low, RiskSeverity.moderate) for o in outputs):
            fp = _fingerprint(RiskType.reassurance, RiskSeverity.low, None, False)
            if _cooldown_allows(db, "reassurance:global", fp, timedelta(hours=6)):
                title, msg = _french_message_for_alert(RiskType.reassurance, RiskSeverity.low, None, False, sig)
                alert = Alert(
                    title_fr=title,
                    message_fr=msg,
                    severity=RiskSeverity.low,
                    risk_type=RiskType.reassurance,
                    zone_id=None,
                    flood_broadcast=False,
                    metadata_json={"signals": sig.__dict__},
                )
                db.add(alert)
                db.flush()
                _dispatch_notifications(db, alert, broadcast_all=True)
                _touch_cooldown(db, "reassurance:global", fp)

    db.commit()
    publish_event({"type": "alerts_refresh", "at": datetime.now(tz=UTC).isoformat()})

    return outputs


def _geo_filter_recipients(
    db: Session,
    recipients: Sequence[Any],
    *,
    broadcast_all: bool,
    flood_broadcast: bool,
    zone_id: int | None,
) -> list[Any]:
    """Return recipients for a zone-targeted alert; broadcast modes return everyone."""
    items = list(recipients)
    if broadcast_all or flood_broadcast:
        return items

    matched: list[Any] = []
    for r in items:
        if r.home_lat is not None and r.home_lon is not None and zone_id is not None:
            z = db.get(Zone, zone_id)
            if z is None:
                continue
            inside = db.scalar(
                select(ST_Contains(z.geom, ST_SetSRID(ST_MakePoint(r.home_lon, r.home_lat), 4326))),
            )
            if inside:
                matched.append(r)
        elif r.school_id and zone_id is not None:
            sch = db.get(School, r.school_id)
            if sch and sch.zone_id == zone_id:
                matched.append(r)
    return matched if matched else items


def _dispatch_notifications(db: Session, alert: Alert, broadcast_all: bool, zone_id: int | None = None) -> None:
    """Create notification rows and invoke providers (channels auto-selected from prefs)."""
    from app.services import notifications as notif_svc

    users = db.execute(select(User).where(User.is_active.is_(True))).scalars().all()
    subscribers = db.execute(select(AlertSubscriber)).scalars().all()

    user_targets: list[User] = _geo_filter_recipients(
        db,
        users,
        broadcast_all=broadcast_all,
        flood_broadcast=alert.flood_broadcast,
        zone_id=zone_id,
    )
    sub_targets: list[AlertSubscriber] = _geo_filter_recipients(
        db,
        subscribers,
        broadcast_all=broadcast_all,
        flood_broadcast=alert.flood_broadcast,
        zone_id=zone_id,
    )

    body = alert.message_fr
    for u in user_targets:
        if u.alert_email_enabled:
            row = Notification(
                user_id=u.id,
                subscriber_id=None,
                alert_id=alert.id,
                channel=NotificationChannel.email,
                status=NotificationStatus.pending,
                body_fr=body,
            )
            db.add(row)
            db.flush()
            notif_svc.deliver_notification(db, row, u)
        if u.alert_sms_enabled and u.phone_e164:
            row = Notification(
                user_id=u.id,
                subscriber_id=None,
                alert_id=alert.id,
                channel=NotificationChannel.sms,
                status=NotificationStatus.pending,
                body_fr=body,
            )
            db.add(row)
            db.flush()
            notif_svc.deliver_notification(db, row, u)
        if u.alert_whatsapp_enabled and (u.whatsapp_e164 or u.phone_e164):
            row = Notification(
                user_id=u.id,
                subscriber_id=None,
                alert_id=alert.id,
                channel=NotificationChannel.whatsapp,
                status=NotificationStatus.pending,
                body_fr=body,
            )
            db.add(row)
            db.flush()
            notif_svc.deliver_notification(db, row, u, whatsapp_number=u.whatsapp_e164 or u.phone_e164)

    for s in sub_targets:
        if s.alert_email_enabled:
            row = Notification(
                user_id=None,
                subscriber_id=s.id,
                alert_id=alert.id,
                channel=NotificationChannel.email,
                status=NotificationStatus.pending,
                body_fr=body,
            )
            db.add(row)
            db.flush()
            notif_svc.deliver_notification(db, row, s)
        if s.alert_sms_enabled and s.phone_e164:
            row = Notification(
                user_id=None,
                subscriber_id=s.id,
                alert_id=alert.id,
                channel=NotificationChannel.sms,
                status=NotificationStatus.pending,
                body_fr=body,
            )
            db.add(row)
            db.flush()
            notif_svc.deliver_notification(db, row, s)
        if s.alert_whatsapp_enabled and (s.whatsapp_e164 or s.phone_e164):
            row = Notification(
                user_id=None,
                subscriber_id=s.id,
                alert_id=alert.id,
                channel=NotificationChannel.whatsapp,
                status=NotificationStatus.pending,
                body_fr=body,
            )
            db.add(row)
            db.flush()
            notif_svc.deliver_notification(db, row, s, whatsapp_number=s.whatsapp_e164 or s.phone_e164)
