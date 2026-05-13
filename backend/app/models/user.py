"""User accounts, roles, and notification channel preferences."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.geo import School


class UserRole(str, enum.Enum):
    """Application roles for authorization."""

    admin = "admin"
    user = "user"


class User(Base):
    """Registered user (parent, educator, or administrator).

    Contact fields are strictly validated at the API layer (Pydantic) to reduce
    abuse. No arbitrary file uploads are associated with this model.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_e164: Mapped[str | None] = mapped_column(String(32), nullable=True)
    whatsapp_e164: Mapped[str | None] = mapped_column(String(32), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=32),
        default=UserRole.user,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    alert_email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    alert_sms_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    alert_whatsapp_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    home_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    home_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    school = relationship("School", back_populates="associated_users")
    notifications = relationship("Notification", back_populates="user")
