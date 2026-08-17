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
        processor = FaceEngine.get_instance()
        embedding, quality_score = processor.process_guest_image(photo_path)

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
