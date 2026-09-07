"""
Meta WhatsApp webhook endpoints.

GET  /webhooks/whatsapp — hub.challenge verification (called once when you register the webhook in Meta Developer Console)
POST /webhooks/whatsapp — receives delivery status updates (sent, delivered, read, failed) and
                          flips notification_logs.status accordingly
"""

import hashlib
import hmac
import logging

from fastapi import APIRouter, Request, Response, HTTPException
from sqlalchemy.orm import Session

from core.config import settings
from database.session import SessionLocal
from models.notification_log import NotificationLog, NotificationStatus

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Hub verification (GET)
# ---------------------------------------------------------------------------

@router.get("/whatsapp")
async def verify_whatsapp_webhook(request: Request):
    """
    Meta sends a GET with hub.mode=subscribe, hub.verify_token, and hub.challenge
    when you first register or update the webhook in Meta Developer Console.
    Respond with hub.challenge as plain text to confirm ownership.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if not (mode and token and challenge):
        raise HTTPException(status_code=400, detail="Missing hub.* parameters")

    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("[WA WEBHOOK] Hub challenge verified OK")
        return Response(content=challenge, media_type="text/plain")

    logger.warning(f"[WA WEBHOOK] Verification failed: mode={mode!r} token={token!r}")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


# ---------------------------------------------------------------------------
# Delivery status updates (POST)
# ---------------------------------------------------------------------------

@router.post("/whatsapp")
async def receive_whatsapp_webhook(request: Request):
    """
    Meta sends delivery status updates here (sent → delivered → read, or failed).
    We verify the X-Hub-Signature-256 HMAC before processing anything.
    """
    raw_body = await request.body()

    # --- HMAC signature verification ---
    app_secret = settings.META_WHATSAPP_TOKEN  # App Secret (not the page token)
    sig_header = request.headers.get("X-Hub-Signature-256", "")
    if app_secret and sig_header:
        expected = "sha256=" + hmac.new(
            app_secret.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig_header, expected):
            logger.warning("[WA WEBHOOK] HMAC mismatch — ignoring payload")
            raise HTTPException(status_code=401, detail="Signature mismatch")
    elif not app_secret:
        # App secret not configured — log but don't block (allows local dev)
        logger.warning("[WA WEBHOOK] META_WHATSAPP_TOKEN not set; skipping HMAC check")

    # --- Parse payload ---
    try:
        payload = await request.json()
    except Exception:
        # Already consumed raw_body above; re-parse
        import json
        payload = json.loads(raw_body)

    _process_statuses(payload)

    # Meta requires a 200 within 20 s or it will retry
    return Response(status_code=200, content="EVENT_RECEIVED")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_WA_STATUS_MAP = {
    "sent":      NotificationStatus.SENT.value,
    "delivered": NotificationStatus.DELIVERED.value,
    "read":      NotificationStatus.DELIVERED.value,   # treat read as delivered
    "failed":    NotificationStatus.FAILED.value,
}


def _process_statuses(payload: dict) -> None:
    """Extract status updates from the Meta payload and update notification_logs."""
    db: Session = SessionLocal()
    try:
        entries = payload.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for status_obj in value.get("statuses", []):
                    wa_msg_id = status_obj.get("id")
                    wa_status = status_obj.get("status", "")
                    new_status = _WA_STATUS_MAP.get(wa_status)

                    if not (wa_msg_id and new_status):
                        continue

                    log = (
                        db.query(NotificationLog)
                        .filter(NotificationLog.provider_message_id == wa_msg_id)
                        .first()
                    )
                    if log:
                        log.status = new_status  # type: ignore
                        if new_status == NotificationStatus.FAILED.value:
                            errors = status_obj.get("errors", [])
                            log.error = errors[0].get("message") if errors else "WhatsApp failed"  # type: ignore
                        db.commit()
                        logger.info(
                            f"[WA WEBHOOK] {wa_msg_id} → {new_status} (log {log.id})"
                        )
    except Exception as e:
        logger.error(f"[WA WEBHOOK] Error processing statuses: {e}")
    finally:
        db.close()
