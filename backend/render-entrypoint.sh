#!/bin/bash
set -e

echo "Applying database migrations..."
alembic upgrade head

echo "Starting Celery worker (handling all queues on free tier)..."
# Render free instances have 512MB RAM, limiting concurrency to 1 to avoid OOM
celery -A core.celery_app.celery_app worker -Q celery,faces,match,maintenance --concurrency=1 --loglevel=info &

echo "Starting Celery beat (cron jobs)..."
celery -A core.celery_app.celery_app beat --loglevel=info &

echo "Starting FastAPI server..."
# PORT is provided automatically by Render, fallback to 8000 for local testing
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
