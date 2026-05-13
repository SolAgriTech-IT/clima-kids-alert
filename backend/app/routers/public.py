"""Public, unauthenticated endpoints (MVP open information system)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models.subscriber import AlertSubscriber
from app.schemas.subscribe import PublicSubscribeIn, PublicSubscribeOut

router = APIRouter(prefix="/public", tags=["public"])


@router.post("/subscribe", response_model=PublicSubscribeOut)
@limiter.limit("30/minute")
def subscribe(
    request: Request,
    payload: PublicSubscribeIn,
    db: Annotated[Session, Depends(get_db)],
) -> PublicSubscribeOut:
    """Create or update an alert subscription row (deduplicated by email)."""
    email = str(payload.email).lower()
    row = db.scalars(select(AlertSubscriber).where(AlertSubscriber.email == email)).first()
    if row is None:
        row = AlertSubscriber(email=email)
        db.add(row)

    row.phone_e164 = payload.phone_e164
    row.whatsapp_e164 = payload.whatsapp_e164
    row.school_id = payload.school_id
    row.home_lat = payload.home_lat
    row.home_lon = payload.home_lon
    row.alert_email_enabled = payload.alert_email_enabled
    row.alert_sms_enabled = payload.alert_sms_enabled
    row.alert_whatsapp_enabled = payload.alert_whatsapp_enabled

    if row.school_id is not None:
        from app.models.geo import School

        if db.get(School, row.school_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="École introuvable")

    db.commit()
    return PublicSubscribeOut()
