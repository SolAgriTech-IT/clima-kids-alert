"""CLI for administrator accounts (open-source deployments).

Usage:
  python -m app.scripts.manage_admin list
  python -m app.scripts.manage_admin create admin@example.org 'SecurePassword12!'
  python -m app.scripts.manage_admin promote user@example.org
  python -m app.scripts.manage_admin demote user@example.org
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from app.database import SessionLocal
from app.models import import_models
from app.models.user import User, UserRole
from app.services.security import hash_password


def cmd_list(db) -> None:
    rows = db.scalars(select(User).where(User.role == UserRole.admin)).all()
    for u in rows:
        print(f"{u.id}\t{u.email}\tactive={u.is_active}\t{u.full_name or ''}")


def cmd_create(db, email: str, password: str, full_name: str | None) -> None:
    email = email.strip().lower()
    user = db.scalars(select(User).where(User.email == email)).first()
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name or "Administrateur",
            role=UserRole.admin,
        )
        db.add(user)
    else:
        user.password_hash = hash_password(password)
        user.role = UserRole.admin
        user.is_active = True
        if full_name:
            user.full_name = full_name
    db.commit()
    print(f"OK admin: {email}")


def cmd_promote(db, email: str) -> None:
    email = email.strip().lower()
    user = db.scalars(select(User).where(User.email == email)).first()
    if user is None:
        print(f"User not found: {email}", file=sys.stderr)
        sys.exit(1)
    user.role = UserRole.admin
    user.is_active = True
    db.commit()
    print(f"OK promoted: {email}")


def cmd_demote(db, email: str) -> None:
    email = email.strip().lower()
    user = db.scalars(select(User).where(User.email == email)).first()
    if user is None:
        print(f"User not found: {email}", file=sys.stderr)
        sys.exit(1)
    user.role = UserRole.user
    db.commit()
    print(f"OK demoted: {email}")


def main() -> None:
    import_models()
    parser = argparse.ArgumentParser(description="CLIMA-KIDS admin user management")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list")
    p_create = sub.add_parser("create")
    p_create.add_argument("email")
    p_create.add_argument("password")
    p_create.add_argument("--name", default=None)

    p_promote = sub.add_parser("promote")
    p_promote.add_argument("email")

    p_demote = sub.add_parser("demote")
    p_demote.add_argument("email")

    args = parser.parse_args()
    db = SessionLocal()
    try:
        if args.command == "list":
            cmd_list(db)
        elif args.command == "create":
            cmd_create(db, args.email, args.password, args.name)
        elif args.command == "promote":
            cmd_promote(db, args.email)
        elif args.command == "demote":
            cmd_demote(db, args.email)
    finally:
        db.close()


if __name__ == "__main__":
    main()
