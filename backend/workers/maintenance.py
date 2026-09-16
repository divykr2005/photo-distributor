import logging
from datetime import datetime, timezone, timedelta
import redis
from sqlalchemy import text

from core.celery_app import celery_app
from database.session import SessionLocal
from core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(name="workers.maintenance.requeue_stale_photos")
def requeue_stale_photos() -> dict:
    """Finds photos stuck in processing for >10 minutes and requeues or marks them failed."""
    db = SessionLocal()
    stale_count = 0
    failed_count = 0

    try:
        ten_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=10)

        # Select stale photos
        query = text("""
            SELECT id, attempts FROM photos
            WHERE status = 'processing'
              AND updated_at < :cutoff
        """)
        rows = db.execute(query, {"cutoff": ten_minutes_ago}).fetchall()

        for row in rows:
            photo_id = row.id
            attempts = row.attempts

            if attempts < 3:
                db.execute(
                    text("UPDATE photos SET status = 'queued', updated_at = NOW() WHERE id = :id"),
                    {"id": photo_id}
                )
                from workers.faces import extract_faces
                extract_faces.delay(str(photo_id))
                stale_count += 1
            else:
                db.execute(
                    text("UPDATE photos SET status = 'failed', processing_error = 'Stale worker timeout after 3 attempts', updated_at = NOW() WHERE id = :id"),
                    {"id": photo_id}
                )
                failed_count += 1

        db.commit()
        logger.info(f"Stale photo maintenance complete: {stale_count} requeued, {failed_count} marked failed.")
        return {"requeued": stale_count, "failed": failed_count}
    except Exception as e:
        logger.error(f"Error in requeue_stale_photos: {e}")
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()


@celery_app.task(name="workers.maintenance.check_dirty_events_task")
def check_dirty_events_task() -> dict:
    """Scans Redis every 30s for events marked dirty and triggers batched matching if lock acquired."""
    try:
        url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        if "ssl_cert_reqs=CERT_NONE" in url:
            url = url.replace("ssl_cert_reqs=CERT_NONE", "ssl_cert_reqs=none")
        r = redis.Redis.from_url(url)
        keys = r.keys("event:*:faces_dirty")
        triggered = []

        for key_bytes in keys:
            key = key_bytes.decode() if isinstance(key_bytes, bytes) else key_bytes
            val = r.get(key)
            if val and (val == b"true" or val == "true"):
                # Extract event_id from key
                parts = key.split(":")
                if len(parts) >= 3:
                    event_id = parts[1]
                    lock_key = f"event:{event_id}:match_lock"
                    acquired = r.set(lock_key, "locked", nx=True, ex=600)
                    if acquired:
                        r.delete(key)
                        from workers.matching import run_event_match
                        run_event_match.delay(event_id)
                        triggered.append(event_id)

        return {"triggered_events": triggered}
    except Exception as e:
        logger.error(f"Error in check_dirty_events_task: {e}")
        return {"error": str(e)}

@celery_app.task(name="workers.maintenance.monitor_queue_depth")
def monitor_queue_depth() -> dict:
    """Monitors the depth of Celery queues and logs warnings if they exceed thresholds."""
    try:
        url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        if "ssl_cert_reqs=CERT_NONE" in url:
            url = url.replace("ssl_cert_reqs=CERT_NONE", "ssl_cert_reqs=none")
        r = redis.Redis.from_url(url)

        queues = ["faces", "match", "maintenance"]
        queue_sizes = {}
        for q in queues:
            size = r.llen(q)
            queue_sizes[q] = size
            if size > 1000:
                logger.warning(f"HIGH QUEUE DEPTH ALERT: Queue '{q}' has {size} pending tasks!")

        return queue_sizes
    except Exception as e:
        logger.error(f"Error in monitor_queue_depth: {e}")
        return {"error": str(e)}

@celery_app.task(name="workers.maintenance.sweep_expired_guests")
def sweep_expired_guests() -> dict:
    """Deletes guests (and their biometric data) whose expires_at date has passed."""
    db = SessionLocal()
    deleted_count = 0
    try:
        now = datetime.now(timezone.utc)

        # 1. Find all expired guests
        from models.guest import Guest
        expired_guests = db.query(Guest).filter(Guest.expires_at < now).all()

        if not expired_guests:
            return {"deleted": 0}

        from services.storage import get_storage_backend
        storage = get_storage_backend()

        for guest in expired_guests:
            # 2. Delete the actual selfie image from storage
            if guest.image_path:
                try:
                    storage.delete(guest.image_path)
                except Exception as e:
                    logger.warning(f"Could not delete image {guest.image_path} for guest {guest.id}: {e}")
                guest.image_path = None

            # 3. Delete embeddings
            from models.face_embedding import FaceEmbedding
            db.query(FaceEmbedding).filter(FaceEmbedding.guest_id == guest.id).delete(synchronize_session=False)

            # 4. Delete photo matches
            from models.photo_match import PhotoMatch
            db.query(PhotoMatch).filter(PhotoMatch.guest_id == guest.id).delete(synchronize_session=False)

            # 5. Clear sensitive crypto keys and set purged flag
            guest.wrapped_dek = None
            guest.dek_key_id = None
            guest.embedding_status = "pending"
            guest.biometrics_purged_at = now

            deleted_count += 1

        db.commit()
        logger.info(f"Biometric retention sweep complete: purged biometrics for {deleted_count} expired guests.")
        return {"purged": deleted_count}
    except Exception as e:
        logger.error(f"Error in sweep_expired_guests: {e}")
        db.rollback()
        return {"error": str(e)}
        db.close()

@celery_app.task(name="workers.maintenance.purge_stale_embeddings")
def purge_stale_embeddings(days: int = 30) -> dict:
    """Deletes guest embeddings N days after the event has occurred."""
    db = SessionLocal()
    purged_count = 0
    try:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)

        # 1. Find all guests belonging to events that happened before the cutoff
        from models.event import Event
        from models.guest import Guest

        stale_events = db.query(Event.id).filter(Event.date < cutoff).all()
        stale_event_ids = [e.id for e in stale_events]

        if not stale_event_ids:
            return {"purged": 0}

        guests_to_purge = db.query(Guest).filter(
            Guest.event_id.in_(stale_event_ids),
            Guest.biometrics_purged_at.is_(None)
        ).all()

        if not guests_to_purge:
            return {"purged": 0}

        from services.storage import get_storage_backend
        storage = get_storage_backend()

        for guest in guests_to_purge:
            if guest.image_path:
                try:
                    storage.delete(guest.image_path)
                except Exception:
                    pass
                guest.image_path = None

            # Delete embeddings
            from models.face_embedding import FaceEmbedding
            db.query(FaceEmbedding).filter(FaceEmbedding.guest_id == guest.id).delete(synchronize_session=False)

            # Delete matches
            from models.photo_match import PhotoMatch
            db.query(PhotoMatch).filter(PhotoMatch.guest_id == guest.id).delete(synchronize_session=False)

            # Clear crypto keys
            guest.wrapped_dek = None
            guest.dek_key_id = None
            guest.embedding_status = "pending"
            guest.biometrics_purged_at = now

            purged_count += 1

        # 6. Delete PhotoFace records (group photo biometrics) for the stale events
        from models.photo_face import PhotoFace
        deleted_photo_faces = db.query(PhotoFace).filter(
            PhotoFace.event_id.in_(stale_event_ids)
        ).delete(synchronize_session=False)

        # 7. Audit Logging
        from models.audit_log import AuditLog
        for guest in guests_to_purge:
            audit = AuditLog(
                guest_id=guest.id,
                event_id=guest.event_id,
                action="biometrics_auto_purged_event_expiration",
                timestamp=now
            )
            db.add(audit)

        db.commit()
        logger.info(f"Purge stale embeddings complete: purged biometrics for {purged_count} guests and {deleted_photo_faces} photo faces.")
        return {"purged_guests": purged_count, "purged_photo_faces": deleted_photo_faces}
    except Exception as e:
        logger.error(f"Error in purge_stale_embeddings: {e}")
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()
