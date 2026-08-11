import os
from uuid import UUID
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from models.user import User
from models.event import Event
from models.event_photo import EventPhoto
from models.photo_match import PhotoMatch
from repositories.event_photo_repository import EventPhotoRepository
from repositories.photo_match_repository import PhotoMatchRepository
from worker.tasks import process_event_photo_task

router = APIRouter()


@router.post("/{event_id}/photos")
async def upload_event_photos(
    event_id: UUID,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk upload event photos. Each photo is dispatched to Celery for face matching."""
    # Verify event exists and belongs to user
    event = db.query(Event).filter(Event.id == event_id, Event.created_by == current_user.id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    upload_dir = Path("uploads/events") / str(event_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    photo_repo = EventPhotoRepository(db)
    uploaded_records = []

    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            continue

        content = await file.read()

        # Reject oversized files (20 MB per photo)
        if len(content) > 20 * 1024 * 1024:
            continue

        file_ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"

        # Create DB record
        event_photo = photo_repo.create(
            event_id=event_id,
            uploaded_by=current_user.id,
            file_path="",  # updated after save
            file_size=len(content),
        )

        # Save file
        filename = f"{event_photo.id}.{file_ext}"
        file_path = upload_dir / filename

        with open(file_path, "wb") as buffer:
            buffer.write(content)

        # Update file path
        event_photo.file_path = str(file_path).replace("\\", "/")
        db.commit()

        # Dispatch to Celery for face matching
        process_event_photo_task.delay(str(event_photo.id))

        uploaded_records.append({
            "id": str(event_photo.id),
            "file_path": event_photo.file_path,
            "file_size": event_photo.file_size,
            "status": "pending",
        })

    return {"uploaded": len(uploaded_records), "photos": uploaded_records}


@router.get("/{event_id}/photos")
def list_event_photos(
    event_id: UUID,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all photos for an event with pagination and optional status filter."""
    event = db.query(Event).filter(Event.id == event_id, Event.created_by == current_user.id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    photo_repo = EventPhotoRepository(db)
    skip = (page - 1) * page_size
    photos, total = photo_repo.get_by_event(event_id, status=status, skip=skip, limit=page_size)

    return {
        "data": [
            {
                "id": str(p.id),
                "file_path": p.file_path,
                "file_size": p.file_size,
                "faces_detected": p.faces_detected,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in photos
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{event_id}/photos/{photo_id}")
def get_event_photo(
    event_id: UUID,
    photo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single photo with its match results."""
    event = db.query(Event).filter(Event.id == event_id, Event.created_by == current_user.id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    photo_repo = EventPhotoRepository(db)
    photo = photo_repo.get_by_id(photo_id)
    if not photo or photo.event_id != event_id:
        raise HTTPException(status_code=404, detail="Photo not found")

    match_repo = PhotoMatchRepository(db)
    matches = match_repo.get_by_photo(photo_id)

    return {
        "id": str(photo.id),
        "event_id": str(photo.event_id),
        "file_path": photo.file_path,
        "file_size": photo.file_size,
        "faces_detected": photo.faces_detected,
        "status": photo.status,
        "created_at": photo.created_at.isoformat() if photo.created_at else None,
        "matches": [
            {
                "guest_id": str(m.guest_id),
                "guest_name": f"{m.guest.first_name} {m.guest.last_name}" if m.guest else "Unknown",
                "confidence": round(m.confidence, 4),
                "face_index": m.face_index,
                "is_solo": m.is_solo,
            }
            for m in matches
        ],
    }


@router.get("/{event_id}/photos/{photo_id}/matches")
def get_photo_matches(
    event_id: UUID,
    photo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all matched guests for a specific photo."""
    event = db.query(Event).filter(Event.id == event_id, Event.created_by == current_user.id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    photo_repo = EventPhotoRepository(db)
    photo = photo_repo.get_by_id(photo_id)
    if not photo or photo.event_id != event_id:
        raise HTTPException(status_code=404, detail="Photo not found")

    match_repo = PhotoMatchRepository(db)
    matches = match_repo.get_by_photo(photo_id)

    return {
        "photo_id": str(photo_id),
        "total_matches": len(matches),
        "matches": [
            {
                "guest_id": str(m.guest_id),
                "guest_name": f"{m.guest.first_name} {m.guest.last_name}" if m.guest else "Unknown",
                "guest_image": m.guest.image_path if m.guest else None,
                "confidence": round(m.confidence, 4),
                "face_index": m.face_index,
                "is_solo": m.is_solo,
            }
            for m in matches
        ],
    }
