import os
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from models.event import Event
from models.user import User
from models.photo import Photo
from models.photo_face import PhotoFace
from services.storage import get_storage_backend

router = APIRouter()


def _verify_event_owner(db: Session, event_id: UUID, user_id: UUID) -> Event:
    event = (
        db.query(Event)
        .filter(Event.id == event_id, Event.created_by == user_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=403, detail="Access denied to event media")
    return event


def _serve_key(storage_key: str, media_type: str = "image/jpeg"):
    storage = get_storage_backend()
    
    # Try fetching as bytes (works universally for R2 and Local)
    try:
        data = storage.get(storage_key)
        if data:
            return Response(content=data, media_type=media_type)
    except Exception:
        pass
        
    raise HTTPException(status_code=404, detail="Media file not found")


@router.get("/media/photos/{photo_id}/original")
def get_photo_original(
    photo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    _verify_event_owner(db, photo.event_id, current_user.id) # type: ignore
    return _serve_key(photo.storage_key, media_type=photo.mime_type or "image/jpeg") # type: ignore


@router.get("/media/photos/{photo_id}/web")
def get_photo_web(
    photo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    _verify_event_owner(db, photo.event_id, current_user.id) # type: ignore
    # Photos whose biometric processing is blocked by the consent gate may not
    # have derivatives. Organizers can still view their own uploaded original.
    key = photo.web_key or photo.storage_key
    media_type = "image/jpeg" if photo.web_key else (photo.mime_type or "image/jpeg")
    return _serve_key(key, media_type=media_type) # type: ignore


@router.get("/media/photos/{photo_id}/thumb")
def get_photo_thumb(
    photo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    _verify_event_owner(db, photo.event_id, current_user.id) # type: ignore
    # See get_photo_web: this fallback is ownership-protected and does not
    # perform or expose biometric processing.
    key = photo.thumb_key or photo.storage_key
    media_type = "image/jpeg" if photo.thumb_key else (photo.mime_type or "image/jpeg")
    return _serve_key(key, media_type=media_type) # type: ignore


@router.get("/media/faces/{photo_face_id}")
def get_face_crop(
    photo_face_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    face = db.query(PhotoFace).filter(PhotoFace.id == photo_face_id).first()
    if not face or not face.crop_key:
        raise HTTPException(status_code=404, detail="Face crop not found")
    _verify_event_owner(db, face.event_id, current_user.id) # type: ignore
    return _serve_key(face.crop_key, media_type="image/jpeg") # type: ignore
