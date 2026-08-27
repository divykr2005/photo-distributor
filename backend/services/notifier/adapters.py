import logging
import os
import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import requests

from core.config import settings
from services.notifier.base import BaseNotifier, NotificationResult

logger = logging.getLogger(__name__)


class ConsoleNotifier(BaseNotifier):
    """Dev default notifier logging messages to stdout/logger."""

    def send(
        self,
        recipient: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ) -> NotificationResult:
        msg_id = f"console_{uuid.uuid4().hex[:12]}"
        logger.info(
            f"[CONSOLE NOTIFIER] Recipient: {recipient} | Subject: {subject}\n"
            f"--- TEXT BODY ---\n{body_text}\n-------------------"
        )
        return NotificationResult(
            success=True,
            provider="console",
            provider_message_id=msg_id,
        )


class SmtpNotifier(BaseNotifier):
    """SMTP email notifier."""

    def send(
        self,
        recipient: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ) -> NotificationResult:
        smtp_host = getattr(settings, "SMTP_HOST", None) or os.getenv("SMTP_HOST")
        smtp_port = int(getattr(settings, "SMTP_PORT", 587) or os.getenv("SMTP_PORT", 587))
        smtp_user = getattr(settings, "SMTP_USER", None) or os.getenv("SMTP_USER")
        smtp_password = getattr(settings, "SMTP_PASSWORD", None) or os.getenv("SMTP_PASSWORD")
        smtp_from = getattr(settings, "SMTP_FROM", "noreply@eventphotos.com") or os.getenv("SMTP_FROM", "noreply@eventphotos.com")

        if not smtp_host:
            # Fallback to console mock behavior if SMTP not configured
            logger.warning("[SMTP NOTIFIER] SMTP_HOST not configured. Falling back to console logging.")
            return ConsoleNotifier().send(recipient, subject, body_text, body_html, extra_data)

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = smtp_from
            msg["To"] = recipient

            part1 = MIMEText(body_text, "plain")
            msg.attach(part1)

            if body_html:
                part2 = MIMEText(body_html, "html")
                msg.attach(part2)

            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                if getattr(settings, "SMTP_TLS", True):
                    server.starttls()
                if smtp_user and smtp_password:
                    server.login(smtp_user, smtp_password)
                server.sendmail(smtp_from, [recipient], msg.as_string())

            msg_id = f"smtp_{uuid.uuid4().hex[:12]}"
            return NotificationResult(
                success=True,
                provider="smtp",
                provider_message_id=msg_id,
            )
        except (smtplib.SMTPException, TimeoutError, OSError) as e:
            logger.error(f"[SMTP NOTIFIER] Transient error sending to {recipient}: {e}")
            return NotificationResult(
                success=False,
                provider="smtp",
                error=str(e),
                is_transient=True,
            )
        except Exception as e:
            logger.error(f"[SMTP NOTIFIER] Hard error sending to {recipient}: {e}")
            return NotificationResult(
                success=False,
                provider="smtp",
                error=str(e),
                is_transient=False,
            )


class WebhookNotifier(BaseNotifier):
    """Webhook notifier posting JSON payload to custom endpoint."""

    def send(
        self,
        recipient: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ) -> NotificationResult:
        webhook_url = recipient if recipient.startswith("http") else getattr(settings, "WEBHOOK_URL", None) or os.getenv("WEBHOOK_URL")

        if not webhook_url:
            logger.warning("[WEBHOOK NOTIFIER] No webhook URL configured. Falling back to console logging.")
            return ConsoleNotifier().send(recipient, subject, body_text, body_html, extra_data)

        payload = {
            "recipient": recipient,
            "subject": subject,
            "body_text": body_text,
            "body_html": body_html,
            "extra_data": extra_data or {},
        }

        try:
            resp = requests.post(webhook_url, json=payload, timeout=5)
            if resp.status_code >= 500 or resp.status_code == 429:
                return NotificationResult(
                    success=False,
                    provider="webhook",
                    error=f"HTTP {resp.status_code}: {resp.text[:100]}",
                    is_transient=True,
                )
            elif resp.status_code >= 400:
                return NotificationResult(
                    success=False,
                    provider="webhook",
                    error=f"HTTP {resp.status_code}: {resp.text[:100]}",
                    is_transient=False,
                )
            return NotificationResult(
                success=True,
                provider="webhook",
                provider_message_id=f"wh_{uuid.uuid4().hex[:12]}",
            )
        except requests.RequestException as e:
            return NotificationResult(
                success=False,
                provider="webhook",
                error=str(e),
                is_transient=True,
            )


class TwilioSmsNotifier(BaseNotifier):
    """Twilio SMS notifier."""

    def send(
        self,
        recipient: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ) -> NotificationResult:
        account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None) or os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None) or os.getenv("TWILIO_AUTH_TOKEN")
        from_number = getattr(settings, "TWILIO_PHONE_NUMBER", None) or os.getenv("TWILIO_PHONE_NUMBER")

        if not (account_sid and auth_token and from_number):
            logger.warning("[TWILIO SMS] Credentials not configured. Falling back to console logging.")
            return ConsoleNotifier().send(recipient, subject, body_text, body_html, extra_data)

        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            message = client.messages.create(
                body=body_text,
                from_=from_number,
                to=recipient,
            )
            return NotificationResult(
                success=True,
                provider="twilio_sms",
                provider_message_id=message.sid,
            )
        except Exception as e:
            err_str = str(e)
            is_transient = "500" in err_str or "429" in err_str or "timeout" in err_str.lower()
            logger.error(f"[TWILIO SMS] Error sending to {recipient}: {err_str}")
            return NotificationResult(
                success=False,
                provider="twilio_sms",
                error=err_str,
                is_transient=is_transient,
            )


class TwilioWhatsappNotifier(BaseNotifier):
    """Twilio WhatsApp notifier (flag-gated by WHATSAPP_ENABLED)."""

    def send(
        self,
        recipient: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ) -> NotificationResult:
        whatsapp_enabled = getattr(settings, "WHATSAPP_ENABLED", False) or (os.getenv("WHATSAPP_ENABLED", "false").lower() == "true")
        if not whatsapp_enabled:
            return NotificationResult(
                success=False,
                provider="twilio_whatsapp",
                error="WhatsApp notifications are currently disabled (WHATSAPP_ENABLED=False).",
                is_transient=False,
            )

        account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None) or os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None) or os.getenv("TWILIO_AUTH_TOKEN")
        from_whatsapp = getattr(settings, "TWILIO_WHATSAPP_NUMBER", None) or os.getenv("TWILIO_WHATSAPP_NUMBER")

        if not (account_sid and auth_token and from_whatsapp):
            logger.warning("[TWILIO WHATSAPP] Credentials not configured. Falling back to console logging.")
            return ConsoleNotifier().send(recipient, subject, body_text, body_html, extra_data)

        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            to_addr = recipient if recipient.startswith("whatsapp:") else f"whatsapp:{recipient}"
            from_addr = from_whatsapp if from_whatsapp.startswith("whatsapp:") else f"whatsapp:{from_whatsapp}"
            message = client.messages.create(
                body=body_text,
                from_=from_addr,
                to=to_addr,
            )
            return NotificationResult(
                success=True,
                provider="twilio_whatsapp",
                provider_message_id=message.sid,
            )
        except Exception as e:
            err_str = str(e)
            is_transient = "500" in err_str or "429" in err_str or "timeout" in err_str.lower()
            return NotificationResult(
                success=False,
                provider="twilio_whatsapp",
                error=err_str,
                is_transient=is_transient,
            )


def get_notifier(channel: str) -> BaseNotifier:
    """Factory method to get notifier adapter by channel name."""
    ch = channel.lower()
    if ch == "smtp":
        return SmtpNotifier()
    elif ch == "webhook":
        return WebhookNotifier()
    elif ch == "twilio_sms":
        return TwilioSmsNotifier()
    elif ch == "twilio_whatsapp":
        return TwilioWhatsappNotifier()
    else:
        return ConsoleNotifier()
