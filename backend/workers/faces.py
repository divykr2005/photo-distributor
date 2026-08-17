import uuid
import logging
from datetime import datetime, timezone
import redis
from sqlalchemy import text
from celery.signals import worker_process_init

from core.celery_app import celery_app
from database.session import SessionLocal
from models.photo import Photo
from models.photo_face import PhotoFace
from services.storage import get_storage_backend
from core.config import settings

logger = logging.getLogger(__name__)


@worker_process_init.connect
def prewarm_face_engine(**kwargs):
    """Pre-load InsightFace model at worker startup so first task is fast."""
    try:
        from services.face_engine import FaceEngine
        FaceEngine.get_instance()
        logger.info("FaceEngine pre-warmed successfully at worker startup.")
    except Exception as e:
        logger.warning(f"FaceEngine pre-warm failed (will retry on first task): {e}")


@celery_app.task(
    name="workers.faces.extract_faces",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def extract_faces(self, photo_id_str: str) -> dict:
    photo_id = uuid.UUID(photo_id_str)
    db = SessionLocal()
    try:
        # Atomic claim of photo record
        claim_stmt = text("""
            UPDATE photos
            SET status = 'processing',
                attempts = attempts + 1,
                updated_at = NOW()
            WHERE id = :photo_id
              AND status IN ('pending', 'queued', 'failed')
              AND attempts < 3
            RETURNING id, event_id, storage_key;
        """)
        result = db.execute(claim_stmt, {"photo_id": photo_id}).fetchone()
        if not result:
            logger.info(f"Photo {photo_id_str} already claimed, processed, or max attempts reached.")
            return {"status": "skipped"}

        event_id = result.event_id
        storage_key = result.storage_key

        storage = get_storage_backend()
        raw_bytes = storage.get(storage_key)
        if not raw_bytes:
            db.execute(text("UPDATE photos SET status = 'failed', processing_error = 'File not found in storage' WHERE id = :id"), {"id": photo_id})
            db.commit()
            return {"status": "failed", "error": "File not found"}

        # Delete-before-insert idempotency
        db.execute(text("DELETE FROM photo_faces WHERE photo_id = :photo_id"), {"photo_id": photo_id})
        db.commit()

        # Import FaceEngine lazily so worker initializes it once
        from services.face_engine import FaceEngine
        engine = FaceEngine.get_instance()

        web_bytes, thumb_bytes, web_w, web_h, exif_taken_at, detected_faces = engine.process_photo_bytes(
            raw_bytes, str(event_id), str(photo_id)
        )

        import io
        from PIL import Image
        from services.hashing import phash_dct, dhash
        web_img = Image.open(io.BytesIO(web_bytes))
        phash_val = phash_dct(web_img)
        dhash_val = dhash(web_img)

        web_key = f"events/{event_id}/photos/{photo_id}/web.jpg"
        thumb_key = f"events/{event_id}/photos/{photo_id}/thumb.jpg"
        storage.put(web_key, web_bytes)
        storage.put(thumb_key, thumb_bytes)

        # Insert PhotoFaces
        faces_created = 0
        for face_data in detected_faces:
            face_id = uuid.uuid4()
            crop_key = f"events/{event_id}/photos/{photo_id}/faces/{face_id}.jpg"
            storage.put(crop_key, face_data["crop_bytes"])

            photo_face = PhotoFace(
                id=face_id,
                photo_id=photo_id,
                event_id=event_id,
                bbox_x=face_data["bbox_x"],
                bbox_y=face_data["bbox_y"],
                bbox_w=face_data["bbox_w"],
                bbox_h=face_data["bbox_h"],
                det_score=face_data["det_score"],
                embedding=face_data["embedding"],
                model_version="buffalo_l",
                embedding_dim=512,
                quality_score=face_data["quality_score"],
                blur_score=face_data["blur_score"],
                face_area_ratio=face_data["face_area_ratio"],
                yaw=face_data["yaw"],
                pitch=face_data["pitch"],
                roll=face_data["roll"],
                is_matchable=face_data["is_matchable"],
                quality_flags=face_data["quality_flags"],
                crop_key=crop_key,
            )
            db.add(photo_face)
            faces_created += 1

        # Mark photo processed
        photo = db.query(Photo).filter(Photo.id == photo_id).first()
        if photo:
            photo.status = "processed"  # type: ignore
            photo.web_key = web_key  # type: ignore
            photo.thumb_key = thumb_key  # type: ignore
            photo.width = web_w  # type: ignore
            photo.height = web_h  # type: ignore
            if exif_taken_at and not photo.exif_taken_at:
                try:
                    photo.exif_taken_at = datetime.fromisoformat(exif_taken_at)  # type: ignore
                except Exception:
                    pass
            photo.face_count = faces_created  # type: ignore
            photo.processed_at = datetime.now(timezone.utc)  # type: ignore
            photo.processing_error = None  # type: ignore
            photo.phash = phash_val  # type: ignore
            photo.dhash = dhash_val  # type: ignore
            photo.hash_computed_at = datetime.now(timezone.utc)  # type: ignore

        db.commit()

        # Set Redis event faces dirty flag
        try:
            r = redis.Redis.from_url(getattr(settings, "REDIS_URL", "redis://localhost:6379/0"))
            r.set(f"event:{event_id}:faces_dirty", "true")
        except Exception as e:
            logger.warning(f"Failed to set dirty flag in Redis: {e}")

        logger.info(f"Successfully processed photo {photo_id_str}: {faces_created} faces detected.")
        return {"status": "success", "photo_id": photo_id_str, "faces_count": faces_created}

    except Exception as e:
        logger.error(f"Error in extract_faces for {photo_id_str}: {e}")
        db.rollback()
        # Increment attempts / mark failed if >= 3
        try:
            photo = db.query(Photo).filter(Photo.id == photo_id).first()
            if photo:
                if photo.attempts >= 3:
                    photo.status = "failed"  # type: ignore
                else:
                    photo.status = "failed"  # type: ignore
                photo.processing_error = str(e)  # type: ignore
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()
