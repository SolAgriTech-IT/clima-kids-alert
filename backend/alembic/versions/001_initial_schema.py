"""Initial PostGIS schema for CLIMA-KIDS ALERT.

Revision ID: 001
Revises:
Create Date: 2026-05-11
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2.types import Geometry
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "zones",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("population_estimate", sa.Integer(), nullable=True),
        sa.Column("geom", Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_zones_slug", "zones", ["slug"], unique=True)

    op.create_table(
        "schools",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("zone_id", sa.Integer(), sa.ForeignKey("zones.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("student_count_estimate", sa.Integer(), nullable=True),
        sa.Column("geom", Geometry(geometry_type="POINT", srid=4326), nullable=False),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"]),
    )
    op.create_index("ix_schools_zone_id", "schools", ["zone_id"])

    op.create_table(
        "health_centers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("zone_id", sa.Integer(), sa.ForeignKey("zones.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("geom", Geometry(geometry_type="POINT", srid=4326), nullable=False),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"]),
    )
    op.create_index("ix_health_centers_zone_id", "health_centers", ["zone_id"])

    op.create_table(
        "hazard_areas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("geom", Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_hazard_areas_kind", "hazard_areas", ["kind"])

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("phone_e164", sa.String(length=32), nullable=True),
        sa.Column("whatsapp_e164", sa.String(length=32), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("alert_email_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("alert_sms_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("alert_whatsapp_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("home_lat", sa.Float(), nullable=True),
        sa.Column("home_lon", sa.Float(), nullable=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "environmental_readings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_environmental_readings_observed_at", "environmental_readings", ["observed_at"])
    op.create_index("ix_environmental_readings_source", "environmental_readings", ["source"])

    op.create_table(
        "zone_risk_scores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("zone_id", sa.Integer(), sa.ForeignKey("zones.id"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("factors", JSONB(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"]),
    )
    op.create_index("ix_zone_risk_scores_zone_id", "zone_risk_scores", ["zone_id"])
    op.create_index("ix_zone_risk_scores_computed_at", "zone_risk_scores", ["computed_at"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title_fr", sa.String(length=255), nullable=False),
        sa.Column("message_fr", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("risk_type", sa.String(length=32), nullable=False),
        sa.Column("zone_id", sa.Integer(), sa.ForeignKey("zones.id"), nullable=True),
        sa.Column("flood_broadcast", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"]),
    )
    op.create_index("ix_alerts_severity", "alerts", ["severity"])
    op.create_index("ix_alerts_risk_type", "alerts", ["risk_type"])
    op.create_index("ix_alerts_zone_id", "alerts", ["zone_id"])
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("alert_id", sa.Integer(), sa.ForeignKey("alerts.id"), nullable=True),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("body_fr", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"]),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_alert_id", "notifications", ["alert_id"])
    op.create_index("ix_notifications_status", "notifications", ["status"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])

    op.create_table(
        "api_fetch_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_api_fetch_logs_source", "api_fetch_logs", ["source"])
    op.create_index("ix_api_fetch_logs_created_at", "api_fetch_logs", ["created_at"])

    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("config", JSONB(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_alert_rules_name", "alert_rules", ["name"], unique=True)

    op.create_table(
        "alert_cooldown_state",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scope_key", sa.String(length=255), nullable=False),
        sa.Column("last_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alert_cooldown_scope_key", "alert_cooldown_state", ["scope_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_alert_cooldown_scope_key", table_name="alert_cooldown_state")
    op.drop_table("alert_cooldown_state")
    op.drop_index("ix_alert_rules_name", table_name="alert_rules")
    op.drop_table("alert_rules")
    op.drop_index("ix_api_fetch_logs_created_at", table_name="api_fetch_logs")
    op.drop_index("ix_api_fetch_logs_source", table_name="api_fetch_logs")
    op.drop_table("api_fetch_logs")
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_status", table_name="notifications")
    op.drop_index("ix_notifications_alert_id", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_alerts_created_at", table_name="alerts")
    op.drop_index("ix_alerts_zone_id", table_name="alerts")
    op.drop_index("ix_alerts_risk_type", table_name="alerts")
    op.drop_index("ix_alerts_severity", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_zone_risk_scores_computed_at", table_name="zone_risk_scores")
    op.drop_index("ix_zone_risk_scores_zone_id", table_name="zone_risk_scores")
    op.drop_table("zone_risk_scores")
    op.drop_index("ix_environmental_readings_source", table_name="environmental_readings")
    op.drop_index("ix_environmental_readings_observed_at", table_name="environmental_readings")
    op.drop_table("environmental_readings")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_hazard_areas_kind", table_name="hazard_areas")
    op.drop_table("hazard_areas")
    op.drop_index("ix_health_centers_zone_id", table_name="health_centers")
    op.drop_table("health_centers")
    op.drop_index("ix_schools_zone_id", table_name="schools")
    op.drop_table("schools")
    op.drop_index("ix_zones_slug", table_name="zones")
    op.drop_table("zones")
    op.execute("DROP EXTENSION IF EXISTS postgis")
