import logging
from uuid import UUID
from sqlalchemy.orm import Session
from worker.face_processor import FaceProcessor, FaceQualityError
from repositories.guest_repository import GuestRepository
from repositories.face_embedding_repository import FaceEmbeddingRepository
from models.guest import EmbeddingStatus

logger = logging.getLogger(__name__)


def process_guest_registration_photo(guest_id: str, photo_path: str, db: Session) -> None:
    """
    Synchronous task: extract embedding from a guest registration photo.
    Writes to face_embeddings table and updates guest.embedding_status.
    """
    guest_repo = GuestRepository(db)
    emb_repo = FaceEmbeddingRepository(db)

    guest = guest_repo.get_by_id(guest_id)  # type: ignore
    if not guest:
        logger.error(f"Guest {guest_id} not found when processing photo.")
        return

    try:
        from services.face_engine import FaceEngine
        from services.storage import get_storage_backend

        processor = FaceEngine.get_instance()
        storage = get_storage_backend()

        # The Celery wrapper already downloaded storage into a temporary file.
        import os
        actual_path = photo_path
        if not os.path.isabs(photo_path) and hasattr(storage, "_get_full_path"):
            actual_path = storage._get_full_path(photo_path)

        import hashlib

        with open(actual_path, "rb") as f:
            photo_bytes = f.read()

        content_hash = hashlib.sha256(photo_bytes).hexdigest()

        # Deduplicate if we've already processed this exact photo
        existing_embedding = emb_repo.get_latest_by_guest(UUID(str(guest.id)))
        if existing_embedding and getattr(existing_embedding, 'content_hash', None) == content_hash:
            logger.info(f"Skipping processing for guest {guest_id}: identical content hash.")
            return

        embedding, quality_score = processor.process_guest_image(actual_path)

        emb_repo.create(
            guest_id=guest.id,  # type: ignore
            embedding=embedding,
            quality_score=quality_score,
            content_hash=content_hash,
        )
        emb_repo.set_guest_embedding_status(guest, EmbeddingStatus.SUCCESS)
        logger.info(f"Embedding stored for guest {guest_id} (quality={quality_score})")

        try:
            from workers.matching import run_guest_match
            run_guest_match.delay(str(guest.event_id), str(guest.id))
            logger.info(f"Queued match task for new guest {guest_id}")
        except Exception as queue_err:
            logger.error(f"Failed to queue match task for guest {guest_id}: {queue_err}")

    except (FaceQualityError, ValueError) as e:
        error_msg = str(e)
        logger.warning(f"Quality gate failed for guest {guest_id}: {error_msg}")
        emb_repo.set_guest_embedding_status(guest, EmbeddingStatus.FAILED)
        # Re-raise so the endpoint can surface the specific error to the caller
        raise

    except Exception as e:
        logger.error(f"Unexpected error processing embedding for guest {guest_id}: {e}")
        emb_repo.set_guest_embedding_status(guest, EmbeddingStatus.FAILED)
        raise


# ---------------------------------------------------------------------------
# Celery task for event photo processing (Week 2 matching pipeline)
# ---------------------------------------------------------------------------
from core.celery_app import celery_app

@celery_app.task(
    name="worker.tasks.process_guest_registration_photo_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def process_guest_registration_photo_task(self, guest_id: str, storage_key: str) -> None:
    from database.session import SessionLocal
    from services.storage import get_storage_backend
    from models.consent import BiometricConsent
    from core.config import settings
    import io
    import tempfile
    import os

    db = SessionLocal()
    storage = get_storage_backend()
    try:
        # ── P0 Consent gate ──────────────────────────────────────────────────
        # Abort BEFORE touching any storage or model if consent is absent or
        # has been withdrawn. The text version must match the current published
        # notice so that stale consents from an older notice are not honoured.
        consent = (
            db.query(BiometricConsent)
            .filter(BiometricConsent.guest_id == guest_id)
            .order_by(BiometricConsent.given_at.desc())
            .first()
        )
        required_version = getattr(settings, "CURRENT_BIOMETRIC_CONSENT_VERSION", None)
        consent_valid = (
            consent is not None
            and (not hasattr(consent, "withdrawn_at") or consent.withdrawn_at is None)
            and (required_version is None or consent.consent_text_version == required_version)
        )
        if not consent_valid:
            logger.warning(
                "Consent gate: no valid consent for guest %s (required_version=%s). "
                "Embedding extraction aborted.",
                guest_id, required_version,
            )
            GuestRepository(db).update_embedding_status(UUID(guest_id), EmbeddingStatus.FAILED)
            return
        # ─────────────────────────────────────────────────────────────────────

        photo_bytes = storage.get(storage_key)
        if not photo_bytes:
            raise FileNotFoundError(f"Photo not found in storage: {storage_key}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(photo_bytes)
            tmp_path = tmp.name

        try:
            process_guest_registration_photo(guest_id, tmp_path, db)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception as e:
        logger.error(f"process_guest_registration_photo_task failed for {guest_id}: {e}")
        db.rollback()
        GuestRepository(db).update_embedding_status(UUID(guest_id), EmbeddingStatus.FAILED)
        raise
    finally:
        db.close()


@celery_app.task(name="worker.tasks.backfill_hashes")
def backfill_hashes(event_id_str: str) -> dict:
    from database.session import SessionLocal
    from models.photo import Photo
    from services.storage import get_storage_backend
    import io
    from PIL import Image
    from services.hashing import phash_dct, dhash
    from datetime import datetime, timezone

    db = SessionLocal()
    storage = get_storage_backend()
    processed = 0
    try:
        photos = db.query(Photo).filter(
            Photo.event_id == event_id_str,
            Photo.hash_computed_at.is_(None),
            Photo.status == 'processed',
            Photo.web_key.isnot(None)
        ).all()

        for photo in photos:
            web_bytes = storage.get(str(photo.web_key))
            if not web_bytes:
                continue

            img = Image.open(io.BytesIO(web_bytes))
            photo.phash = phash_dct(img)  # type: ignore
            photo.dhash = dhash(img)  # type: ignore
            photo.hash_computed_at = datetime.now(timezone.utc)  # type: ignore
            processed += 1

            if processed % 100 == 0:
                db.commit()

        db.commit()
        return {"status": "completed", "processed": processed}
    except Exception as e:
        logger.error(f"backfill_hashes failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="worker.tasks.cluster_duplicates_task", bind=True)
def cluster_duplicates_task(self, event_id_str: str) -> dict:
    import redis
    from database.session import SessionLocal
    from services.dedup_service import DedupService
    from core.config import settings

    lock_name = f"event:{event_id_str}:dedup_lock"
    from core.config import get_redis_url
    r = redis.Redis.from_url(get_redis_url())

    # Try to acquire lock, non-blocking
    if not r.set(lock_name, "locked", nx=True, ex=300): # 5 min timeout
        logger.warning(f"Dedup task for event {event_id_str} is already running.")
        return {"status": "skipped", "reason": "lock_acquired"}

    db = SessionLocal()
    try:
        service = DedupService(db)
        result = service.cluster_duplicates(event_id_str)
        logger.info(f"cluster_duplicates_task completed for {event_id_str}: {result}")
        return result
    except Exception as e:
        logger.error(f"cluster_duplicates_task failed for {event_id_str}: {e}")
        raise
    finally:
        db.close()
        r.delete(lock_name)


@celery_app.task(name="worker.tasks.import_drive_photos_task", bind=True)
def import_drive_photos_task(self, event_id_str: str, folder_id: str, user_id_str: str, batch_id_str: str) -> dict:
    from googleapiclient.discovery import build  # type: ignore[import]
    from database.session import SessionLocal
    from models.photo import Photo
    from models.upload_batch import UploadBatch
    from core.config import settings
    from services.storage import get_storage_backend
    import uuid
    import hashlib
    import io

    if not settings.GOOGLE_DRIVE_API_KEY:
        logger.error("GOOGLE_DRIVE_API_KEY is not configured")
        return {"status": "error", "reason": "No API key"}

    try:
        service = build('drive', 'v3', developerKey=settings.GOOGLE_DRIVE_API_KEY)
    except Exception as e:
        logger.error(f"Failed to build drive service: {e}")
        return {"status": "error", "reason": str(e)}

    db = SessionLocal()
    storage = get_storage_backend()
    processed_count = 0

    try:
        query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"
        results = service.files().list(q=query, pageSize=1000, fields="nextPageToken, files(id, name, mimeType, size)").execute()
        items = results.get('files', [])

        batch = db.query(UploadBatch).filter(UploadBatch.id == batch_id_str).first()
        if batch:
            batch.total_files = len(items)  # type: ignore[assignment]
            db.commit()

        for item in items:
            try:
                request = service.files().get_media(fileId=item['id'])
                file_bytes = request.execute()

                content_hash = hashlib.sha256(file_bytes).hexdigest()

                existing_photo = (
                    db.query(Photo)
                    .filter(Photo.event_id == event_id_str, Photo.content_hash == content_hash)
                    .first()
                )

                if existing_photo:
                    if batch:
                        batch.duplicate_files = batch.duplicate_files + 1  # type: ignore
                        batch.received_files = batch.received_files + 1  # type: ignore
                        db.commit()
                    continue

                photo_id = uuid.uuid4()
                original_filename = item.get('name', 'drive_photo.jpg')
                ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "jpg"
                storage_key = f"events/{event_id_str}/photos/{photo_id}/original.{ext}"

                storage.put(storage_key, io.BytesIO(file_bytes))

                photo = Photo(
                    id=photo_id,
                    event_id=event_id_str,
                    batch_id=batch_id_str,
                    uploaded_by=user_id_str,
                    original_filename=original_filename,
                    storage_key=storage_key,
                    content_hash=content_hash,
                    mime_type=item.get('mimeType', 'image/jpeg'),
                    file_size=len(file_bytes),
                    status="pending",
                    attempts=0,
                )
                db.add(photo)
                if batch:
                    batch.received_files = batch.received_files + 1  # type: ignore
                db.commit()

                from workers.faces import extract_faces
                from models.event import Event, UploadMode
                _event = db.query(Event).filter(Event.id == event_id_str).first()
                if _event and _event.upload_mode == UploadMode.CONTROLLED:
                    extract_faces.delay(str(photo_id))
                else:
                    logger.info(
                        "Drive import: skipping face extraction for photo %s — "
                        "event %s upload_mode is not 'controlled'.",
                        photo_id, event_id_str,
                    )

                processed_count += 1

            except Exception as e:
                logger.error(f"Error processing drive file {item['id']}: {e}")
                if batch:
                    batch.failed_files = batch.failed_files + 1  # type: ignore
                    db.commit()

        if batch:
            batch.status = "completed"  # type: ignore[assignment]
            db.commit()

        return {"status": "completed", "processed": processed_count}
    except Exception as e:
        logger.error(f"Drive import task failed: {e}")
        return {"status": "error", "reason": str(e)}
    finally:
        db.close()


@celery_app.task(
    name="worker.tasks.process_event_photo_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_event_photo_task(self, event_photo_id: str) -> None:
    """Process an uploaded event photo: detect faces and match against registered guests."""
    from database.session import SessionLocal
    from repositories.event_photo_repository import EventPhotoRepository
    from repositories.face_embedding_repository import FaceEmbeddingRepository
    from repositories.photo_match_repository import PhotoMatchRepository
    from services.face_engine import FaceEngine

    db = SessionLocal()
    try:
        photo_repo = EventPhotoRepository(db)
        photo = photo_repo.get_by_id(UUID(event_photo_id))
        if not photo:
            logger.error("process_event_photo_task: photo %s not found", event_photo_id)
            return

        photo.status = "processing"  # type: ignore[assignment]
        db.commit()

        with open(str(photo.file_path), "rb") as fh:
            raw_bytes = fh.read()

        engine = FaceEngine.get_instance()
        _web, _thumb, _w, _h, _exif, detected_faces = engine.process_photo_bytes(
            raw_bytes, str(photo.event_id), event_photo_id
        )

        emb_repo = FaceEmbeddingRepository(db)
        match_repo = PhotoMatchRepository(db)

        photo.faces_detected = len(detected_faces)  # type: ignore[assignment]
        matched_count = 0

        for face_index, face in enumerate(detected_faces):
            if not face.get("is_matchable", True):
                continue
            matches = emb_repo.find_matches(
                query_embedding=face["embedding"],
                event_id=UUID(str(photo.event_id)),
            )
            for m in matches:
                match_repo.create(
                    event_photo_id=UUID(event_photo_id),
                    guest_id=m["guest_id"],
                    confidence=m["confidence"],
                    face_index=face_index,
                    is_solo=len(detected_faces) == 1,
                )
                matched_count += 1

        photo.status = "success"  # type: ignore[assignment]
        db.commit()
        logger.info(
            "process_event_photo_task: photo %s — %d face(s), %d match(es)",
            event_photo_id, len(detected_faces), matched_count,
        )
    except Exception as exc:
        logger.error("process_event_photo_task failed for %s: %s", event_photo_id, exc)
        db.rollback()
        try:
            photo_repo2 = EventPhotoRepository(db)
            failed_photo = photo_repo2.get_by_id(UUID(event_photo_id))
            if failed_photo:
                failed_photo.status = "failed"  # type: ignore[assignment]
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()
