#!/bin/bash
set -e

echo "Applying database migrations..."
alembic upgrade head

# Use --pool=solo to avoid preforking a second Python process, saving memory but keeping it reliable.
celery -A core.celery_app.celery_app worker -Q celery,faces,match,maintenance --pool=solo --loglevel=info &

echo "Starting Celery beat (cron jobs)..."
celery -A core.celery_app.celery_app beat --loglevel=info &

echo "Starting FastAPI server..."
# PORT is provided automatically by Render, fallback to 8000 for local testing
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'
