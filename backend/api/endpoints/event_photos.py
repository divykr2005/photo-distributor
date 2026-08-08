import os
from uuid import UUID
from typing import List
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from models.user import User
from models.event import Event
from models.event_photo import EventPhoto
from worker.tasks import process_event_photo

router = APIRouter()

@router.post("/{event_id}/photos")
async def upload_event_photos(
    event_id: UUID,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify event exists and belongs to user
    event = db.query(Event).filter(Event.id == event_id, Event.created_by == current_user.id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    upload_dir = Path("uploads/events") / str(event_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded_records = []

    for file in files:
        if not file.content_type.startswith("image/"):
            continue

        file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        
        # Create DB record first to get ID
        event_photo = EventPhoto(
            event_id=event_id,
            uploaded_by=current_user.id,
            file_path="",  # will update after saving
            file_size=0,
            status="pending"
        )
        db.add(event_photo)
        db.commit()
        db.refresh(event_photo)

        # Save file
        filename = f"{event_photo.id}.{file_ext}"
        file_path = upload_dir / filename
        
        content = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        # Update record
        event_photo.file_path = str(file_path).replace("\\", "/")
        event_photo.file_size = len(content)
        db.commit()
        
        # Dispatch background task for matching
        background_tasks.add_task(process_event_photo, str(event_photo.id), str(file_path), db)
        
        uploaded_records.append({
            "id": event_photo.id,
            "file_path": event_photo.file_path,
            "status": "pending"
        })

    return {"uploaded": len(uploaded_records), "photos": uploaded_records}
