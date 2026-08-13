import os
import re
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.endpoints.public import _validate_access_code
from models.event import Event
from models.match import Match
from models.photo import Photo
from services.storage import get_storage_backend
from services.visibility import visible_matches

router = APIRouter()

CHUNK_SIZE = 1024 * 1024  # 1 MB streaming chunks


def _sanitize_filename(name: str) -> str:
    """Sanitize string for Content-Disposition header."""
    return re.sub(r'[^a-zA-Z0-9_\.-]', '_', name.lower())


def _file_chunk_generator(file_path: str, start: int, length: int, chunk_size: int = CHUNK_SIZE):
    """Generator streaming a byte range from a file in chunks."""
    with open(file_path, "rb") as f:
        f.seek(start)
        remaining = length
        while remaining > 0:
            bytes_to_read = min(chunk_size, remaining)
            chunk = f.read(bytes_to_read)
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


from middleware.rate_limit import limiter, get_token_from_request


@router.get("/photos/{photo_id}/download")
@limiter.limit("30/minute", key_func=get_token_from_request)
def download_public_photo(
    request: Request,
    photo_id: UUID,
    token: Optional[str] = Query(None, description="Access code from magic link"),
    session: Optional[str] = Query(None, description="Selfie search session token"),
    db: Session = Depends(get_db),
):
    """
    Download original photo with access verification (Day 18).
    - Verifies access via magic-link token or selfie search session token.
    - Streams original photo in 1MB chunks with HTTP Range support (206) for mobile resume.
    - Increments download_count on the photo.
    """
    if not token and not session:
        raise HTTPException(status_code=403, detail="Access denied")

    event_title = "event"

    if token:
        # Validate magic link token & guest visibility predicate
        _token_row, guest, event = _validate_access_code(db, token)
        event_title = str(event.title)
        match = (
            visible_matches(db, UUID(str(guest.id)))
            .filter(Match.photo_id == photo_id)
            .first()
        )
        if not match:
            raise HTTPException(status_code=403, detail="Access denied")
    elif session:
        # Validate selfie search session token (D24)
        from services.selfie_service import SelfieSearchService
        service = SelfieSearchService(db)
        if not service.validate_session_photo(session, str(photo_id)):
            raise HTTPException(status_code=403, detail="Access denied")

    # Load photo record
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    storage = get_storage_backend()
    file_path = storage.get_path(str(photo.storage_key))
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Increment photo download count via atomic SQL update
    db.execute(
        text("UPDATE photos SET download_count = download_count + 1 WHERE id = :id"),
        {"id": str(photo_id)},
    )
    db.commit()

    file_size = os.path.getsize(file_path)
    event_slug = _sanitize_filename(str(event_title))
    download_filename = f"{event_slug}-{photo.id}.jpg"

    headers = {
        "Content-Disposition": f'attachment; filename="{download_filename}"',
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, no-transform",
    }

    # Range header handling for mobile resume & 206 Partial Content
    range_header = request.headers.get("range") if request else None

    if range_header and range_header.startswith("bytes="):
        try:
            byte_range = range_header.replace("bytes=", "").split("-")
            start = int(byte_range[0])
            end = int(byte_range[1]) if byte_range[1] else file_size - 1
            if start >= file_size or end >= file_size or start > end:
                raise HTTPException(status_code=416, detail="Requested Range Not Satisfiable")

            length = end - start + 1
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            headers["Content-Length"] = str(length)

            return StreamingResponse(
                _file_chunk_generator(file_path, start, length),
                status_code=206,
                headers=headers,
                media_type=str(photo.mime_type or "image/jpeg"),
            )
        except (ValueError, IndexError):
            pass

    # Full content response (200)
    headers["Content-Length"] = str(file_size)
    return StreamingResponse(
        _file_chunk_generator(file_path, 0, file_size),
        status_code=200,
        headers=headers,
        media_type=str(photo.mime_type or "image/jpeg"),
    )
