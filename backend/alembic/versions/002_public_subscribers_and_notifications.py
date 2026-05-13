"""Alert subscribers + nullable notification recipient FKs.

Revision ID: 002
Revises: 001
Create Date: 2026-05-12
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alert_subscribers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone_e164", sa.String(length=32), nullable=True),
        sa.Column("whatsapp_e164", sa.String(length=32), nullable=True),
        sa.Column("alert_email_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("alert_sms_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("alert_whatsapp_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("home_lat", sa.Float(), nullable=True),
        sa.Column("home_lon", sa.Float(), nullable=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_alert_subscribers_email", "alert_subscribers", ["email"], unique=True)

    op.add_column("notifications", sa.Column("subscriber_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_notifications_subscriber_id",
        "notifications",
        "alert_subscribers",
        ["subscriber_id"],
        ["id"],
    )
    op.create_index("ix_notifications_subscriber_id", "notifications", ["subscriber_id"])

    op.alter_column("notifications", "user_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column("notifications", "user_id", existing_type=sa.Integer(), nullable=False)

    op.drop_index("ix_notifications_subscriber_id", table_name="notifications")
    op.drop_constraint("fk_notifications_subscriber_id", "notifications", type_="foreignkey")
    op.drop_column("notifications", "subscriber_id")

    op.drop_index("ix_alert_subscribers_email", table_name="alert_subscribers")
    op.drop_table("alert_subscribers")
