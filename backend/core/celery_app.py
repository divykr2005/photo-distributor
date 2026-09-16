import os
from celery import Celery
from core.config import settings

redis_url = os.getenv("REDIS_URL", getattr(settings, "REDIS_URL", "redis://localhost:6379/0"))

if getattr(settings, "SENTRY_DSN", None):
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        integrations=[CeleryIntegration()],
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

celery_app = Celery(
    "photo_distributor",
    broker=redis_url,
    backend=redis_url,
    include=[
        "workers.faces",
        "workers.matching",
        "workers.maintenance",
        "workers.zip_worker",
        "workers.notifications",
        "worker.tasks",
    ]
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
    task_time_limit=660,
    task_soft_time_limit=600,
    visibility_timeout=600,
    task_always_eager=os.getenv("CELERY_TASK_ALWAYS_EAGER", "False").lower() == "true",
    task_eager_propagates=os.getenv("CELERY_TASK_ALWAYS_EAGER", "False").lower() == "true",
    task_routes={
        "worker.tasks.process_guest_registration_photo_task": {"queue": "faces"},
        "worker.tasks.process_event_photo_task": {"queue": "faces"},
        "workers.faces.*": {"queue": "faces"},
        "workers.matching.*": {"queue": "match"},
        "workers.maintenance.*": {"queue": "maintenance"},
        "workers.zip.*": {"queue": "maintenance"},
        "worker.tasks.*": {"queue": "maintenance"},
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
        "monitor-queue-depth-every-1m": {
            "task": "workers.maintenance.monitor_queue_depth",
            "schedule": 60.0,
            "options": {"queue": "maintenance"},
        },
        "sweep-expired-guests-daily": {
            "task": "workers.maintenance.sweep_expired_guests",
            "schedule": 86400.0,  # Every 24 hours
            "options": {"queue": "maintenance"},
        },
        "purge-stale-embeddings-daily": {
            "task": "workers.maintenance.purge_stale_embeddings",
            "schedule": 86400.0,  # Every 24 hours
            "options": {"queue": "maintenance"},
        },
    },
    # P1 hardening: expire task results from Redis after 1 hour.
    # Without this, every task result accumulates in Redis indefinitely.
    result_expires=3600,
    # Cap how long a task can sit in the broker queue before being discarded.
    # Prevents a backlog of stale biometric tasks from running after a restart.
    task_default_priority=5,
    task_queue_max_priority=10,
    # Biometric faces tasks are CPU-heavy; rate-limit to 30/min per worker
    # so the worker doesn't starve the host during burst ingestion.
    task_annotations={
        "workers.faces.extract_faces": {"rate_limit": "30/m"},
        "worker.tasks.process_guest_registration_photo_task": {"rate_limit": "60/m"},
    },
)


