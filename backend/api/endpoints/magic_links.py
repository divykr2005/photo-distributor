"""
Magic link CRUD endpoints (D17–D19).

- POST /events/{event_id}/guests/{guest_id}/magic-link  → generate / rotate
- POST /events/{event_id}/magic-links/bulk              → bulk-generate
- DELETE /events/{event_id}/guests/{guest_id}/magic-link → revoke
- GET /events/{event_id}/guests/{guest_id}/magic-link    → info (no plaintext)
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from core.config import settings
from models.event import Event
from models.guest import Guest
from models.guest_access_token import GuestAccessToken
from models.user import User
from schemas.public_guest import (
    BulkMagicLinkResponse,
    MagicLinkInfo,
    MagicLinkResponse,
)

router = APIRouter()

# D17: secrets.token_urlsafe(16) → 22 chars, 128 bits of entropy
TOKEN_BYTES = 16
# D19: default expiry = event.date + 90 days
DEFAULT_TOKEN_LIFETIME_DAYS = 90


def _hash_token(plaintext: str) -> str:
    """D18: SHA-256 hash for at-rest storage."""
    return hashlib.sha256(plaintext.encode()).hexdigest()


def _generate_token(
    db: Session,
    guest: Guest,
    event: Event,
    created_by: UUID,
) -> tuple[GuestAccessToken, str]:
    """Generate a new access token, revoke any existing live one (rotation)."""
    # Revoke existing live tokens for this guest
    existing = (
        db.query(GuestAccessToken)
        .filter(
            GuestAccessToken.guest_id == guest.id,
            GuestAccessToken.revoked_at.is_(None),
        )
        .all()
    )
    now = datetime.now(timezone.utc)
    for tok in existing:
        tok.revoked_at = now

    # D17: generate plaintext — returned exactly once
    plaintext = secrets.token_urlsafe(TOKEN_BYTES)
    token_hash = _hash_token(plaintext)

    # D19: expires_at = event.date + 90 days
    expires_at = event.date + timedelta(days=DEFAULT_TOKEN_LIFETIME_DAYS)

    token_row = GuestAccessToken(
        guest_id=guest.id,
        event_id=event.id,
        token_hash=token_hash,
        token_prefix=plaintext[:6],
        expires_at=expires_at,
        created_by=created_by,
    )
    db.add(token_row)
    return token_row, plaintext


def _get_event_owned_by(db: Session, event_id: UUID, user_id: UUID) -> Event:
    """Fetch event and verify ownership."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event or event.created_by != user_id:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


# ── Generate / Rotate ──

@router.post(
    "/events/{event_id}/guests/{guest_id}/magic-link",
    response_model=MagicLinkResponse,
    status_code=201,
)
def generate_magic_link(
    event_id: UUID,
    guest_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate or rotate a magic link for a guest. Returns plaintext once."""
    event = _get_event_owned_by(db, event_id, current_user.id)

    guest = db.query(Guest).filter(Guest.id == guest_id, Guest.event_id == event_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")

    token_row, plaintext = _generate_token(db, guest, event, current_user.id)
    db.commit()
    db.refresh(token_row)

    portal_url = f"{settings.FRONTEND_URL}/g/{plaintext}"

    return MagicLinkResponse(
        guest_id=guest.id,
        access_code=plaintext,
        portal_url=portal_url,
        expires_at=token_row.expires_at,
    )


# ── Bulk Generate ──

@router.post(
    "/events/{event_id}/magic-links/bulk",
    response_model=BulkMagicLinkResponse,
)
def bulk_generate_magic_links(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate magic links for all guests missing a live token."""
    event = _get_event_owned_by(db, event_id, current_user.id)

    guests = db.query(Guest).filter(Guest.event_id == event_id).all()

    now = datetime.now(timezone.utc)
    generated = 0
    skipped = 0
    links: list[MagicLinkResponse] = []

    for guest in guests:
        # Check if guest already has a live (non-revoked, non-expired) token
        live_token = (
            db.query(GuestAccessToken)
            .filter(
                GuestAccessToken.guest_id == guest.id,
                GuestAccessToken.revoked_at.is_(None),
                GuestAccessToken.expires_at > now,
            )
            .first()
        )
        if live_token:
            skipped += 1
            continue

        token_row, plaintext = _generate_token(db, guest, event, current_user.id)
        generated += 1
        links.append(
            MagicLinkResponse(
                guest_id=guest.id,
                access_code=plaintext,
                portal_url=f"{settings.FRONTEND_URL}/g/{plaintext}",
                expires_at=token_row.expires_at,
            )
        )

    db.commit()

    return BulkMagicLinkResponse(
        generated=generated,
        skipped=skipped,
        links=links,
    )


# ── Revoke ──

@router.delete(
    "/events/{event_id}/guests/{guest_id}/magic-link",
    status_code=204,
)
def revoke_magic_link(
    event_id: UUID,
    guest_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke all live tokens for a guest."""
    _get_event_owned_by(db, event_id, current_user.id)

    guest = db.query(Guest).filter(Guest.id == guest_id, Guest.event_id == event_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")

    now = datetime.now(timezone.utc)
    live_tokens = (
        db.query(GuestAccessToken)
        .filter(
            GuestAccessToken.guest_id == guest.id,
            GuestAccessToken.revoked_at.is_(None),
        )
        .all()
    )
    for tok in live_tokens:
        tok.revoked_at = now

    db.commit()


# ── Info (no plaintext) ──

@router.get(
    "/events/{event_id}/guests/{guest_id}/magic-link",
    response_model=MagicLinkInfo | None,
)
def get_magic_link_info(
    event_id: UUID,
    guest_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get non-secret metadata about the guest's current magic link."""
    _get_event_owned_by(db, event_id, current_user.id)

    guest = db.query(Guest).filter(Guest.id == guest_id, Guest.event_id == event_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")

    token = (
        db.query(GuestAccessToken)
        .filter(
            GuestAccessToken.guest_id == guest.id,
            GuestAccessToken.revoked_at.is_(None),
        )
        .order_by(GuestAccessToken.created_at.desc())
        .first()
    )
    if not token:
        return None
    return token
