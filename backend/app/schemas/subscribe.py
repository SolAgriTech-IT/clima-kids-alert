"""Public subscription payload (no password, no authentication)."""

from __future__ import annotations

import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class PublicSubscribeIn(BaseModel):
    """Minimal contact profile for alert routing."""

    email: EmailStr
    phone_e164: str | None = Field(default=None, max_length=32)
    whatsapp_e164: str | None = Field(default=None, max_length=32)
    school_id: int | None = Field(default=None, ge=1)
    home_lat: float | None = Field(default=None, ge=-90, le=90)
    home_lon: float | None = Field(default=None, ge=-180, le=180)
    alert_email_enabled: bool = True
    alert_sms_enabled: bool = True
    alert_whatsapp_enabled: bool = True

    @field_validator("phone_e164", "whatsapp_e164")
    @classmethod
    def e164(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if not re.fullmatch(r"\+[1-9]\d{6,14}", v):
            raise ValueError("Format E.164 requis (ex: +243900000000)")
        return v


class PublicSubscribeOut(BaseModel):
    status: str = "ok"
    message: str = "Inscription enregistrée. Vous recevrez les alertes selon vos canaux activés."
