# AI Codebase Understanding Guide: Snaptracer (Photo Distributor)

This document is specifically written to help any AI agent understand the entire codebase, architecture, services, and features of the **Snaptracer** (photo-distributor) project instantly.

## 1. System Overview
Snaptracer is a full-stack web application for event photo distribution. Event organizers upload galleries of photos, and the system uses facial recognition (InsightFace) to automatically match guests to their photos. Guests receive magic links (via Email/WhatsApp) to a public portal to securely view and download their personalized matched photos.

## 2. Infrastructure & Docker Services
The system is containerized and orchestrated via `docker-compose.yml`.

### Docker Services
1. **`migrate`**: One-shot container that runs `alembic upgrade head` before backend/workers start.
2. **`backend`**: FastAPI application.
   - **Internal Port**: 8000
   - **Exposed Port**: 8000 (proxied by Traefik in prod).
   - **Volumes**: `app_uploads` (shared storage).
3. **`worker-faces`**: Celery worker dedicated to compute-heavy AI tasks.
   - **Queues**: `faces` (runs InsightFace model inference).
   - **Concurrency**: Restricted (pool=prefork, concurrency=1) due to high memory usage of ONNX/InsightFace.
   - **Model**: `buffalo_l` mounted via `insightface_models` volume.
4. **`worker-general`**: Celery worker for I/O bound tasks and scheduling.
   - **Queues**: `match`, `celery`, `maintenance`.
   - **Concurrency**: Threaded pool (pool=threads, concurrency=4).
   - **Features**: Includes Celery Beat scheduler for background maintenance tasks (e.g., biometric data deletion).
5. **`flower`**: Celery monitoring dashboard.
   - **Profile**: `debug` (only starts if explicitly requested).
   - **Exposed Port**: `127.0.0.1:5555`
6. **`traefik`**: Edge router / reverse proxy.
   - **Exposed Ports**: 80 (HTTP), 443 (HTTPS).
   - **Role**: Terminates TLS (Let's Encrypt), applies security headers, rate limiting, and routes to the `backend`.
7. **`redis`**: Message broker for Celery and caching.
   - **Internal Port**: 6379
   - **Role**: Broker/Result backend.

### External Dependencies
- **PostgreSQL**: Stores relational data and facial embeddings. Relies on the **`pgvector`** extension for vector similarity search.
- **Object Storage**: S3-compatible backend (e.g., Cloudflare R2) via `boto3`. Falls back to local volume (`/uploads`) if not configured.

## 3. Backend (FastAPI / Python 3)
Located in `/backend`. Uses SQLAlchemy 2.0+ for ORM and Alembic for migrations.

### Core API Routers (`/api/v1/`)
- **`auth`**: JWT-based authentication (login, refresh, logout, `/me`). Uses HttpOnly cookies.
- **`events`**: CRUD for events (weddings, parties, etc.).
- **`guests`**: CRUD for event guests. Manages contact info (email, WhatsApp) and biometric consent.
- **`photos` / `uploads`**: Handling of original photo uploads from organizers.
- **`matches`**: Endpoints for viewing/verifying AI-generated guest-to-photo matches.
- **`pipeline` / `clusters`**: Triggers ML processing pipeline (face extraction, clustering, matching).
- **`notifications` / `webhooks`**: Sending Magic Links via Email/WhatsApp (Meta Cloud API). Handles delivery receipts.
- **`magic_links`**: Organizer side generation of access tokens.
- **`public_*`**: Endpoints for the guest-facing public portal (no JWT required, authenticated via token). Includes self-registration (`public_registration`), selfie upload (`public_selfie`), gallery viewing (`public_media`), and downloading ZIPs (`public_zip`, `public_download`).

### Data Flow & ML Pipeline
1. Photo uploaded -> saved to storage -> `process_photo` task sent to `faces` queue.
2. `worker-faces` runs InsightFace -> detects faces -> extracts 512D embeddings.
3. Embeddings stored in Postgres using `vector(512)` column (`pgvector`).
4. `worker-general` runs HNSW cosine similarity search inside Postgres to match guest reference faces to gallery faces.

## 4. Frontend (Next.js 14 / TypeScript / Tailwind CSS)
Located in `/frontend`. Uses App Router, React Hook Form, Zod, and Axios.

### Route Structure
- **`(auth)`**: Organizer login and registration.
- **`(dashboard)`**: Authenticated organizer interface (`/dashboard`, `/events`, `/guests`, etc.).
- **`g/[token]`**: Public guest portal. Guests land here using a magic link, upload a selfie, consent to biometric processing, and view their matched photos.

## 5. Architectural Rules & Invariants for AI Agents
When modifying this codebase, strictly adhere to these rules from `PLAN.md` and `AGENTS.md`:
1. **Never edit `.env`**: Only edit `.env.example`. `.env` is forbidden for agents.
2. **Alembic Revisions**: Every SQLAlchemy model change MUST have an accompanying Alembic migration script.
3. **Traefik Rules**: Never widen Traefik router rules or expose unnecessary ports.
4. **Matching Single Source of Truth**: Use `pgvector` inside PostgreSQL (`ORDER BY embedding <=> :probe`) for similarity matching. Do not use numpy in-memory fallback.
5. **Authentication**: Use `HttpOnly` cookies for JWT storage (not `localStorage`) to prevent XSS. Access token TTL 15m, Refresh token 30d.
6. **URL Configuration**: Rely solely on `backend/core/config.py` (pydantic-settings) for `FRONTEND_URL` and `API_BASE_URL`. Do not hardcode `http://localhost` in production.
7. **Biometric Compliance**: Retain guest explicit consent (timestamp, text version). Use Celery Beat to automatically purge embeddings after a configured retention window post-event.
8. **WhatsApp Integration**: Must use approved Meta Utility Templates. Cannot send arbitrary text messages. Magic links in WhatsApp must fit the pre-approved template URL shape.

## 6. Development Commands
Use `Makefile` for standard ops:
- `make up`: Start local environment via Docker Compose.
- `make logs`: Tail logs.
- `make test`: Run isolated test suite.
- `make deploy`: Run deployment targets.
