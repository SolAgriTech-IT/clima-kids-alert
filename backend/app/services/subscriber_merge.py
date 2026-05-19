"""Application-level subscriber merge (mirrors db/postgresql trigger logic)."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.subscriber import AlertSubscriber, LocationSource, SubscriberUserType


def find_matching_subscriber(
    db: Session,
    *,
    email: str,
    phone_e164: str | None,
    whatsapp_e164: str | None,
) -> AlertSubscriber | None:
    email_l = email.strip().lower()
    clauses = [AlertSubscriber.is_active.is_(True)]
    match_parts = [AlertSubscriber.email.ilike(email_l)]
    if phone_e164:
        match_parts.extend(
            [
                AlertSubscriber.phone_e164 == phone_e164,
                AlertSubscriber.whatsapp_e164 == phone_e164,
            ],
        )
    if whatsapp_e164:
        match_parts.extend(
            [
                AlertSubscriber.whatsapp_e164 == whatsapp_e164,
                AlertSubscriber.phone_e164 == whatsapp_e164,
            ],
        )
    stmt = select(AlertSubscriber).where(clauses[0], or_(*match_parts)).order_by(AlertSubscriber.id).limit(1)
    return db.scalars(stmt).first()


def upsert_subscriber(
    db: Session,
    *,
    email: str,
    phone_e164: str | None,
    whatsapp_e164: str | None,
    user_type: SubscriberUserType,
    school_id: int | None,
    home_lat: float | None,
    home_lon: float | None,
    location_source: LocationSource | None,
    alert_email_enabled: bool,
    alert_sms_enabled: bool,
    alert_whatsapp_enabled: bool,
) -> AlertSubscriber:
    row = find_matching_subscriber(
        db,
        email=email,
        phone_e164=phone_e164,
        whatsapp_e164=whatsapp_e164,
    )
    if row is None:
        row = AlertSubscriber(email=email.strip().lower())
        db.add(row)

    row.email = email.strip().lower()
    if phone_e164:
        row.phone_e164 = phone_e164
    if whatsapp_e164:
        row.whatsapp_e164 = whatsapp_e164
    row.user_type = user_type
    row.school_id = school_id
    if home_lat is not None:
        row.home_lat = home_lat
    if home_lon is not None:
        row.home_lon = home_lon
    if location_source is not None:
        row.location_source = location_source
    row.alert_email_enabled = row.alert_email_enabled or alert_email_enabled
    row.alert_sms_enabled = row.alert_sms_enabled or alert_sms_enabled
    row.alert_whatsapp_enabled = row.alert_whatsapp_enabled or alert_whatsapp_enabled
    row.is_active = True
    return row
