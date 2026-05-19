"""Point-in-polygon zone lookup for subscriber geolocation."""

from __future__ import annotations

from geoalchemy2.elements import WKTElement
from geoalchemy2.functions import ST_Contains
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.geo import Zone


def find_zone_for_point(db: Session, lat: float, lon: float) -> Zone | None:
    """Return the zone whose polygon contains (lat, lon), if any."""
    pt = WKTElement(f"POINT({lon} {lat})", srid=4326)
    return db.scalars(select(Zone).where(ST_Contains(Zone.geom, pt)).limit(1)).first()
