"""Import Formspree notification emails / CSV exports into PostgreSQL.

Workflow (open source):
  1. Formspree forwards submissions to your inbox OR exports CSV.
  2. Save CSV to ./data/inbox/formspree_export.csv (gitignored).
  3. Run: python -m app.scripts.formspree_import data/inbox/formspree_export.csv
  4. Files older than 24h in data/inbox/processed/ are deleted automatically.

Expected CSV columns (flexible headers):
  email, phone, whatsapp, user_type, school_id,
  home_lat, home_lon, alert_email, alert_sms, alert_whatsapp
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.database import SessionLocal
from app.models import import_models
from app.models.subscriber import LocationSource, SubscriberUserType
from app.services.subscriber_merge import upsert_subscriber

log = logging.getLogger(__name__)

USER_TYPE_MAP = {
    "école": SubscriberUserType.school,
    "ecole": SubscriberUserType.school,
    "school": SubscriberUserType.school,
    "association": SubscriberUserType.association,
    "parent": SubscriberUserType.parent,
    "autre": SubscriberUserType.other,
    "other": SubscriberUserType.other,
}


def _bool(v: str | None) -> bool:
    if v is None:
        return False
    return str(v).strip().lower() in ("1", "true", "yes", "on", "oui")


def _parse_row(row: dict[str, str]) -> dict | None:
    email = (row.get("email") or row.get("Email") or "").strip()
    if not email:
        return None
    ut_raw = (row.get("user_type") or row.get("type") or "other").strip().lower()
    return {
        "email": email,
        "phone_e164": (row.get("phone_e164") or row.get("phone") or "").strip() or None,
        "whatsapp_e164": (row.get("whatsapp_e164") or row.get("whatsapp") or "").strip() or None,
        "user_type": USER_TYPE_MAP.get(ut_raw, SubscriberUserType.other),
        "school_id": int(row["school_id"]) if (row.get("school_id") or "").isdigit() else None,
        "home_lat": float(row["home_lat"]) if (row.get("home_lat") or "").strip() else None,
        "home_lon": float(row["home_lon"]) if (row.get("home_lon") or "").strip() else None,
        "location_source": LocationSource.stored,
        "alert_email_enabled": _bool(row.get("alert_email_enabled") or row.get("alert_email")),
        "alert_sms_enabled": _bool(row.get("alert_sms_enabled") or row.get("alert_sms")),
        "alert_whatsapp_enabled": _bool(row.get("alert_whatsapp_enabled") or row.get("alert_whatsapp")),
    }


def import_csv(path: Path) -> int:
    import_models()
    count = 0
    db = SessionLocal()
    try:
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                parsed = _parse_row(row)
                if not parsed:
                    continue
                upsert_subscriber(db, **parsed)
                count += 1
        db.commit()
    finally:
        db.close()
    return count


def purge_old_processed(processed_dir: Path, hours: int = 24) -> int:
    if not processed_dir.is_dir():
        return 0
    cutoff = datetime.now(tz=UTC) - timedelta(hours=hours)
    removed = 0
    for f in processed_dir.glob("*.csv"):
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=UTC)
        if mtime < cutoff:
            f.unlink(missing_ok=True)
            removed += 1
    return removed


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--processed-dir", type=Path, default=Path("data/inbox/processed"))
    args = parser.parse_args()

    if not args.csv_path.is_file():
        log.error("File not found: %s", args.csv_path)
        sys.exit(1)

    n = import_csv(args.csv_path)
    args.processed_dir.mkdir(parents=True, exist_ok=True)
    dest = args.processed_dir / f"{args.csv_path.stem}_{int(datetime.now(tz=UTC).timestamp())}.csv"
    args.csv_path.rename(dest)
    purged = purge_old_processed(args.processed_dir)
    log.info("Imported %s rows; moved to %s; purged %s old files", n, dest, purged)


if __name__ == "__main__":
    main()
