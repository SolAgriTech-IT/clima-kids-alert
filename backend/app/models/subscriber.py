"""Public alert subscribers (no login) — contact details for outbound notifications."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SubscriberUserType(str, enum.Enum):
    school = "school"
    association = "association"
    parent = "parent"
    other = "other"


class LocationSource(str, enum.Enum):
    gps = "gps"
    ip = "ip"
    stored = "stored"


class AlertSubscriber(Base):
    """Public subscription row: channels enabled per contact method."""

    __tablename__ = "alert_subscribers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    phone_e164: Mapped[str | None] = mapped_column(String(32), nullable=True)
    whatsapp_e164: Mapped[str | None] = mapped_column(String(32), nullable=True)

    user_type: Mapped[SubscriberUserType] = mapped_column(
        Enum(SubscriberUserType, native_enum=False, length=32),
        default=SubscriberUserType.other,
        nullable=False,
    )

    alert_email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    alert_sms_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    alert_whatsapp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    home_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    home_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_source: Mapped[LocationSource | None] = mapped_column(
        Enum(LocationSource, native_enum=False, length=16),
        nullable=True,
    )
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    school = relationship("School", foreign_keys=[school_id], viewonly=True)
    notifications = relationship("Notification", back_populates="subscriber")


class UnsubscribeRequest(Base):
    """Logged opt-out request (admin notified, subscriber deactivated when matched)."""

    __tablename__ = "unsubscribe_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_e164: Mapped[str | None] = mapped_column(String(32), nullable=True)
    whatsapp_e164: Mapped[str | None] = mapped_column(String(32), nullable=True)
    user_type: Mapped[SubscriberUserType | None] = mapped_column(
        Enum(SubscriberUserType, native_enum=False, length=32),
        nullable=True,
    )
    payload_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
