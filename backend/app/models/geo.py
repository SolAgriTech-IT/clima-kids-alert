"""Geospatial entities: neighborhoods, facilities, and hazard polygons (PostGIS)."""

from __future__ import annotations

import enum
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class HazardKind(str, enum.Enum):
    """Categories of static hazard layers used in risk overlays."""

    flood_prone = "flood_prone"
    mine_site = "mine_site"
    dusty_corridor = "dusty_corridor"


class Zone(Base):
    """Administrative or analytical neighborhood polygon (e.g., Kasulo, Manika)."""

    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    population_estimate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    geom: Mapped[object] = mapped_column(Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    schools = relationship("School", back_populates="zone")
    health_centers = relationship("HealthCenter", back_populates="zone")
    risk_scores = relationship("ZoneRiskScore", back_populates="zone")


class School(Base):
    """School point location for exposure mapping and optional user association."""

    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    student_count_estimate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    geom: Mapped[object] = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=False)

    zone = relationship("Zone", back_populates="schools")
    associated_users = relationship("User", back_populates="school")


class HealthCenter(Base):
    """Health facility point for map layers and response planning."""

    __tablename__ = "health_centers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    geom: Mapped[object] = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=False)

    zone = relationship("Zone", back_populates="health_centers")


class HazardArea(Base):
    """Polygon layer for flood-prone areas, mining footprints, or dust corridors."""

    __tablename__ = "hazard_areas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[HazardKind] = mapped_column(
        Enum(HazardKind, native_enum=False, length=32),
        nullable=False,
        index=True,
    )
    geom: Mapped[object] = mapped_column(Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
