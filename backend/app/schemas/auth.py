"""Authentication request/response schemas (validation only; messages are French at API edge)."""

from __future__ import annotations

import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    phone_e164: str | None = Field(default=None, max_length=32)
    whatsapp_e164: str | None = Field(default=None, max_length=32)
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


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
