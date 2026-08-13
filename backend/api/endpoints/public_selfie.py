import hashlib
import logging
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from api.dependencies import get_db
from models.event import Event
from schemas.selfie_search import PublicEventInfo, SelfieSearchPhotoItem, SelfieSearchResponse
from services.selfie_service import SelfieSearchService
from worker.face_processor import FaceQualityError

from middleware.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/heic", "image/heif", "image/webp"}


def _get_public_event(db: Session, event_id: UUID) -> Event:
    """Fetch event and verify selfie search is enabled."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event or not event.selfie_search_enabled:
        raise HTTPException(status_code=404, detail="Selfie search is not enabled for this event.")
    return event


@router.get("/events/{event_id}/info", response_model=PublicEventInfo)
def get_public_event_info(
    event_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get public event branding and selfie search status.
    Returns 404 if event is disabled or not found.
    """
    event = _get_public_event(db, event_id)
    return PublicEventInfo(
        id=UUID(str(event.id)),
        title=str(event.title),
        date=cast(Any, event.date),
        selfie_search_enabled=bool(event.selfie_search_enabled),
    )


@router.post("/events/{event_id}/search-selfie", response_model=SelfieSearchResponse)
@limiter.limit("5/minute")
async def search_selfie(
    request: Request,
    event_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Ephemeral selfie search (D22–D24).
    - Image is processed strictly in memory and discarded.
    - Quality gate rejections return HTTP 422 with actionable detail.
    - Results are authorized by a short-lived session token.
    """
    event = _get_public_event(db, event_id)

    # Validate file size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="File size exceeds maximum limit of 10 MB.",
        )

    # Hash IP and user agent for abuse forensics
    client_ip = request.client.host if request.client else "127.0.0.1"
    ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()

    user_agent = request.headers.get("user-agent", "")
    user_agent_hash = hashlib.sha256(user_agent.encode()).hexdigest() if user_agent else None

    service = SelfieSearchService(db)

    try:
        session_id, photos = service.search_by_selfie(
            event=event,
            file_bytes=file_bytes,
            ip_hash=ip_hash,
            user_agent_hash=user_agent_hash,
        )
    except FaceQualityError as fqe:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(fqe),
        )

    api_base = "/api/v1/public"
    photo_items = [
        SelfieSearchPhotoItem(
            id=UUID(str(photo.id)),
            thumb_url=f"{api_base}/media/{photo.id}/thumb?session={session_id}",
            web_url=f"{api_base}/media/{photo.id}/web?session={session_id}",
            taken_at=cast(Any, photo.exif_taken_at),
            filename=str(photo.original_filename) if photo.original_filename else None,
        )
        for photo in photos
    ]

    return SelfieSearchResponse(
        session_id=session_id,
        total=len(photo_items),
        photos=photo_items,
    )
