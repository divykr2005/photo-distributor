from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.dependencies import get_current_user, get_db
from models.event import Event
from models.user import User
from models.upload_batch import UploadBatch
from models.photo import Photo
from models.photo_face import PhotoFace
from models.match import Match
from schemas.upload_batch import UploadBatchCreate, UploadBatchResponse

router = APIRouter()


def _verify_event_owner(db: Session, event_id: UUID, user_id: UUID) -> Event:
    event = (
        db.query(Event)
        .filter(Event.id == event_id, Event.created_by == user_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.post("/events/{event_id}/upload-batches", response_model=UploadBatchResponse, status_code=201)
def create_upload_batch(
    event_id: UUID,
    batch_in: UploadBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_event_owner(db, event_id, current_user.id)
    batch = UploadBatch(
        event_id=event_id,
        created_by=current_user.id,
        total_files=batch_in.total_files,
        received_files=0,
        duplicate_files=0,
        rejected_files=0,
        status="active",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


@router.get("/upload-batches/{batch_id}", response_model=UploadBatchResponse)
def get_upload_batch_status(
    batch_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    batch = db.query(UploadBatch).filter(UploadBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Upload batch not found")

    _verify_event_owner(db, batch.event_id, current_user.id)

    # Derived progress metrics calculated from database queries to prevent counter drift
    processed_count = (
        db.query(func.count(Photo.id))
        .filter(Photo.batch_id == batch_id, Photo.status == "processed")
        .scalar() or 0
    )
    failed_count = (
        db.query(func.count(Photo.id))
        .filter(Photo.batch_id == batch_id, Photo.status == "failed")
        .scalar() or 0
    )
    faces_count = (
        db.query(func.count(PhotoFace.id))
        .join(Photo, Photo.id == PhotoFace.photo_id)
        .filter(Photo.batch_id == batch_id)
        .scalar() or 0
    )
    matches_count = (
        db.query(func.count(Match.id))
        .join(Photo, Photo.id == Match.photo_id)
        .filter(Photo.batch_id == batch_id, Match.decision == "auto_confirmed")
        .scalar() or 0
    )

    resp = UploadBatchResponse.model_validate(batch)
    resp.processed_files = processed_count
    resp.failed_files = failed_count
    resp.faces_found = faces_count
    resp.matches_created = matches_count

    return resp
