"""Subscriber user_type, merge-friendly indexes, unsubscribe requests.

Revision ID: 003
Revises: 002
Create Date: 2026-05-17
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # String columns (native_enum=False in ORM) — avoids duplicate PostgreSQL ENUM DDL.
    op.add_column(
        "alert_subscribers",
        sa.Column(
            "user_type",
            sa.String(length=32),
            nullable=False,
            server_default="other",
        ),
    )
    op.add_column(
        "alert_subscribers",
        sa.Column(
            "location_source",
            sa.String(length=16),
            nullable=True,
        ),
    )
    op.add_column(
        "alert_subscribers",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "alert_subscribers",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.drop_index("ix_alert_subscribers_email", table_name="alert_subscribers")
    op.create_index("ix_alert_subscribers_email", "alert_subscribers", ["email"], unique=False)

    op.create_table(
        "unsubscribe_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone_e164", sa.String(length=32), nullable=True),
        sa.Column("whatsapp_e164", sa.String(length=32), nullable=True),
        sa.Column("user_type", sa.String(length=32), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_unsubscribe_requests_status", "unsubscribe_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_unsubscribe_requests_status", table_name="unsubscribe_requests")
    op.drop_table("unsubscribe_requests")

    op.drop_column("alert_subscribers", "updated_at")
    op.drop_column("alert_subscribers", "is_active")
    op.drop_column("alert_subscribers", "location_source")
    op.drop_column("alert_subscribers", "user_type")

    op.drop_index("ix_alert_subscribers_email", table_name="alert_subscribers")
    op.create_index("ix_alert_subscribers_email", "alert_subscribers", ["email"], unique=True)
