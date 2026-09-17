import logging
import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from core.config import settings
from services.notifier.base import NotificationProvider, NotificationResult

logger = logging.getLogger(__name__)


class ConsoleNotifier:
    """Development-only notifier that exercises delivery without external I/O."""

    def send(
        self,
        recipient: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ) -> NotificationResult:
        # Deliberately avoid logging message bodies because they contain private
        # guest portal and opt-out tokens.
        logger.info("[CONSOLE NOTIFIER] simulated delivery to %s: %s", recipient, subject)
        return NotificationResult(
            success=True,
            provider="console",
            provider_message_id=f"console_{uuid.uuid4().hex[:12]}",
        )


class SmtpNotifier:
    """SMTP email notifier. Reads credentials from settings (typed, validated at startup)."""

    def send(
        self,
        recipient: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ) -> NotificationResult:
        sender = settings.SMTP_FROM or settings.SMTP_USER
        if not settings.SMTP_HOST or not sender:
            logger.error(
                "[SMTP] SMTP_HOST and a sender address are required. Set "
                "SMTP_HOST plus SMTP_FROM or SMTP_USER before sending email."
            )
            return NotificationResult(
                success=False,
                provider="smtp",
                error="SMTP host or sender not configured",
                is_transient=False,
            )

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = recipient

            msg.attach(MIMEText(body_text, "plain"))
            if body_html:
                msg.attach(MIMEText(body_html, "html"))

            if settings.SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
                if settings.SMTP_TLS:
                    server.starttls()

            with server:
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(sender, [recipient], msg.as_string())

            return NotificationResult(
                success=True,
                provider="smtp",
                provider_message_id=f"smtp_{uuid.uuid4().hex[:12]}",
            )
        except (smtplib.SMTPException, TimeoutError, OSError) as e:
            logger.error(f"[SMTP] Transient error sending to {recipient}: {e}")
            return NotificationResult(
                success=False,
                provider="smtp",
                error=str(e),
                is_transient=True,
            )
        except Exception as e:
            logger.error(f"[SMTP] Hard error sending to {recipient}: {e}")
            return NotificationResult(
                success=False,
                provider="smtp",
                error=str(e),
                is_transient=False,
            )


def get_notifier(channel: str) -> NotificationProvider:
    """Factory: return the provider for the given channel name.

    Accepted values: 'smtp', plus 'console' in local development.
    Raises ValueError for unknown channels — no silent console fallback in production.
    """
    ch = channel.lower()
    if ch == "smtp":
        return SmtpNotifier()
    if ch == "console" and settings.ENVIRONMENT == "dev":
        return ConsoleNotifier()
    raise ValueError(
        f"Unknown notification channel: {ch!r}. "
        "Accepted values: 'smtp' (and 'console' in development)."
    )
