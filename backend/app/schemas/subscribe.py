"""Public subscription payload (no password, no authentication)."""

from __future__ import annotations

import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.subscriber import LocationSource, SubscriberUserType


class PublicSubscribeIn(BaseModel):
    """Contact profile for alert routing with automatic geolocation fields."""

    email: EmailStr
    phone_e164: str | None = Field(default=None, max_length=32)
    whatsapp_e164: str | None = Field(default=None, max_length=32)
    user_type: SubscriberUserType = SubscriberUserType.other
    school_id: int | None = Field(default=None, ge=1)
    home_lat: float | None = Field(default=None, ge=-90, le=90)
    home_lon: float | None = Field(default=None, ge=-180, le=180)
    location_source: LocationSource | None = None
    alert_email_enabled: bool = True
    alert_sms_enabled: bool = False
    alert_whatsapp_enabled: bool = False

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
    message: str = (
        "Merci. Votre abonnement aux alertes climatiques a été pris en compte avec succès."
    )


class PublicUnsubscribeIn(BaseModel):
    email: EmailStr
    phone_e164: str | None = Field(default=None, max_length=32)
    whatsapp_e164: str | None = Field(default=None, max_length=32)
    user_type: SubscriberUserType | None = None

    @field_validator("phone_e164", "whatsapp_e164")
    @classmethod
    def e164(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if not re.fullmatch(r"\+[1-9]\d{6,14}", v):
            raise ValueError("Format E.164 requis (ex: +243900000000)")
        return v


class PublicUnsubscribeOut(BaseModel):
    status: str = "ok"
    message: str = "Votre demande de désabonnement a été enregistrée. Un administrateur la traitera sous peu."
