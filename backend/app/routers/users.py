"""Authenticated user profile routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(user, k, v)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
