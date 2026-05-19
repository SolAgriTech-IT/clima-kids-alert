"""Admin-only simulation and broadcast endpoints."""

from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_admin
from app.models.alerting import Alert, Notification, NotificationChannel, NotificationStatus, RiskSeverity, RiskType
from app.models.subscriber import AlertSubscriber
from app.models.user import User, UserRole
from app.services.notifications import deliver_notification, delivery_row_dict, notification_providers_status
from app.services.risk_engine import evaluate_and_persist
from app.services.simulation import build_simulated_risk_cards, get_climate_override, set_climate_override
from app.services.security import hash_password

router = APIRouter(prefix="/admin/simulations", tags=["admin-simulations"])


@router.get("/notification-providers")
def get_notification_providers(_: Annotated[User, Depends(require_admin)]) -> dict:
    """Which outbound channels are configured (SendGrid, SMTP, Twilio)."""
    return notification_providers_status()


class ClimateSimIn(BaseModel):
    precip_mm: float = Field(ge=0, le=500, description="Pluie / inondation (mm)")
    pm10: float = Field(ge=0, le=1000, description="Pollution PM10 (µg/m³)")
    temperature_c: float = Field(ge=-20, le=55, description="Température (°C)")


@router.post("/climate")
def simulate_climate(
    payload: ClimateSimIn,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> dict:
    """Override dashboard climate cards for 2 minutes and re-run risk evaluation."""
    override = set_climate_override(
        precip_mm=payload.precip_mm,
        pm10=payload.pm10,
        temperature_c=payload.temperature_c,
    )
    fake_payload = {
        "weather": {
            "current": {
                "temperature_2m": override["temperature_c"],
                "precipitation": override["precip_mm"],
            },
        },
        "air_quality": {"current": {"pm10": override["pm10"]}},
        "simulation": True,
    }
    evaluate_and_persist(db, fake_payload)
    return {"status": "ok", "ttl_seconds": 120, "override": override, "alerts": "evaluated"}


@router.get("/climate/status")
def climate_sim_status(_: Annotated[User, Depends(require_admin)]) -> dict:
    active = get_climate_override()
    if active:
        return {"active": True, "override": active, "cards": build_simulated_risk_cards(active)}
    return {"active": False}


class TestAlertIn(BaseModel):
    email: str | None = Field(default=None, max_length=255)
    phone_e164: str | None = Field(default=None, max_length=32)

    @field_validator("phone_e164")
    @classmethod
    def e164(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if not re.fullmatch(r"\+[1-9]\d{6,14}", v):
            raise ValueError("Format E.164 requis")
        return v


@router.post("/test-alert")
def test_alert(
    payload: TestAlertIn,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> dict:
    if not payload.email and not payload.phone_e164:
        raise HTTPException(status_code=400, detail="E-mail ou numéro requis")

    alert = Alert(
        title_fr="Test CLIMA-KIDS ALERT",
        message_fr="Ceci est une alerte de test envoyée par un administrateur.",
        severity=RiskSeverity.moderate,
        risk_type=RiskType.composite,
        zone_id=None,
        flood_broadcast=False,
        metadata_json={"test": True},
    )
    db.add(alert)
    db.flush()

    target = SimpleNamespace(
        email=payload.email or "test@local.invalid",
        phone_e164=payload.phone_e164,
        whatsapp_e164=payload.phone_e164,
        alert_email_enabled=bool(payload.email),
        alert_sms_enabled=bool(payload.phone_e164),
        alert_whatsapp_enabled=bool(payload.phone_e164),
    )
    deliveries: list[dict[str, str | None]] = []
    for channel in (NotificationChannel.email, NotificationChannel.sms, NotificationChannel.whatsapp):
        if channel == NotificationChannel.email and not payload.email:
            continue
        if channel != NotificationChannel.email and not payload.phone_e164:
            continue
        row = Notification(
            user_id=None,
            subscriber_id=None,
            alert_id=alert.id,
            channel=channel,
            status=NotificationStatus.pending,
            body_fr=alert.message_fr,
        )
        db.add(row)
        db.flush()
        deliver_notification(db, row, target)
        deliveries.append(delivery_row_dict(row))

    db.commit()
    sent = sum(1 for d in deliveries if d["status"] == "sent")
    return {
        "status": "ok" if sent else "no_delivery",
        "sent": sent,
        "deliveries": deliveries,
        "providers": notification_providers_status(),
    }


class BroadcastIn(BaseModel):
    message_fr: str = Field(min_length=3, max_length=4000)

    @field_validator("message_fr")
    @classmethod
    def word_limit(cls, v: str) -> str:
        words = v.split()
        if len(words) > 150:
            raise ValueError("Message limité à 150 mots maximum")
        return v


@router.post("/broadcast")
def broadcast_message(
    payload: BroadcastIn,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> dict:
    """Send official message to each active subscriber on their enabled channels."""
    subs = db.scalars(select(AlertSubscriber).where(AlertSubscriber.is_active.is_(True))).all()
    sent = 0
    deliveries: list[dict[str, str | None]] = []
    alert = Alert(
        title_fr="Message officiel CLIMA-KIDS ALERT",
        message_fr=payload.message_fr,
        severity=RiskSeverity.moderate,
        risk_type=RiskType.composite,
        metadata_json={"broadcast_official": True},
    )
    db.add(alert)
    db.flush()

    for sub in subs:
        proxy = SimpleNamespace(
            email=sub.email,
            phone_e164=sub.phone_e164,
            whatsapp_e164=sub.whatsapp_e164 or sub.phone_e164,
            alert_email_enabled=sub.alert_email_enabled,
            alert_sms_enabled=sub.alert_sms_enabled,
            alert_whatsapp_enabled=sub.alert_whatsapp_enabled,
        )
        channels: list[NotificationChannel] = []
        if sub.alert_email_enabled:
            channels.append(NotificationChannel.email)
        if sub.alert_sms_enabled and sub.phone_e164:
            channels.append(NotificationChannel.sms)
        if sub.alert_whatsapp_enabled and (sub.whatsapp_e164 or sub.phone_e164):
            channels.append(NotificationChannel.whatsapp)
        for ch in channels:
            row = Notification(
                user_id=None,
                subscriber_id=sub.id,
                alert_id=alert.id,
                channel=ch,
                status=NotificationStatus.pending,
                body_fr=payload.message_fr,
            )
            db.add(row)
            db.flush()
            deliver_notification(db, row, proxy)
            if row.status == NotificationStatus.sent:
                sent += 1
            deliveries.append(
                {
                    **delivery_row_dict(row),
                    "subscriber": sub.email,
                },
            )

    db.commit()
    return {
        "status": "ok",
        "notifications_sent": sent,
        "notifications_total": len(deliveries),
        "deliveries": deliveries[:50],
        "deliveries_truncated": len(deliveries) > 50,
        "providers": notification_providers_status(),
    }


class AdminCreateIn(BaseModel):
    email: str
    password: str = Field(min_length=12, max_length=128)
    full_name: str | None = None


@router.get("/admins")
def list_admins(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> list[dict]:
    rows = db.scalars(select(User).where(User.role == UserRole.admin)).all()
    return [{"id": u.id, "email": u.email, "full_name": u.full_name, "is_active": u.is_active} for u in rows]


@router.post("/admins")
def create_admin(
    payload: AdminCreateIn,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> dict[str, str]:
    email = payload.email.strip().lower()
    existing = db.scalars(select(User).where(User.email == email)).first()
    if existing:
        existing.role = UserRole.admin
        existing.password_hash = hash_password(payload.password)
        existing.is_active = True
        if payload.full_name:
            existing.full_name = payload.full_name
    else:
        db.add(
            User(
                email=email,
                password_hash=hash_password(payload.password),
                full_name=payload.full_name or "Administrateur",
                role=UserRole.admin,
            ),
        )
    db.commit()
    return {"status": "ok", "email": email}


@router.delete("/admins/{user_id}")
def remove_admin(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
) -> dict[str, str]:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas supprimer votre propre compte")
    admins = db.scalars(select(User).where(User.role == UserRole.admin, User.is_active.is_(True))).all()
    if len(admins) <= 1 and target.role == UserRole.admin:
        raise HTTPException(status_code=400, detail="Au moins un administrateur doit rester actif")
    target.role = UserRole.user
    db.commit()
    return {"status": "ok"}
