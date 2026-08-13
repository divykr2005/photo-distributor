"""
Public API endpoints — no JWT, token-validated, hostile-territory rules.

Day 15:
  GET /public/guest/{access_code} — validate token, return PublicGuestSchema + counts

Day 16 will add:
  GET /public/guest/{access_code}/photos — paginated photo list
  GET /public/media/{photo_id}/{variant}?token= — media serving

Day 17 will add:
  POST /public/events/{event_id}/search-selfie

Day 18 will add:
  GET /public/photos/{photo_id}/download?token=

All responses use the D30 whitelisted serializer — never leak embeddings,
phone, email, notes, similarity scores, or storage keys.
"""
import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from api.dependencies import get_db
from models.event import Event
from models.guest import Guest
from models.guest_access_token import GuestAccessToken
from schemas.public_guest import PublicGuestPortal
from services.visibility import visible_match_count

logger = logging.getLogger(__name__)

router = APIRouter()


def _validate_access_code(
    db: Session, access_code: str
) -> tuple[GuestAccessToken, Guest, Event]:
    """
    Validate magic link token string against database.
    - Constant-time hash check
    - Uniform 404 for invalid OR revoked (enumeration defense)
    - 410 for expired
    - Touches last_accessed_at + increments access_count
    Returns (GuestAccessToken, Guest, Event).
    """
    token_hash = hashlib.sha256(access_code.encode()).hexdigest()

    token_row = (
        db.query(GuestAccessToken)
        .filter(GuestAccessToken.token_hash == token_hash)
        .first()
    )

    # Uniform 404 for invalid or revoked — never reveal existence
    if not token_row:
        raise HTTPException(status_code=404, detail="Link not found")

    # Constant-time comparison even though we already found it by hash index
    if not secrets.compare_digest(str(token_row.token_hash), token_hash):
        raise HTTPException(status_code=404, detail="Link not found")

    if token_row.revoked_at is not None:
        raise HTTPException(status_code=404, detail="Link not found")

    # Expired → 410
    now = datetime.now(timezone.utc)
    if token_row.expires_at < now:
        raise HTTPException(
            status_code=410,
            detail="This link has expired. Please contact your event organizer for a new one.",
        )

    # Touch access tracking
    cast(Any, token_row).last_accessed_at = now
    cast(Any, token_row).access_count = (cast(Any, token_row).access_count or 0) + 1

    # Load guest and event
    guest = db.query(Guest).filter(Guest.id == token_row.guest_id).first()
    event = db.query(Event).filter(Event.id == token_row.event_id).first()

    if not guest or not event:
        raise HTTPException(status_code=404, detail="Link not found")

    db.commit()

    # Log with token hash only (never plaintext) — D15 requirement
    logger.info(
        "Public portal access: token_prefix=%s event=%s guest=%s",
        token_row.token_prefix,
        str(event.id),
        str(guest.id),
    )

    return token_row, guest, event


from middleware.rate_limit import limiter

# ── GET /public/guest/{access_code} ──

@router.get("/guest/{access_code}", response_model=PublicGuestPortal)
@limiter.limit("60/minute")
def get_public_guest_portal(
    request: Request,
    access_code: str,
    db: Session = Depends(get_db),
):
    """
    Validate magic link and return portal entry data.
    Returns first name, event info, and visible photo count only (D30).
    """
    _token_row, guest, event = _validate_access_code(db, access_code)

    photo_count = visible_match_count(db, UUID(str(guest.id)))

    return PublicGuestPortal(
        first_name=str(guest.first_name),
        event_title=str(event.title),
        event_date=cast(Any, event.date),
        photo_count=photo_count,
    )
