# Undo Log

This file tracks the changes made during the agent sessions so that they can be easily undone if necessary.

## [Session: 2026-09-10] Operability, ZIP Worker, and Docker Updates

### 1. ZIP Worker Empty File Fix
**What was done:**
Added a safeguard in `backend/workers/zip_worker.py` to check if `processed_bytes == 0`. If no photos are found in storage, it now sets the ZIP archive status to `FAILED` instead of returning a broken 22-byte zip.
**How to undo:**
Open `backend/workers/zip_worker.py`, find the `if processed_bytes == 0:` block inside `generate_guest_zip`, and remove it. Rebuild the container: `docker compose build worker-general`.

### 2. Docker Compose Health Checks & Logging (Phase 8)
**What was done:**
- Added `json-file` logging driver with `10m` size and `3` max files to limit log growth in `docker-compose.yml`.
- Added `healthcheck` definitions to `redis` and `backend` (and potentially `db`) services in `docker-compose.yml`.
- Added a `docker-prune` service to `docker-compose.yml` to automatically run `docker system prune -f` weekly.
**How to undo:**
Revert `docker-compose.yml` by removing the `healthcheck` blocks, the `logging` blocks under the base and traefik services, and the entire `docker-prune` service definition. Run `docker compose up -d` to apply.

### 3. Swap File Creation Script (Phase 8)
**What was done:**
Created `scripts/create_swap.sh` to automate the creation of a 4GB swap file to prevent Out-Of-Memory (OOM) crashes during face embeddings.
**How to undo:**
Delete the file `scripts/create_swap.sh`.

### 4. Database Alembic Pointer Reset (Local Only)
**What was done:**
Manually reset the `alembic_version` in the Neon DB back to `85538f8762a1` to fix a `migrate` container crash caused by reverting previous schema changes.
**How to undo:**
No action needed unless migrations break again. You can update `alembic_version` via `UPDATE alembic_version SET version_num = '...';`

### 5. Local Docker Container Rebuild
**What was done:**
Ran `docker compose build` to package the local Python code modifications into the Docker images so the Celery workers would execute the updated `zip_worker.py` code.
**How to undo:**
No action needed. Rebuilding just brought the containers in sync with your local code.
