"""Registration and JWT login."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import TokenResponse, UserLogin, UserRegister
from app.schemas.user import UserOut
from app.services.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> User:
    exists = db.scalars(select(User).where(User.email == str(payload.email).lower())).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cet e-mail est déjà utilisé")
    user = User(
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        phone_e164=payload.phone_e164,
        whatsapp_e164=payload.whatsapp_e164,
        role=UserRole.user,
        home_lat=payload.home_lat,
        home_lon=payload.home_lon,
        school_id=payload.school_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = db.scalars(select(User).where(User.email == str(credentials.email).lower())).first()
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte désactivé")
    token = create_access_token(str(user.id), {"role": user.role.value})
    return TokenResponse(access_token=token)
