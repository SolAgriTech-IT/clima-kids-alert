"""Dashboard DTOs for the French UI."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    high_risk_zones: int
    schools_exposed: int
    health_centers: int
    children_potentially_exposed: int
    alerts_sent_today: int
    reception_rate_percent: int
    global_severity: str
    updated_at: datetime


class RiskCard(BaseModel):
    title: str
    value: str
    severity: str
    advice: str


class RiskCardsResponse(BaseModel):
    heat: RiskCard
    dust: RiskCard
    rain: RiskCard


class ZoneScoreRow(BaseModel):
    zone: str
    score: int
    level: str
    action: str


class AlertRow(BaseModel):
    date: str
    zone: str
    risk: str
    channel: str
    status: str


class DashboardTables(BaseModel):
    zone_scores: list[ZoneScoreRow]
    recent_alerts: list[AlertRow]


class GeoFeatureProperties(BaseModel):
    slug: str
    name: str
    score: int | None
    severity: str | None


class GeoJSONResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[dict[str, Any]]
