"""Public, unauthenticated endpoints (MVP open information system)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.limiter import limiter
from app.models.alerting import Notification, NotificationChannel, NotificationStatus
from app.models.subscriber import UnsubscribeRequest
from app.schemas.subscribe import (
    PublicSubscribeIn,
    PublicSubscribeOut,
    PublicUnsubscribeIn,
    PublicUnsubscribeOut,
)
from app.services.geo_zones import find_zone_for_point
from app.services.notifications import deliver_notification
from app.services.subscriber_merge import upsert_subscriber

router = APIRouter(prefix="/public", tags=["public"])


@router.post("/subscribe", response_model=PublicSubscribeOut)
def subscribe(
    data: PublicSubscribeIn,
    db: Annotated[Session, Depends(get_db)],
) -> PublicSubscribeOut:
    """Create or merge an alert subscription (email / phone / WhatsApp identity)."""
    if data.school_id is not None:
        from app.models.geo import School

        if db.get(School, data.school_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="École introuvable")

    upsert_subscriber(
        db,
        email=str(data.email),
        phone_e164=data.phone_e164,
        whatsapp_e164=data.whatsapp_e164,
        user_type=data.user_type,
        school_id=data.school_id,
        home_lat=data.home_lat,
        home_lon=data.home_lon,
        location_source=data.location_source,
        alert_email_enabled=data.alert_email_enabled,
        alert_sms_enabled=data.alert_sms_enabled,
        alert_whatsapp_enabled=data.alert_whatsapp_enabled,
    )
    msg = "Merci. Votre abonnement aux alertes climatiques a été pris en compte avec succès."
    if data.home_lat is not None and data.home_lon is not None:
        zone = find_zone_for_point(db, data.home_lat, data.home_lon)
        if zone is not None:
            msg += f" Vous serez alerté pour la zone : {zone.name}."
    db.commit()
    return PublicSubscribeOut(message=msg)


@router.post("/unsubscribe", response_model=PublicUnsubscribeOut)
def unsubscribe(
    data: PublicUnsubscribeIn,
    db: Annotated[Session, Depends(get_db)],
) -> PublicUnsubscribeOut:
    """Record opt-out request, deactivate matching subscriber, notify admin."""
    settings = get_settings()
    req = UnsubscribeRequest(
        email=str(data.email).lower(),
        phone_e164=data.phone_e164,
        whatsapp_e164=data.whatsapp_e164,
        user_type=data.user_type,
        payload_json=data.model_dump(),
        status="pending",
    )
    db.add(req)

    from app.services.subscriber_merge import find_matching_subscriber

    row = find_matching_subscriber(
        db,
        email=str(data.email),
        phone_e164=data.phone_e164,
        whatsapp_e164=data.whatsapp_e164,
    )
    if row is not None:
        row.is_active = False
        row.alert_email_enabled = False
        row.alert_sms_enabled = False
        row.alert_whatsapp_enabled = False
        req.status = "processed"
        req.processed_at = datetime.now(tz=UTC)

    db.flush()

    admin_email = settings.admin_notify_email or settings.seed_admin_email
    if admin_email:
        body = (
            "Demande de désabonnement CLIMA-KIDS ALERT\n\n"
            f"E-mail : {data.email}\n"
            f"Téléphone : {data.phone_e164 or '—'}\n"
            f"WhatsApp : {data.whatsapp_e164 or '—'}\n"
            f"Type : {(data.user_type.value if data.user_type else '—')}\n"
            f"Statut : {req.status}\n"
        )
        notif = Notification(
            user_id=None,
            subscriber_id=row.id if row else None,
            alert_id=None,
            channel=NotificationChannel.email,
            status=NotificationStatus.pending,
            body_fr=body,
        )
        db.add(notif)
        db.flush()
        deliver_notification(db, notif, SimpleNamespace(email=admin_email, phone_e164=None, whatsapp_e164=None))

    db.commit()
    return PublicUnsubscribeOut()


@router.get("/geo/ip-location")
@limiter.limit("60/minute")
async def ip_location(request: Request) -> dict[str, Any]:
    """Fallback geolocation from client IP (when GPS is denied)."""
    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else ""
    )
    if not client_ip or client_ip in ("127.0.0.1", "::1"):
        settings = get_settings()
        return {
            "lat": settings.default_lat,
            "lon": settings.default_lon,
            "source": "default",
            "city": settings.default_city_name,
        }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"http://ip-api.com/json/{client_ip}?fields=status,lat,lon,city")
            data = resp.json()
        if data.get("status") == "success":
            return {
                "lat": float(data["lat"]),
                "lon": float(data["lon"]),
                "source": "ip",
                "city": data.get("city"),
            }
    except Exception:
        pass
    settings = get_settings()
    return {
        "lat": settings.default_lat,
        "lon": settings.default_lon,
        "source": "default",
        "city": settings.default_city_name,
    }
