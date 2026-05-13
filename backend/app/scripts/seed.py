"""Seed Kolwezi reference layers, demo facilities, and the MVP admin account.

Run automatically on container startup (Docker Compose).

Important: the **admin user is ensured on every run** (created if missing), even when
geo data already exists. Geo layers are only inserted when no zones are present.
"""

from __future__ import annotations

import logging
import sys

from geoalchemy2.elements import WKTElement
from shapely.geometry import MultiPolygon, Point, box

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import SessionLocal
from app.models import import_models
from app.models.geo import HazardArea, HazardKind, HealthCenter, School, Zone
from app.models.user import User, UserRole
from app.services.security import hash_password

log = logging.getLogger(__name__)


def _mpoly_from_offsets(center_lon: float, center_lat: float, half: float = 0.018) -> WKTElement:
    poly = box(center_lon - half, center_lat - half, center_lon + half, center_lat + half)
    mp = MultiPolygon([poly])
    return WKTElement(mp.wkt, srid=4326)


def ensure_seed_admin_user(db: Session, settings: Settings) -> None:
    """Create the configured admin account if it does not exist.

    If ``SEED_RESET_ADMIN_PASSWORD=true``, also resets the password hash and
    restores the admin role (development / recovery only).
    """
    email = settings.seed_admin_email.strip().lower()
    if not email:
        log.warning("SEED_ADMIN_EMAIL is empty; skipping admin seed")
        return

    user = db.scalars(select(User).where(User.email == email)).first()
    if user is None:
        db.add(
            User(
                email=email,
                password_hash=hash_password(settings.seed_admin_password),
                full_name="Administrateur CLIMA-KIDS",
                role=UserRole.admin,
                alert_email_enabled=True,
                alert_sms_enabled=False,
                alert_whatsapp_enabled=False,
            ),
        )
        db.commit()
        log.info("Admin seed: created %s", email)
        return

    if settings.seed_reset_admin_password:
        user.password_hash = hash_password(settings.seed_admin_password)
        user.role = UserRole.admin
        user.is_active = True
        db.add(user)
        db.commit()
        log.warning("Admin seed: password reset for %s (SEED_RESET_ADMIN_PASSWORD=true)", email)


def seed() -> None:
    import_models()
    settings = get_settings()
    db = SessionLocal()
    try:
        ensure_seed_admin_user(db, settings)

        if int(db.scalar(select(func.count()).select_from(Zone)) or 0) > 0:
            log.info("Geo seed skipped: zones already present")
            return

        districts = [
            ("manika", "Manika", (-10.70, 25.42)),
            ("kasulo", "Kasulo", (-10.72, 25.48)),
            ("dilala", "Dilala", (-10.74, 25.44)),
            ("kisiliu", "Kisiliu", (-10.68, 25.50)),
            ("mukondo", "Mukondo", (-10.76, 25.40)),
            ("musonje", "Musonje", (-10.73, 25.52)),
        ]
        zone_objs: list[Zone] = []
        for slug, name, (lat, lon) in districts:
            z = Zone(
                slug=slug,
                name=name,
                population_estimate=2500 + hash(slug) % 8000,
                geom=_mpoly_from_offsets(lon, lat),
            )
            db.add(z)
            zone_objs.append(z)
        db.flush()

        # Schools + health centers (illustrative counts aligned with the UI mock)
        school_names = [f"École primaire {i + 1}" for i in range(34)]
        for i, sname in enumerate(school_names):
            z = zone_objs[i % len(zone_objs)]
            lon, lat = districts[i % len(districts)][2][1], districts[i % len(districts)][2][0]
            jitter = (i % 5) * 0.002
            pt = WKTElement(Point(lon + jitter, lat + jitter).wkt, srid=4326)
            db.add(
                School(
                    zone_id=z.id,
                    name=sname,
                    student_count_estimate=350 + (i * 17) % 500,
                    geom=pt,
                ),
            )

        hc_names = [f"Centre de santé {i + 1}" for i in range(12)]
        for i, hname in enumerate(hc_names):
            z = zone_objs[(i + 2) % len(zone_objs)]
            lon, lat = districts[(i + 1) % len(districts)][2][1], districts[(i + 1) % len(districts)][2][0]
            jitter = (i % 4) * 0.0025
            pt = WKTElement(Point(lon + jitter, lat + jitter).wkt, srid=4326)
            db.add(HealthCenter(zone_id=z.id, name=hname, geom=pt))

        # Hazard overlays (mining / dust / flood-prone)
        db.add(
            HazardArea(
                name="Corridor minier principal",
                kind=HazardKind.mine_site,
                geom=_mpoly_from_offsets(25.46, -10.72, half=0.035),
            ),
        )
        db.add(
            HazardArea(
                name="Axes poussiéreux",
                kind=HazardKind.dusty_corridor,
                geom=_mpoly_from_offsets(25.50, -10.71, half=0.028),
            ),
        )
        db.add(
            HazardArea(
                name="Zones inondables signalées",
                kind=HazardKind.flood_prone,
                geom=_mpoly_from_offsets(25.44, -10.73, half=0.03),
            ),
        )

        db.commit()
        log.info("Geo seed completed (Kolwezi layers + facilities)")
    finally:
        db.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    seed()


if __name__ == "__main__":
    main()
    sys.exit(0)
