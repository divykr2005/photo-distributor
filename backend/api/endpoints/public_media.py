"""
Day 16 — Public media serving (D21).

GET /public/media/{photo_id}/{variant}?token=
  - variant ∈ {thumb, web, original}
  - Re-checks visibility predicate on every request
  - ETag / 304 support
  - Cache-Control: private, max-age=3600
  - Strips EXIF from web and thumb derivatives
  - original only reachable via the download endpoint (Day 18)

GET /public/guest/{access_code}/photos
  - Keyset pagination, 24/page, ?cursor=
"""
import hashlib
import io
import logging
import os
from typing import Any, Optional, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.endpoints.public import _validate_access_code
from models.match import Match
from models.photo import Photo
from schemas.public_guest import PublicGuestPhotosResponse, PublicPhotoItem
from services.storage import get_storage_backend
from services.visibility import visible_matches

logger = logging.getLogger(__name__)

router = APIRouter()

ITEMS_PER_PAGE = 24


def _strip_exif(image_bytes: bytes) -> bytes:
    """Strip EXIF data (especially GPS) from JPEG bytes.
    
    Uses a minimal approach: find the JPEG SOI marker, skip all APP1 (EXIF)
    segments, keep everything else. Works for JPEG only.
    """
    if not image_bytes or len(image_bytes) < 4:
        return image_bytes
    # Check JPEG SOI marker
    if image_bytes[0:2] != b'\xff\xd8':
        return image_bytes  # Not a JPEG, return as-is

    try:
        # Try using Pillow if available for robust EXIF stripping
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        # Create a new image without EXIF
        output = io.BytesIO()
        # Copy image data without metadata
        clean_img = Image.new(img.mode, img.size)
        clean_img.putdata(list(cast(Any, img).getdata()))
        clean_img.save(output, format='JPEG', quality=95)
        return output.getvalue()
    except ImportError:
        # Fallback: strip APP1 segments manually
        result = bytearray(image_bytes[0:2])  # SOI
        i = 2
        while i < len(image_bytes) - 1:
            if image_bytes[i] != 0xFF:
                # Rest is image data
                result.extend(image_bytes[i:])
                break
            marker = image_bytes[i:i+2]
            if marker == b'\xff\xda':  # SOS - start of scan, rest is image data
                result.extend(image_bytes[i:])
                break
            if marker in (b'\xff\xe1',):  # APP1 = EXIF — skip it
                if i + 3 < len(image_bytes):
                    seg_len = int.from_bytes(image_bytes[i+2:i+4], 'big')
                    i += 2 + seg_len
                    continue
            # Keep all other segments
            if i + 3 < len(image_bytes):
                seg_len = int.from_bytes(image_bytes[i+2:i+4], 'big')
                result.extend(image_bytes[i:i+2+seg_len])
                i += 2 + seg_len
            else:
                result.extend(image_bytes[i:])
                break
        return bytes(result)


# ── GET /public/media/{photo_id}/{variant} ──

from middleware.rate_limit import limiter, get_token_from_request

@router.get("/media/{photo_id}/{variant}")
@limiter.limit("300/minute", key_func=get_token_from_request)
def get_public_media(
    request: Request,
    photo_id: UUID,
    variant: str,
    token: Optional[str] = Query(None, description="Access code from magic link"),
    session: Optional[str] = Query(None, description="Selfie search session token"),
    db: Session = Depends(get_db),
):
    """
    Serve image bytes through a token-verified or session-verified media endpoint.
    No storage keys, filesystem paths, or /static/ mounts exposed (D21, D24).
    """
    if variant not in ("thumb", "web"):
        raise HTTPException(
            status_code=400,
            detail="Invalid variant. Use 'thumb' or 'web'. Original files are available via the download endpoint.",
        )

    if not token and not session:
        raise HTTPException(status_code=403, detail="Access denied")

    authorized = False

    if token:
        _token_row, guest, event = _validate_access_code(db, token)
        match = (
            visible_matches(db, UUID(str(guest.id)))
            .filter(Match.photo_id == photo_id)
            .first()
        )
        if match:
            authorized = True
    elif session:
        from services.selfie_service import SelfieSearchService
        service = SelfieSearchService(db)
        if service.validate_session_photo(session, str(photo_id)):
            authorized = True

    if not authorized:
        raise HTTPException(status_code=403, detail="Access denied")

    # Load photo record
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # Pick storage key based on variant
    if variant == "thumb":
        storage_key = photo.thumb_key
    elif variant == "web":
        storage_key = photo.web_key
    else:
        raise HTTPException(status_code=400, detail="Invalid variant")

    if not storage_key:
        # Fallback to original if derivative doesn't exist
        storage_key = photo.storage_key

    storage = get_storage_backend()
    try:
        image_bytes = storage.get(str(storage_key))
        if not image_bytes:
            raise HTTPException(status_code=404, detail="Media file not found")
    except Exception:
        raise HTTPException(status_code=404, detail="Media file not found")

    # Generate ETag from length and variant
    etag = f'"{hashlib.md5(f"{len(image_bytes)}:{photo_id}:{variant}".encode()).hexdigest()}"'

    # Check If-None-Match for 304
    if request:
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and if_none_match == etag:
            return Response(status_code=304, headers={
                "ETag": etag,
                "Cache-Control": "private, max-age=3600",
            })

    # Strip EXIF (especially GPS) from web and thumb — D16 requirement
    image_bytes = _strip_exif(image_bytes)

    return Response(
        content=image_bytes,
        media_type=str(photo.mime_type or "image/jpeg"),
        headers={
            "ETag": etag,
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        },
    )


# ── GET /public/guest/{access_code}/photos ──

@router.get("/guest/{access_code}/photos", response_model=PublicGuestPhotosResponse)
def get_public_guest_photos(
    access_code: str,
    cursor: str | None = Query(None, description="Keyset cursor for pagination"),
    show_all: bool = Query(False, description="If true, show all visible photos. If false, show only the best of burst (cluster_rank=1)."),
    db: Session = Depends(get_db),
):
    """
    Paginated list of a guest's visible photos (24/page, keyset pagination).
    Returns photo IDs + variant URLs only — never storage keys (D30).
    """
    _token_row, guest, event = _validate_access_code(db, access_code)

    # Base query: visible matches ordered by similarity desc
    query = (
        visible_matches(db, UUID(str(guest.id)))
        .join(Photo, Match.photo_id == Photo.id)
        .with_entities(
            Match.photo_id,
            Match.similarity,
            Match.cluster_rank,
            Photo.original_filename,
            Photo.exif_taken_at,
        )
    )

    if not show_all:
        # Show only the best photos (cluster_rank = 1) or those not yet ranked
        query = query.filter((Match.cluster_rank == 1) | (Match.cluster_rank.is_(None)))

    query = query.order_by(Match.similarity.desc(), Match.photo_id)

    # Keyset pagination: cursor is "similarity:photo_id"
    if cursor:
        try:
            parts = cursor.split(":")
            cursor_sim = float(parts[0])
            cursor_id = parts[1]
            query = query.filter(
                (Match.similarity < cursor_sim) |
                ((Match.similarity == cursor_sim) & (Match.photo_id > cursor_id))
            )
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="Invalid cursor format")

    rows = query.limit(ITEMS_PER_PAGE + 1).all()

    has_more = len(rows) > ITEMS_PER_PAGE
    page_rows = rows[:ITEMS_PER_PAGE]

    # Build public photo items — URLs use the public media endpoint
    api_base = "/api/v1/public"
    photos = [
        PublicPhotoItem(
            id=row.photo_id,
            thumb_url=f"{api_base}/media/{row.photo_id}/thumb?token={access_code}",
            web_url=f"{api_base}/media/{row.photo_id}/web?token={access_code}",
            taken_at=row.exif_taken_at,
            filename=row.original_filename,
        )
        for row in page_rows
    ]

    # Build next cursor
    next_cursor = None
    if has_more and page_rows:
        last = page_rows[-1]
        next_cursor = f"{last.similarity}:{last.photo_id}"

    total = visible_matches(db, UUID(str(guest.id))).count()

    return PublicGuestPhotosResponse(
        photos=photos,
        total=total,
        next_cursor=next_cursor,
    )
