"""Outbound notifications via SendGrid (email) and Twilio (SMS + WhatsApp).

When credentials are missing, deliveries are marked ``skipped`` with an explicit
error message so operators can distinguish configuration gaps from provider
failures.
"""

from __future__ import annotations

from typing import Any

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client

from app.config import get_settings
from app.models.alerting import Notification, NotificationChannel, NotificationStatus

def deliver_notification(
    db: Any,
    row: Notification,
    user: Any,
    *,
    whatsapp_number: str | None = None,
) -> None:
    settings = get_settings()
    if row.channel == NotificationChannel.email:
        if not settings.sendgrid_api_key:
            row.status = NotificationStatus.skipped
            row.error_message = "SendGrid non configuré (SENDGRID_API_KEY)."
            return
        try:
            message = Mail(
                from_email=settings.email_from,
                to_emails=user.email,
                subject="CLIMA-KIDS ALERT",
                plain_text_content=row.body_fr,
            )
            sg = SendGridAPIClient(settings.sendgrid_api_key)
            resp = sg.send(message)
            row.status = NotificationStatus.sent
            row.provider_message_id = str(resp.status_code)
        except Exception as exc:  # noqa: BLE001 — provider errors are persisted
            row.status = NotificationStatus.failed
            row.error_message = str(exc)[:2000]
        return

    if row.channel in (NotificationChannel.sms, NotificationChannel.whatsapp):
        if not (settings.twilio_account_sid and settings.twilio_auth_token):
            row.status = NotificationStatus.skipped
            row.error_message = "Twilio non configuré (TWILIO_*)."
            return
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        try:
            if row.channel == NotificationChannel.sms:
                if not user.phone_e164 or not settings.twilio_sms_from:
                    row.status = NotificationStatus.skipped
                    row.error_message = "Numéro SMS ou expéditeur Twilio manquant."
                    return
                msg = client.messages.create(
                    body=row.body_fr,
                    from_=settings.twilio_sms_from,
                    to=user.phone_e164,
                )
                row.provider_message_id = msg.sid
            else:
                dest = whatsapp_number or user.whatsapp_e164 or user.phone_e164
                if not dest or not settings.twilio_whatsapp_from:
                    row.status = NotificationStatus.skipped
                    row.error_message = "Numéro WhatsApp ou expéditeur Twilio manquant."
                    return
                if not dest.startswith("whatsapp:"):
                    dest = f"whatsapp:{dest}"
                msg = client.messages.create(
                    body=row.body_fr,
                    from_=settings.twilio_whatsapp_from,
                    to=dest,
                )
                row.provider_message_id = msg.sid
            row.status = NotificationStatus.sent
        except Exception as exc:  # noqa: BLE001
            row.status = NotificationStatus.failed
            row.error_message = str(exc)[:2000]
