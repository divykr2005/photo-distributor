import logging
import redis
from core.celery_app import celery_app
from database.session import SessionLocal
from services.matching_service import MatchingService
from core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(
    name="workers.matching.run_event_match",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def run_event_match(self, event_id_str: str, force: bool = False, trigger: str = "photo_ingest") -> dict:
    """Celery task: Executes batched NumPy matching for an event."""
    db = SessionLocal()
    try:
        service = MatchingService(db)
        result = service.match_pending_faces(event_id_str, force=force, trigger=trigger)
        logger.info(f"run_event_match completed for event {event_id_str}: {result}")
        return result
    except Exception as e:
        logger.error(f"run_event_match failed for event {event_id_str}: {e}")
        raise
    finally:
        db.close()
        # Release Redis match_lock
        try:
            r = redis.Redis.from_url(getattr(settings, "REDIS_URL", "redis://localhost:6379/0"))
            r.delete(f"event:{event_id_str}:match_lock")
        except Exception:
            pass


@celery_app.task(
    name="workers.matching.run_guest_match",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def run_guest_match(self, event_id_str: str, guest_id_str: str) -> dict:
    """Celery task: Fast matching for a single newly registered guest."""
    db = SessionLocal()
    try:
        service = MatchingService(db)
        result = service.match_guest(event_id_str, guest_id_str)
        logger.info(f"run_guest_match completed for guest {guest_id_str}: {result}")
        return result
    except Exception as e:
        logger.error(f"run_guest_match failed for guest {guest_id_str}: {e}")
        raise
    finally:
        db.close()
