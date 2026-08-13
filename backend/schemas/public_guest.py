"""
D30 — Public response serializer.

Whitelisted fields only: first name, event title/date, photo count, photo IDs
+ variant URLs.  Never: embeddings, phone, email, notes, other guests,
internal IDs of matches, similarity scores, storage keys.
"""
from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class PublicPhotoItem(BaseModel):
    """Minimal photo representation for the public portal."""
    id: UUID
    thumb_url: str
    web_url: str
    taken_at: Optional[datetime] = None
    filename: Optional[str] = None


class PublicGuestPortal(BaseModel):
    """Returned by GET /public/guest/{access_code} — the portal entry point."""
    first_name: str
    event_title: str
    event_date: datetime
    photo_count: int


class PublicGuestPhotosResponse(BaseModel):
    """Returned by GET /public/guest/{access_code}/photos — paginated photo list."""
    photos: list[PublicPhotoItem]
    total: int
    next_cursor: Optional[str] = None


class MagicLinkResponse(BaseModel):
    """Returned once at generation time — the only time the plaintext token is exposed."""
    guest_id: UUID
    access_code: str
    portal_url: str
    expires_at: datetime


class MagicLinkInfo(BaseModel):
    """Non-secret metadata about a magic link (no plaintext token)."""
    id: UUID
    guest_id: UUID
    token_prefix: str
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None
    access_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class BulkMagicLinkResponse(BaseModel):
    """Returned by POST /events/{event_id}/magic-links/bulk."""
    generated: int
    skipped: int
    links: list[MagicLinkResponse]
