import os
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from models.event import Event
from models.user import User
from repositories.guest_repository import GuestRepository
from schemas.guest import GuestCreate, GuestResponse, GuestUpdate

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "guests")


def _verify_event_owner(db: Session, event_id: UUID, user_id: UUID) -> Event:
    """Ensure the event exists and belongs to the current user."""
    event = db.query(Event).filter(Event.id == event_id, Event.created_by == user_id).first()
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
    return repo.create(guest_in)


@router.get("/", response_model=list[GuestResponse])
def list_guests(
    event_id: UUID | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = GuestRepository(db)
    return repo.search(current_user.id, query=search, event_id=event_id)


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
    # Verify ownership through event
    _verify_event_owner(db, guest.event_id, current_user.id)
    return guest


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
    return repo.update(guest, guest_in)


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
    # Validate file type
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, or WebP images are accepted")

    # Validate file size (5MB max)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be under 5MB")

    repo = GuestRepository(db)
    guest = repo.get_by_id(guest_id)
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")
    _verify_event_owner(db, guest.event_id, current_user.id)

    # Save file
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    return repo.update_image(guest, f"uploads/guests/{filename}")
