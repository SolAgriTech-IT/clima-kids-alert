"""Outbound notifications via SendGrid, SMTP (Brevo/Mailpit), or Twilio.

When no provider is configured, deliveries are marked ``skipped`` with an explicit
error message. Email tries SendGrid first, then SMTP (free tiers: Brevo, Mailpit local).
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Any

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client

from app.config import get_settings
from app.models.alerting import Notification, NotificationChannel, NotificationStatus

log = logging.getLogger(__name__)


def email_provider_configured() -> bool:
    settings = get_settings()
    return bool(settings.sendgrid_api_key) or bool(settings.smtp_host)


def sms_provider_configured() -> bool:
    settings = get_settings()
    return bool(settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_sms_from)


def whatsapp_provider_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_whatsapp_from,
    )


def notification_providers_status() -> dict[str, Any]:
    """Summary for admin UI — what is wired vs skipped."""
    settings = get_settings()
    return {
        "email": {
            "configured": email_provider_configured(),
            "sendgrid": bool(settings.sendgrid_api_key),
            "smtp": bool(settings.smtp_host),
            "from": settings.email_from,
        },
        "sms": {
            "configured": sms_provider_configured(),
            "from": settings.twilio_sms_from or None,
        },
        "whatsapp": {
            "configured": whatsapp_provider_configured(),
            "from": settings.twilio_whatsapp_from or None,
        },
        "hints": {
            "email_free": "SendGrid (100/jour) ou Brevo SMTP (300/jour) — voir .env.example",
            "sms_free": "Twilio essai : crédit gratuit, numéros vérifiés uniquement",
            "local_email": "Docker : Mailpit sur http://localhost:8025 si SMTP_HOST=mailpit",
        },
    }


def _send_email_smtp(to_email: str, subject: str, body: str) -> str:
    settings = get_settings()
    if not settings.smtp_host:
        raise RuntimeError("SMTP non configuré")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to_email
    msg.set_content(body)

    if settings.smtp_use_tls:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    return "smtp"


def _send_email_sendgrid(to_email: str, subject: str, body: str) -> str:
    settings = get_settings()
    message = Mail(
        from_email=settings.email_from,
        to_emails=to_email,
        subject=subject,
        plain_text_content=body,
    )
    sg = SendGridAPIClient(settings.sendgrid_api_key)
    resp = sg.send(message)
    return str(resp.status_code)


def deliver_notification(
    db: Any,
    row: Notification,
    user: Any,
    *,
    whatsapp_number: str | None = None,
) -> None:
    settings = get_settings()
    if row.channel == NotificationChannel.email:
        if not user.email:
            row.status = NotificationStatus.skipped
            row.error_message = "Adresse e-mail destinataire manquante."
            return
        if settings.sendgrid_api_key:
            try:
                row.provider_message_id = _send_email_sendgrid(
                    user.email,
                    "CLIMA-KIDS ALERT",
                    row.body_fr,
                )
                row.status = NotificationStatus.sent
                return
            except Exception as exc:  # noqa: BLE001
                row.status = NotificationStatus.failed
                row.error_message = f"SendGrid : {exc}"[:2000]
                return
        if settings.smtp_host:
            try:
                row.provider_message_id = _send_email_smtp(user.email, "CLIMA-KIDS ALERT", row.body_fr)
                row.status = NotificationStatus.sent
                log.info("E-mail envoyé via SMTP à %s", user.email)
                return
            except Exception as exc:  # noqa: BLE001
                row.status = NotificationStatus.failed
                row.error_message = f"SMTP : {exc}"[:2000]
                return
        row.status = NotificationStatus.skipped
        row.error_message = (
            "E-mail non configuré : renseignez SENDGRID_API_KEY ou SMTP_HOST "
            "(Brevo gratuit, Mailpit en local — voir .env.example)."
        )
        return

    if row.channel in (NotificationChannel.sms, NotificationChannel.whatsapp):
        if not (settings.twilio_account_sid and settings.twilio_auth_token):
            row.status = NotificationStatus.skipped
            row.error_message = (
                "Twilio non configuré (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN). "
                "Compte essai gratuit sur twilio.com — numéros vérifiés en phase test."
            )
            return
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        try:
            if row.channel == NotificationChannel.sms:
                if not user.phone_e164 or not settings.twilio_sms_from:
                    row.status = NotificationStatus.skipped
                    row.error_message = "Numéro SMS ou TWILIO_SMS_FROM manquant."
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
                    row.error_message = "Numéro WhatsApp ou TWILIO_WHATSAPP_FROM manquant."
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


def delivery_row_dict(row: Notification) -> dict[str, str | None]:
    return {
        "channel": row.channel.value,
        "status": row.status.value,
        "error": row.error_message,
        "provider_id": row.provider_message_id,
    }
