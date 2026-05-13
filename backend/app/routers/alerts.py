"""Alert listing for dashboards."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.alerting import Alert

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/recent")
def recent(
    db: Annotated[Session, Depends(get_db)],
    limit: int = 50,
) -> list[dict[str, Any]]:
    rows = db.execute(select(Alert).order_by(Alert.created_at.desc()).limit(limit)).scalars().all()
    return [
        {
            "id": a.id,
            "title_fr": a.title_fr,
            "message_fr": a.message_fr,
            "severity": a.severity.value,
            "risk_type": a.risk_type.value,
            "zone_id": a.zone_id,
            "flood_broadcast": a.flood_broadcast,
            "created_at": a.created_at.isoformat(),
        }
        for a in rows
    ]
