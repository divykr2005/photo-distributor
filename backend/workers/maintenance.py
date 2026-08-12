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
        r = redis.Redis.from_url(getattr(settings, "REDIS_URL", "redis://localhost:6379/0"))
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
