import os
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from models.event import Event
from models.user import User
from models.guest import EmbeddingStatus
from repositories.guest_repository import GuestRepository
from repositories.face_embedding_repository import FaceEmbeddingRepository
from schemas.guest import GuestCreate, GuestResponse, GuestUpdate
from worker.face_processor import FaceQualityError
from core.config import settings

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
    if guest_in.biometric_consent:
        if guest_in.biometric_consent_text_version != settings.CURRENT_BIOMETRIC_CONSENT_VERSION:
            raise HTTPException(status_code=400, detail="The biometric consent notice is out of date.")
        from datetime import datetime, timezone
        guest_in = guest_in.model_copy(update={"consent_given_at": datetime.now(timezone.utc)})

    repo = GuestRepository(db)
    guest = repo.create(guest_in)
    if guest_in.biometric_consent:
        from models.consent import BiometricConsent
        db.add(BiometricConsent(
            guest_id=guest.id,
            consent_text_version=settings.CURRENT_BIOMETRIC_CONSENT_VERSION,
            phone_e164=guest.phone,
            given_at=guest.consent_given_at,
            notice_text_snapshot=(
                "The guest explicitly consented to facial-feature processing for "
                "event photo matching and delivery."
            ),
        ))
        db.commit()
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


@router.patch("/{guest_id}", response_model=GuestResponse)
def update_guest(
    guest_id: UUID,
    guest_in: GuestUpdate,
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = GuestRepository(db)
    guest = repo.get_by_id(guest_id)
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")
    _verify_event_owner(db, guest.event_id, current_user.id)

    # Optimistic concurrency check
    if if_match:
        # Strip quotes if provided by client (e.g., '"2024-..."' -> '2024-...')
        client_etag = if_match.strip('"')
        server_etag = str(guest.updated_at.timestamp())
        if client_etag != server_etag:
            raise HTTPException(status_code=412, detail="Precondition Failed: Resource has been modified")

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


@router.delete("/{guest_id}/biometrics", status_code=204)
def purge_guest_biometrics(
    guest_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Purge a guest's biometric data (face embeddings + raw selfie) while
    retaining the guest record itself. Use for right-to-erasure requests or
    post-event retention policy enforcement.
    """
    repo = GuestRepository(db)
    guest = repo.get_by_id(guest_id)
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")
    _verify_event_owner(db, guest.event_id, current_user.id)

    # 1. Delete all face_embeddings rows for this guest
    emb_repo = FaceEmbeddingRepository(db)
    emb_repo.delete_by_guest(guest_id)

    # 1.5. Delete all photo matches
    from models.match import Match
    db.query(Match).filter(Match.guest_id == guest_id).delete(synchronize_session=False)

    # 2. Delete the raw selfie from storage (best-effort)
    if guest.image_path:
        try:
            from services.storage import get_storage_backend
            storage = get_storage_backend()
            storage.delete(guest.image_path)
        except Exception:
            pass  # Don't fail the request if storage delete fails
        guest.image_path = None  # type: ignore

    # 3. Reset embedding status and delete crypto keys
    guest.embedding_status = "pending"  # type: ignore
    guest.wrapped_dek = None
    guest.dek_key_id = None

    # 4. Set purged timestamp
    from datetime import datetime, timezone
    guest.biometrics_purged_at = datetime.now(timezone.utc)

    db.commit()



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

    from services.face_presence import contains_face
    if not contains_face(contents):
        if not guest.image_path:
            guest.embedding_status = EmbeddingStatus.NO_FACE  # type: ignore
            db.commit()
        raise HTTPException(
            status_code=422,
            detail="No face detected. Centre the guest's face in the camera and retake the photo.",
        )

    from models.consent import BiometricConsent
    consent = db.query(BiometricConsent).filter(
        BiometricConsent.guest_id == guest_id,
        BiometricConsent.withdrawn_at.is_(None),
        BiometricConsent.consent_text_version == settings.CURRENT_BIOMETRIC_CONSENT_VERSION,
    ).first()
    if not consent:
        raise HTTPException(
            status_code=409,
            detail="Current biometric consent is required before uploading a reference photo.",
        )

    from services.storage import get_storage_backend
    storage = get_storage_backend()

    ext = (
        file.filename.rsplit(".", 1)[-1]
        if file.filename and "." in file.filename
        else "jpg"
    )
    filename = f"{uuid.uuid4()}.{ext}"
    storage_key = f"uploads/guests/{filename}"

    # Upload file to storage
    storage.put(storage_key, contents)

    # Update image_path on guest record immediately
    guest = guest_repo.update_image(guest, storage_key)

    # Run embedding pipeline asynchronously via Celery to prevent Uvicorn OOM
    from worker.tasks import process_guest_registration_photo_task
    process_guest_registration_photo_task.delay(str(guest_id), storage_key)

    # Re-fetch to return updated embedding_status
    db.refresh(guest)
    return guest
