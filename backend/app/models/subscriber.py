"""Public alert subscribers (no login) — contact details for outbound notifications."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AlertSubscriber(Base):
    """MVP public subscription row: channels enabled by default when contact info exists."""

    __tablename__ = "alert_subscribers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone_e164: Mapped[str | None] = mapped_column(String(32), nullable=True)
    whatsapp_e164: Mapped[str | None] = mapped_column(String(32), nullable=True)

    alert_email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    alert_sms_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    alert_whatsapp_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    home_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    home_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    school = relationship("School", foreign_keys=[school_id], viewonly=True)
    notifications = relationship("Notification", back_populates="subscriber")
