"""Administrative actions (manual alert + report delivery).

The UI exposes only two actions; channels are selected automatically from each
user's preferences (email / SMS / WhatsApp).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import require_admin
from app.models.alerting import Alert, RiskSeverity, RiskType
from app.models.user import User
from app.services import dashboard_queries
from app.services.notifications import deliver_notification
from app.services.risk_engine import _dispatch_notifications

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/actions/run-pipeline")
def run_pipeline(
    _: Annotated[User, Depends(require_admin)],
) -> dict[str, str]:
    """Enqueue the Celery ingestion + risk evaluation pipeline (useful for demos)."""
    from app.tasks.pipeline import run_full_pipeline

    if get_settings().use_celery:
        run_full_pipeline.delay()
        return {"status": "queued"}
    run_full_pipeline.apply()
    return {"status": "ok"}


class SendAlertPayload(BaseModel):
    title_fr: str = Field(min_length=3, max_length=255)
    message_fr: str = Field(min_length=3, max_length=4000)
    broadcast_all: bool = True
    zone_id: int | None = Field(default=None, ge=1)


@router.post("/actions/send-alert")
def send_alert(
    payload: SendAlertPayload,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> dict[str, str]:
    alert = Alert(
        title_fr=payload.title_fr,
        message_fr=payload.message_fr,
        severity=RiskSeverity.high,
        risk_type=RiskType.composite,
        zone_id=payload.zone_id,
        flood_broadcast=payload.broadcast_all,
        metadata_json={"manual": True},
    )
    db.add(alert)
    db.flush()
    _dispatch_notifications(db, alert, broadcast_all=payload.broadcast_all, zone_id=payload.zone_id)
    db.commit()
    return {"status": "queued"}


class SendReportPayload(BaseModel):
    """Optional override recipient; defaults to the authenticated admin email."""

    to_email: str | None = Field(default=None, max_length=255)


@router.post("/actions/send-report")
def send_report(
    payload: SendReportPayload,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
) -> dict[str, str]:
    summary = dashboard_queries.build_dashboard_summary(db)
    tables = {
        "zones": dashboard_queries.build_zone_score_rows(db),
        "alerts": dashboard_queries.build_recent_alerts(db, limit=8),
    }
    body = (
        "Rapport CLIMA-KIDS ALERT\n\n"
        f"Zones à haut risque: {summary['high_risk_zones']}\n"
        f"Écoles exposées: {summary['schools_exposed']}\n"
        f"Centres de santé: {summary['health_centers']}\n"
        f"Enfants potentiellement exposés: {summary['children_potentially_exposed']}\n"
        f"Alertes aujourd'hui: {summary['alerts_sent_today']}\n"
        f"Taux de réception: {summary['reception_rate_percent']}%\n\n"
        f"Détail (aperçu): {tables!s}\n"
    )
    from app.models.alerting import Notification, NotificationChannel, NotificationStatus

    target_email = payload.to_email or admin.email
    row = Notification(
        user_id=admin.id,
        subscriber_id=None,
        alert_id=None,
        channel=NotificationChannel.email,
        status=NotificationStatus.pending,
        body_fr=body,
    )
    db.add(row)
    db.flush()
    proxy = SimpleNamespace(
        email=target_email,
        phone_e164=None,
        whatsapp_e164=None,
    )
    deliver_notification(db, row, proxy)  # type: ignore[arg-type]
    db.commit()
    return {"status": "sent" if row.status.value == "sent" else row.status.value}
