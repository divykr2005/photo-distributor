# Project Summary

## Overview
This repository (`photo-distributor` / Snaptracer) is a full-stack web application designed for event photo distribution. It leverages facial recognition to automatically match guests to their photos within uploaded event galleries.

## Directory Structure
- `/frontend`: Next.js 14 web application.
- `/backend`: FastAPI REST API service, including Celery task definitions.
- `/docker`: Additional Docker configuration files.
- `/ai-service` / `/worker`: Scripts and models for AI processing and background workers.
- `/docs`: Project documentation.
- `/scripts`: Utility scripts.
- `/Caddyfile`: Reverse proxy configuration for the backend.
- `/*.md`: Various planning documents (WEEK2_PLAN, WEEK3_PLAN, etc.).

## Technology Stack

### Frontend
- **Framework**: Next.js 14 (App Router) / React 18
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4
- **State/Forms & Validation**: React Hook Form, Zod
- **API Client**: Axios
- **Deployment Target**: Configured for Cloudflare Pages (`@cloudflare/next-on-pages`)

### Backend
- **Framework**: FastAPI (served via Uvicorn)
- **Language**: Python 3
- **Database ORM**: SQLAlchemy 2.0+ with Alembic for migrations
- **Vector Search**: `pgvector` (for storing and querying face embeddings)
- **Authentication**: JWT (`python-jose`), bcrypt, passlib
- **Storage Backend**: Support for Cloudflare R2 / S3 via `boto3` or local storage.

### Background Processing & Machine Learning
- **Task Queue**: Celery (using Redis as message broker and result backend)
- **Computer Vision & AI**:
  - **InsightFace** (using the `buffalo_l` model) for generating facial embeddings
  - **DeepFace**
  - **OpenCV** (Headless)
  - **ONNXRuntime**
- **Image Processing**: Pillow, pillow-heif
- **Workers Architecture**:
  - `worker-faces`: Dedicated container with restricted concurrency for compute-heavy ML tasks (running InsightFace).
  - `worker-io`: Threaded worker for I/O bound tasks like creating ZIP files and standard database operations.

### Infrastructure & Orchestration
- **Containerization**: Docker & Docker Compose
- **Web Server / Reverse Proxy**: Caddy
- **Monitoring**: Celery Flower (Available in debug profile)

## Exposed Ports & Networking
When running locally via `docker-compose.yml`:
- **8000**: FastAPI Backend (accessible via `127.0.0.1:8000`, proxied by Caddy in production/staging environments).
- **5432**: PostgreSQL Database (Standard postgres port, defined in `.env`).
- **6379**: Redis Server (Celery Broker / Backend).
- **5555**: Celery Flower (Monitoring dashboard, started via `docker compose --profile debug`).

## Key Environment Configuration (`.env`)
Main system configurations include:
- **Database & Redis**: `DATABASE_URL`, `CELERY_BROKER_URL`
- **InsightFace**: `INSIGHTFACE_MODEL=buffalo_l`, thread limitations (`ONNX_INTRA_OP_THREADS`, etc.)
- **Matching Algorithm**: Thresholds (`MATCH_THRESHOLD`, `MATCH_REVIEW_FLOOR`)
- **Storage**: `STORAGE_BACKEND` (local vs. r2), Cloudflare R2 credentials.
- **Security**: JWT secrets and expiration times.
