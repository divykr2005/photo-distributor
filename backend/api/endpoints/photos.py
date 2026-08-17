import os
import uuid
import hashlib
import tempfile
from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import exc

from api.dependencies import get_current_user, get_db
from models.event import Event
from models.user import User
from models.upload_batch import UploadBatch
from models.photo import Photo
from models.photo_face import PhotoFace
from schemas.photo import PhotoUploadResponse, PhotoResponse, PhotoListResponse
from services.storage import get_storage_backend

router = APIRouter()

MAX_PHOTO_MB = 25
MAX_PHOTO_BYTES = MAX_PHOTO_MB * 1024 * 1024


def _verify_event_owner(db: Session, event_id: UUID, user_id: UUID) -> Event:
    event = (
        db.query(Event)
        .filter(Event.id == event_id, Event.created_by == user_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def _detect_mime_type(header: bytes) -> Optional[str]:
    """Validate image magic bytes."""
    if len(header) < 12:
        return None

    # JPEG
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    # PNG
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    # HEIC / HEIF
    if header[4:8] == b"ftyp":
        brand = header[8:12]
        if brand in (b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"):
            return "image/heic"
    return None


@router.post("/events/{event_id}/photos", response_model=PhotoUploadResponse, status_code=200)
async def upload_photo(
    event_id: UUID,
    file: UploadFile = File(...),
    batch_id: Optional[UUID] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_event_owner(db, event_id, current_user.id)  # type: ignore

    if batch_id:
        batch = db.query(UploadBatch).filter(UploadBatch.id == batch_id, UploadBatch.event_id == event_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")

    # Step 1 & 2: Stream request in 1MB chunks to a temp file
    sha256_hash = hashlib.sha256()
    bytes_received = 0
    header_bytes = bytearray()

    tmp_file = tempfile.NamedTemporaryFile(delete=False, prefix="event-upload-", suffix=".tmp")
    tmp_path = tmp_file.name

    try:
        while True:
            chunk = await file.read(1024 * 1024)  # 1MB chunk
            if not chunk:
                break
            bytes_received += len(chunk)
            if bytes_received > MAX_PHOTO_BYTES:
                if batch_id:
                    batch = db.query(UploadBatch).filter(UploadBatch.id == batch_id).first()
                    if batch:
                        batch.rejected_files = batch.rejected_files + 1  # type: ignore
                        db.commit()
                raise HTTPException(status_code=400, detail=f"File exceeds limit of {MAX_PHOTO_MB}MB.")

            sha256_hash.update(chunk)
            tmp_file.write(chunk)

            if len(header_bytes) < 12:
                header_bytes.extend(chunk[:12 - len(header_bytes)])

        tmp_file.close()

        # Step 3: Validate magic bytes
        mime_type = _detect_mime_type(bytes(header_bytes))
        if not mime_type:
            os.unlink(tmp_path)
            if batch_id:
                batch = db.query(UploadBatch).filter(UploadBatch.id == batch_id).first()
                if batch:
                    batch.rejected_files = batch.rejected_files + 1  # type: ignore
                    db.commit()
            raise HTTPException(status_code=400, detail="Invalid image file format. Only JPEG, PNG, HEIC are accepted.")

        content_hash = sha256_hash.hexdigest()
        original_filename = file.filename or "photo.jpg"
        ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "jpg"
        if mime_type == "image/heic" and ext not in ("heic", "heif"):
            ext = "heic"

        # Step 5: Check existing duplicate photo
        existing_photo = (
            db.query(Photo)
            .filter(Photo.event_id == event_id, Photo.content_hash == content_hash)
            .first()
        )
        if existing_photo:
            os.unlink(tmp_path)
            if batch_id:
                batch = db.query(UploadBatch).filter(UploadBatch.id == batch_id).first()
                if batch:
                    batch.duplicate_files = batch.duplicate_files + 1  # type: ignore
                    batch.received_files = batch.received_files + 1  # type: ignore
                    db.commit()
            return PhotoUploadResponse(photo_id=existing_photo.id, duplicate=True)  # type: ignore

        # Step 6: Create database record atomically
        photo_id = uuid.uuid4()
        storage_key = f"events/{event_id}/photos/{photo_id}/original.{ext}"

        photo = Photo(
            id=photo_id,
            event_id=event_id,
            batch_id=batch_id,
            uploaded_by=current_user.id,
            original_filename=original_filename,
            storage_key=storage_key,
            content_hash=content_hash,
            mime_type=mime_type,
            file_size=bytes_received,
            status="pending",
            attempts=0,
        )
        db.add(photo)
        if batch_id:
            batch = db.query(UploadBatch).filter(UploadBatch.id == batch_id).first()
            if batch:
                batch.received_files = batch.received_files + 1  # type: ignore
        
        try:
            db.commit()
        except exc.IntegrityError:
            db.rollback()
            os.unlink(tmp_path)
            existing = (
                db.query(Photo)
                .filter(Photo.event_id == event_id, Photo.content_hash == content_hash)
                .first()
            )
            if existing:
                return PhotoUploadResponse(photo_id=existing.id, duplicate=True)  # type: ignore
            raise HTTPException(status_code=500, detail="Database insertion conflict.")

        # Step 7: Move temp file to final storage key & enqueue processing
        storage = get_storage_backend()
        with open(tmp_path, "rb") as f:
            storage.put(storage_key, f)
        os.unlink(tmp_path)

        # Enqueue Celery task asynchronously
        try:
            from workers.faces import extract_faces
            extract_faces.delay(str(photo_id))
        except Exception:
            pass

        return PhotoUploadResponse(photo_id=photo_id, duplicate=False)

    except HTTPException:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        raise
    except Exception as e:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/events/{event_id}/photos", response_model=PhotoListResponse)
def list_event_photos(
    event_id: UUID,
    status: Optional[str] = Query(None),
    face_count_zero: Optional[bool] = Query(None),
    group_duplicates: Optional[bool] = Query(None),
    cursor: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_event_owner(db, event_id, current_user.id)  # type: ignore

    query = db.query(Photo).filter(Photo.event_id == event_id)

    if status:
        query = query.filter(Photo.status == status)

    if face_count_zero is True:
        query = query.filter(Photo.face_count == 0)
    elif face_count_zero is False:
        query = query.filter(Photo.face_count > 0)
        
    if group_duplicates:
        query = query.filter(
            (Photo.dup_cluster_id.is_(None)) | (Photo.is_cluster_representative == True)
        )

    # Keyset pagination on created_at / id
    if cursor:
        try:
            dt_str, id_str = cursor.split("|")
            cursor_dt = datetime.fromisoformat(dt_str)
            cursor_id = UUID(id_str)
            query = query.filter(
                (Photo.created_at < cursor_dt) |
                ((Photo.created_at == cursor_dt) & (Photo.id < cursor_id))
            )
        except Exception:
            pass

    query = query.order_by(Photo.created_at.desc(), Photo.id.desc())
    items = query.limit(limit + 1).all()

    has_more = len(items) > limit
    results = items[:limit]

    next_cursor = None
    if has_more and results:
        last = results[-1]
        next_cursor = f"{last.created_at.isoformat()}|{last.id}"

    return PhotoListResponse(
        data=[PhotoResponse.model_validate(p) for p in results],
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.delete("/photos/{photo_id}", status_code=204)
def delete_photo(
    photo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    _verify_event_owner(db, photo.event_id, current_user.id)  # type: ignore

    # Gather storage keys before deleting DB row
    keys_to_delete = [photo.storage_key, photo.web_key, photo.thumb_key]
    faces = db.query(PhotoFace).filter(PhotoFace.photo_id == photo_id).all()
    for face in faces:
        if face.crop_key:
            keys_to_delete.append(face.crop_key)

    # DB cascade removes PhotoFaces and Matches automatically
    db.delete(photo)
    db.commit()

    # Storage cleanup
    storage = get_storage_backend()
    for key in keys_to_delete:
        if key:
            storage.delete(str(key))


from pydantic import BaseModel
class BulkDeleteRequest(BaseModel):
    photo_ids: list[UUID]

@router.post("/events/{event_id}/photos/bulk-delete", status_code=204)
def bulk_delete_photos(
    event_id: UUID,
    req: BulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_event_owner(db, event_id, current_user.id)  # type: ignore

    photos = db.query(Photo).filter(Photo.id.in_(req.photo_ids), Photo.event_id == event_id).all()
    
    storage = get_storage_backend()
    keys_to_delete = []
    
    for photo in photos:
        keys_to_delete.extend([photo.storage_key, photo.web_key, photo.thumb_key])
        faces = db.query(PhotoFace).filter(PhotoFace.photo_id == photo.id).all()
        for face in faces:
            if face.crop_key:
                keys_to_delete.append(face.crop_key)
                
        db.delete(photo)

    db.commit()

    for key in keys_to_delete:
        if key:
            storage.delete(str(key))
