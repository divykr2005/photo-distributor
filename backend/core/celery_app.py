import os
from celery import Celery
from core.config import settings

redis_url = os.getenv("REDIS_URL", getattr(settings, "REDIS_URL", "redis://localhost:6379/0"))

celery_app = Celery(
    "photo_distributor",
    broker=redis_url,
    backend=redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    visibility_timeout=600,
    task_routes={
        "workers.faces.*": {"queue": "faces"},
        "workers.matching.*": {"queue": "match"},
        "workers.maintenance.*": {"queue": "maintenance"},
        "workers.zip.*": {"queue": "maintenance"},
    },
    beat_schedule={
        "check-dirty-events-every-30s": {
            "task": "workers.maintenance.check_dirty_events_task",
            "schedule": 30.0,
            "options": {"queue": "maintenance"},
        },
        "requeue-stale-photos-every-5m": {
            "task": "workers.maintenance.requeue_stale_photos",
            "schedule": 300.0,
            "options": {"queue": "maintenance"},
        },
        "sweep-expired-zips-hourly": {
            "task": "workers.zip.sweep_expired_zips",
            "schedule": 3600.0,
            "options": {"queue": "maintenance"},
        },
    },
)

# Auto-discover tasks in workers package
celery_app.autodiscover_tasks(["workers"])
