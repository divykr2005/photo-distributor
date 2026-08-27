import os
import uuid
from typing import cast, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from pydantic import EmailStr

from api.dependencies import get_db
from models.event import Event
from repositories.guest_repository import GuestRepository
from schemas.guest import GuestCreate
from worker.face_processor import FaceQualityError

router = APIRouter()

UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "guests"
)

@router.get("/events/{event_id}")
def get_public_event_details(
    event_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Returns basic non-sensitive event details for the public registration page.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    return {
        "id": str(event.id),
        "title": str(event.title),
        "date": cast(Any, event.date),
    }


@router.post("/events/{event_id}/register")
async def public_guest_register(
    event_id: UUID,
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: str = Form(...),
    email: str | None = Form(None),
    gender: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Public endpoint for a guest to register themselves with a selfie.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # File validation
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(
            status_code=400, detail="Only JPEG, PNG, or WebP images are accepted."
        )

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be under 10 MB.")

    # Create the guest record
    repo = GuestRepository(db)
    guest_in = GuestCreate(
        event_id=event_id,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        email=email,
        gender=gender,
    )
    guest = repo.create(guest_in)

    # Persist file
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

    # Update image path
    storage_key = f"uploads/guests/{filename}"
    guest = repo.update_image(guest, storage_key)

    # Synchronously extract embedding
    from worker.tasks import process_guest_registration_photo

    try:
        process_guest_registration_photo(str(guest.id), filepath, db)
    except (FaceQualityError, ValueError) as e:
        # If quality fails, we still created the guest, but embedding failed.
        # It's better to delete the guest so they try again, or just let them retry upload.
        # For public reg, we should rollback or delete the guest so they can fix it immediately.
        repo.delete(guest)
        raise HTTPException(status_code=422, detail=str(e))

    db.refresh(guest)
    
    return {
        "success": True,
        "message": "Registered successfully",
        "guest_id": str(guest.id)
    }
