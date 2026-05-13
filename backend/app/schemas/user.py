"""User profile schemas."""

from __future__ import annotations

import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None
    role: UserRole
    phone_e164: str | None
    whatsapp_e164: str | None
    alert_email_enabled: bool
    alert_sms_enabled: bool
    alert_whatsapp_enabled: bool
    home_lat: float | None
    home_lon: float | None
    school_id: int | None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    phone_e164: str | None = Field(default=None, max_length=32)
    whatsapp_e164: str | None = Field(default=None, max_length=32)
    alert_email_enabled: bool | None = None
    alert_sms_enabled: bool | None = None
    alert_whatsapp_enabled: bool | None = None
    home_lat: float | None = Field(default=None, ge=-90, le=90)
    home_lon: float | None = Field(default=None, ge=-180, le=180)
    school_id: int | None = Field(default=None, ge=1)

    @field_validator("phone_e164", "whatsapp_e164")
    @classmethod
    def e164(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not re.fullmatch(r"\+[1-9]\d{6,14}", v):
            raise ValueError("Format E.164 requis (ex: +243900000000)")
        return v
