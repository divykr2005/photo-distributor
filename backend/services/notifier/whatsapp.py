import logging
import uuid
from typing import Optional

import requests

from core.config import settings
from services.notifier.base import NotificationResult

logger = logging.getLogger(__name__)


class MetaWhatsAppProvider:
    """Meta WhatsApp Business API notifier.

    Uses approved utility templates only — raw text messages outside a 24-hour
    customer-service window require a pre-approved template.
    """

    def send(
        self,
        recipient: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ) -> NotificationResult:
        if not settings.META_WHATSAPP_TOKEN or not settings.META_WHATSAPP_PHONE_ID:
            logger.error(
                "[META_WA] META_WHATSAPP_TOKEN and META_WHATSAPP_PHONE_ID are not configured."
            )
            return NotificationResult(
                success=False,
                provider="meta_whatsapp",
                error="META_WHATSAPP credentials not configured",
                is_transient=False,
            )

        # Normalise to E.164 without leading + (Meta API requirement)
        import phonenumbers
        try:
            parsed = phonenumbers.parse(recipient)
            e164_num = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            to_number = e164_num.lstrip("+")
        except phonenumbers.phonenumberutil.NumberParseException:
            # Fallback to basic stripping if it can't be parsed
            to_number = recipient.lstrip("+").replace(" ", "").replace("-", "")

        url = f"https://graph.facebook.com/v19.0/{settings.META_WHATSAPP_PHONE_ID}/messages"
        headers = {
            "Authorization": f"Bearer {settings.META_WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }

        # Prefer explicit template override from extra_data; fall back to configured default.
        extra = extra_data or {}
        use_template = extra.get("use_template", True)

        if use_template:
            template_name = extra.get("template_name", settings.META_WHATSAPP_TEMPLATE_NAME)
            language_code = extra.get("language_code", settings.META_WHATSAPP_TEMPLATE_LANG)
            # Template components (URL button parameter) injected via extra_data["components"]
            components = extra.get("components", [])
            payload: dict = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": language_code},
                },
            }
            if components:
                payload["template"]["components"] = components
        else:
            # Free-form text — only works within a 24-hour customer-service window.
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to_number,
                "type": "text",
                "text": {"preview_url": False, "body": body_text},
            }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=10)

            if resp.status_code in (429, 500, 502, 503, 504):
                return NotificationResult(
                    success=False,
                    provider="meta_whatsapp",
                    error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    is_transient=True,
                )
            if resp.status_code >= 400:
                return NotificationResult(
                    success=False,
                    provider="meta_whatsapp",
                    error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    is_transient=False,
                )

            data = resp.json()
            messages = data.get("messages", [])
            msg_id = messages[0].get("id") if messages else f"wa_{uuid.uuid4().hex[:12]}"
            return NotificationResult(
                success=True,
                provider="meta_whatsapp",
                provider_message_id=msg_id,
            )

        except requests.Timeout:
            return NotificationResult(
                success=False,
                provider="meta_whatsapp",
                error="Request timed out",
                is_transient=True,
            )
        except requests.RequestException as e:
            return NotificationResult(
                success=False,
                provider="meta_whatsapp",
                error=str(e),
                is_transient=True,
            )
