"""Liveness/readiness endpoints for orchestrators (Docker, Kubernetes, Nginx)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    """Return ``ok`` when the API process and database connection are healthy."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
