"""Alerts, notifications, environmental readings, and API ingestion logs."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RiskSeverity(str, enum.Enum):
    """Ordered severity for UI and routing."""

    low = "low"
    moderate = "moderate"
    high = "high"
    critical = "critical"


class RiskType(str, enum.Enum):
    """Risk channel labels aligned with the child health engine."""

    heat = "heat"
    cold = "cold"
    air_quality = "air_quality"
    wind_dust = "wind_dust"
    flood = "flood"
    composite = "composite"
    reassurance = "reassurance"


class NotificationChannel(str, enum.Enum):
    """Outbound notification channels."""

    email = "email"
    sms = "sms"
    whatsapp = "whatsapp"


class NotificationStatus(str, enum.Enum):
    """Delivery lifecycle for observability and duplicate control."""

    pending = "pending"
    sent = "sent"
    failed = "failed"
    skipped = "skipped"


class EnvironmentalReading(Base):
    """Time-stamped observation bundle from external APIs (Open-Meteo, OpenAQ, etc.)."""

    __tablename__ = "environmental_readings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ZoneRiskScore(Base):
    """Latest computed child health risk score per zone."""

    __tablename__ = "zone_risk_scores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), index=True, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[RiskSeverity] = mapped_column(
        Enum(RiskSeverity, native_enum=False, length=32),
        nullable=False,
    )
    factors: Mapped[dict] = mapped_column(JSONB, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    zone = relationship("Zone", back_populates="risk_scores")


class Alert(Base):
    """Human-readable alert record (French message) with optional geospatial targeting."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title_fr: Mapped[str] = mapped_column(String(255), nullable=False)
    message_fr: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[RiskSeverity] = mapped_column(
        Enum(RiskSeverity, native_enum=False, length=32),
        nullable=False,
        index=True,
    )
    risk_type: Mapped[RiskType] = mapped_column(
        Enum(RiskType, native_enum=False, length=32),
        nullable=False,
        index=True,
    )
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id"), nullable=True, index=True)
    flood_broadcast: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    zone = relationship("Zone")
    notifications = relationship("Notification", back_populates="alert")


class Notification(Base):
    """Per-recipient delivery attempt across email, SMS, or WhatsApp."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    subscriber_id: Mapped[int | None] = mapped_column(
        ForeignKey("alert_subscribers.id"),
        index=True,
        nullable=True,
    )
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id"), nullable=True, index=True)
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, native_enum=False, length=32),
        nullable=False,
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, native_enum=False, length=32),
        nullable=False,
        index=True,
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_fr: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", back_populates="notifications")
    subscriber = relationship("AlertSubscriber", back_populates="notifications")
    alert = relationship("Alert", back_populates="notifications")


class ApiFetchLog(Base):
    """Operational trace for ingestion jobs (latency, HTTP codes, error strings)."""

    __tablename__ = "api_fetch_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class AlertRule(Base):
    """Versioned JSON rule configuration for future admin tuning (engine still uses code paths)."""

    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AlertCooldownState(Base):
    """Stores last fired fingerprint per scope to prevent notification spam."""

    __tablename__ = "alert_cooldown_state"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scope_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    last_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
