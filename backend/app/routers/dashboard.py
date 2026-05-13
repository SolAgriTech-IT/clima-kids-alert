"""Aggregated dashboard data for the French Next.js UI."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dashboard import DashboardSummary, DashboardTables, RiskCardsResponse
from app.services import dashboard_queries

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(
    db: Annotated[Session, Depends(get_db)],
) -> DashboardSummary:
    return DashboardSummary.model_validate(dashboard_queries.build_dashboard_summary(db))


@router.get("/risk-cards", response_model=RiskCardsResponse)
def risk_cards(
    db: Annotated[Session, Depends(get_db)],
) -> RiskCardsResponse:
    data = dashboard_queries.build_risk_cards(db)
    return RiskCardsResponse.model_validate(data)


@router.get("/tables", response_model=DashboardTables)
def tables(
    db: Annotated[Session, Depends(get_db)],
) -> DashboardTables:
    return DashboardTables(
        zone_scores=dashboard_queries.build_zone_score_rows(db),
        recent_alerts=dashboard_queries.build_recent_alerts(db),
    )
