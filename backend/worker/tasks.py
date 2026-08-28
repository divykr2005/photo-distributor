import logging
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
        
        actual_path = photo_path
        if hasattr(storage, "_get_full_path"):
            actual_path = storage._get_full_path(photo_path)
            
        embedding, quality_score = processor.process_guest_image(actual_path)

        emb_repo.create(
            guest_id=guest.id,  # type: ignore
            embedding=embedding,
            quality_score=quality_score,
        )
        emb_repo.set_guest_embedding_status(guest, EmbeddingStatus.SUCCESS)
        logger.info(f"Embedding stored for guest {guest_id} (quality={quality_score})")

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
    import io
    import tempfile
    import os
    
    db = SessionLocal()
    storage = get_storage_backend()
    try:
        photo_bytes = storage.get(storage_key)
        if not photo_bytes:
            logger.error(f"process_guest_registration_photo_task: Photo not found in storage: {storage_key}")
            return
            
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
        raise
    finally:
        db.close()

@celery_app.task(
    name="worker.tasks.process_event_photo_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_event_photo_task(self, photo_id: str) -> dict:
    """
    Celery task: detect faces in an event photo, match against registered
    guest embeddings via pgvector cosine similarity, and store matches.
    """
    from database.session import SessionLocal
    from services.matching_service import MatchingService

    db = SessionLocal()
    try:
        service = MatchingService(db)
        result = service.process_photo(photo_id)  # type: ignore
        logger.info(f"process_event_photo_task completed for {photo_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"process_event_photo_task failed for {photo_id}: {e}")
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
    r = redis.Redis.from_url(getattr(settings, "REDIS_URL", "redis://localhost:6379/0"))
    
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
    from googleapiclient.discovery import build
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
            batch.total_files = len(items)
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
                extract_faces.delay(str(photo_id))
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing drive file {item['id']}: {e}")
                if batch:
                    batch.failed_files = batch.failed_files + 1  # type: ignore
                    db.commit()

        if batch:
            batch.status = "completed"
            db.commit()
            
        return {"status": "completed", "processed": processed_count}
    except Exception as e:
        logger.error(f"Drive import task failed: {e}")
        return {"status": "error", "reason": str(e)}
    finally:
        db.close()
