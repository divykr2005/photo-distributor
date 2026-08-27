import os
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from models.event import Event
from models.user import User
from repositories.guest_repository import GuestRepository
from repositories.face_embedding_repository import FaceEmbeddingRepository
from schemas.guest import GuestCreate, GuestResponse, GuestUpdate
from worker.face_processor import FaceQualityError

router = APIRouter()

UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "guests"
)


def _verify_event_owner(db: Session, event_id, user_id) -> Event:
    """Ensure the event exists and belongs to the current user."""
    event = (
        db.query(Event)
        .filter(Event.id == event_id, Event.created_by == user_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.post("/", response_model=GuestResponse, status_code=201)
def create_guest(
    guest_in: GuestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_event_owner(db, guest_in.event_id, current_user.id)
    repo = GuestRepository(db)
    guest = repo.create(guest_in)
    from schemas.guest import GuestResponse
    return GuestResponse.model_validate(guest)


@router.get("/")
def list_guests(
    event_id: UUID | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = GuestRepository(db)
    skip = (page - 1) * page_size
    guests, total = repo.search(
        current_user.id, query=search, event_id=event_id, skip=skip, limit=page_size  # type: ignore
    )
    from schemas.guest import GuestResponse
    guests_data = [GuestResponse.model_validate(g) for g in guests]
    return {"data": guests_data, "total": total, "page": page, "page_size": page_size}


@router.get("/{guest_id}", response_model=GuestResponse)
def get_guest(
    guest_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = GuestRepository(db)
    guest = repo.get_by_id(guest_id)
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")
    _verify_event_owner(db, guest.event_id, current_user.id)
    from schemas.guest import GuestResponse
    return GuestResponse.model_validate(guest)


@router.put("/{guest_id}", response_model=GuestResponse)
def update_guest(
    guest_id: UUID,
    guest_in: GuestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = GuestRepository(db)
    guest = repo.get_by_id(guest_id)
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")
    _verify_event_owner(db, guest.event_id, current_user.id)
    guest = repo.update(guest, guest_in)
    from schemas.guest import GuestResponse
    return GuestResponse.model_validate(guest)


@router.delete("/{guest_id}", status_code=204)
def delete_guest(
    guest_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = GuestRepository(db)
    guest = repo.get_by_id(guest_id)
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")
    _verify_event_owner(db, guest.event_id, current_user.id)
    repo.delete(guest)


@router.post("/{guest_id}/photo", response_model=GuestResponse)
async def upload_guest_photo(
    guest_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload (or retake) a guest registration photo.
    - Validates file type and size client- and server-side.
    - Runs the full InsightFace quality gate synchronously.
    - On success: stores embedding in face_embeddings, sets embedding_status=success.
    - On quality failure: returns HTTP 422 with the specific rejection reason.
    """
    # Server-side file validation
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(
            status_code=400, detail="Only JPEG, PNG, or WebP images are accepted."
        )

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be under 5 MB.")

    guest_repo = GuestRepository(db)
    guest = guest_repo.get_by_id(guest_id)
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")
    _verify_event_owner(db, guest.event_id, current_user.id)

    # Persist file to disk
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = (
        file.filename.rsplit(".", 1)[-1]
        if file.filename and "." in file.filename
        else "jpg"
    )
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    # Update image_path on guest record immediately
    storage_key = f"uploads/guests/{filename}"
    guest = guest_repo.update_image(guest, storage_key)

    # Run embedding pipeline synchronously (Celery is out of scope for Week 1)
    from worker.tasks import process_guest_registration_photo

    try:
        process_guest_registration_photo(str(guest_id), filepath, db)
    except (FaceQualityError, ValueError) as e:
        # Quality gate rejected — surface the specific reason with 422
        raise HTTPException(status_code=422, detail=str(e))

    # Re-fetch to return updated embedding_status
    db.refresh(guest)
    return guest
