import os
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
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
    file_path = storage.get_path(storage_key)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Media file not found")
    return FileResponse(file_path, media_type=media_type)


@router.get("/media/photos/{photo_id}/original")
def get_photo_original(
    photo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    _verify_event_owner(db, photo.event_id, current_user.id)
    return _serve_key(photo.storage_key, media_type=photo.mime_type or "image/jpeg")


@router.get("/media/photos/{photo_id}/web")
def get_photo_web(
    photo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo or not photo.web_key:
        raise HTTPException(status_code=404, detail="Web photo derivative not found")
    _verify_event_owner(db, photo.event_id, current_user.id)
    return _serve_key(photo.web_key, media_type="image/jpeg")


@router.get("/media/photos/{photo_id}/thumb")
def get_photo_thumb(
    photo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo or not photo.thumb_key:
        raise HTTPException(status_code=404, detail="Thumbnail derivative not found")
    _verify_event_owner(db, photo.event_id, current_user.id)
    return _serve_key(photo.thumb_key, media_type="image/jpeg")


@router.get("/media/faces/{photo_face_id}")
def get_face_crop(
    photo_face_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    face = db.query(PhotoFace).filter(PhotoFace.id == photo_face_id).first()
    if not face or not face.crop_key:
        raise HTTPException(status_code=404, detail="Face crop not found")
    _verify_event_owner(db, face.event_id, current_user.id)
    return _serve_key(face.crop_key, media_type="image/jpeg")
