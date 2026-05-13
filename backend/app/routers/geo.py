"""GeoJSON layers for Leaflet."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from geoalchemy2.functions import ST_AsGeoJSON
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.geo import HazardArea, HealthCenter, School

router = APIRouter(prefix="/geo", tags=["geo"])


def _features(db: Session, model: type) -> list[dict[str, Any]]:
    feats: list[dict[str, Any]] = []
    for row in db.execute(select(model)).scalars().all():
        gj = db.scalar(select(ST_AsGeoJSON(row.geom)))
        geom = json.loads(gj) if isinstance(gj, str) else gj
        props: dict[str, Any] = {}
        for col in row.__table__.columns.keys():
            if col == "geom":
                continue
            v = getattr(row, col)
            if hasattr(v, "value"):
                v = v.value
            props[col] = v
        feats.append({"type": "Feature", "geometry": geom, "properties": props})
    return feats


@router.get("/zones")
def zones_geojson(
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    from app.services import dashboard_queries

    return dashboard_queries.zones_geojson(db)


@router.get("/schools")
def schools_geojson(
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": _features(db, School)}


@router.get("/health-centers")
def health_geojson(
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": _features(db, HealthCenter)}


@router.get("/hazards")
def hazards_geojson(
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": _features(db, HazardArea)}
