import hashlib
import os
import re
import shutil
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.endpoints.public import _validate_access_code
from models.zip_archive import ZipArchive, ZipStatus
from services.storage import get_storage_backend
from services.visibility import visible_photo_ids
from workers.zip_worker import generate_guest_zip

router = APIRouter()

CHUNK_SIZE = 1024 * 1024  # 1 MB chunk streaming


def _sanitize_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\.-]", "_", name.lower())


def _check_disk_watermark(path: str = ".") -> bool:
    """Return True if disk usage is below 80% watermark (per D25), False if above."""
    try:
        total, used, free = shutil.disk_usage(path)
        percent_used = (used / total) * 100.0
        return percent_used < 80.0
    except Exception:
        return True  # Fallback if disk usage check fails


def _file_chunk_generator(file_path: str, start: int, length: int, chunk_size: int = CHUNK_SIZE):
    with open(file_path, "rb") as f:
        f.seek(start)
        remaining = length
        while remaining > 0:
            bytes_to_read = min(chunk_size, remaining)
            chunk = f.read(bytes_to_read)
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


from middleware.rate_limit import limiter, get_token_from_request


@router.post("/guest/{token}/zip")
@limiter.limit("5/minute", key_func=get_token_from_request)
def request_guest_zip(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
):
    """
    Request or retrieve cached ZIP archive for a guest (Day 20 / D25).
    - Checks disk watermark (>80% usage returns 503 + Retry-After).
    - Idempotent on (guest_id, match_set_hash).
    - Cache hit returns completed archive info instantly (200 OK).
    - In-flight job returns job status (202 Accepted).
    - New job creates ZipArchive and enqueues Celery task (202 Accepted).
    """
    _token_row, guest, event = _validate_access_code(db, token)

    if not _check_disk_watermark():
        return JSONResponse(
            status_code=503,
            headers={"Retry-After": "300"},
            content={"detail": "Disk watermark exceeded (storage above 80%). Please try again later."},
        )

    photo_ids = visible_photo_ids(db, UUID(str(guest.id)))
    if not photo_ids:
        raise HTTPException(status_code=404, detail="No photos available for download")

    if len(photo_ids) > 1000:
        raise HTTPException(status_code=400, detail="Archive photo count exceeds limit (max 1000 photos)")

    match_set_hash = hashlib.sha256(",".join(sorted(str(pid) for pid in photo_ids)).encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)

    # 1. Cache hit check
    existing_completed = (
        db.query(ZipArchive)
        .filter(
            ZipArchive.guest_id == guest.id,
            ZipArchive.match_set_hash == match_set_hash,
            ZipArchive.status == ZipStatus.COMPLETED.value,
            ZipArchive.expires_at > now,
        )
        .first()
    )
    if existing_completed and existing_completed.file_path and os.path.exists(str(existing_completed.file_path)):
        return JSONResponse(
            status_code=200,
            content={
                "job_id": str(existing_completed.id),
                "status": ZipStatus.COMPLETED.value,
                "photo_count": existing_completed.photo_count,
                "total_bytes": existing_completed.total_bytes,
                "processed_photos": existing_completed.processed_photos,
                "processed_bytes": existing_completed.processed_bytes,
                "download_url": f"/api/v1/public/guest/{token}/zip/{existing_completed.id}/download",
            },
        )

    # 2. In-flight check
    in_flight = (
        db.query(ZipArchive)
        .filter(
            ZipArchive.guest_id == guest.id,
            ZipArchive.status.in_([ZipStatus.PENDING.value, ZipStatus.PROCESSING.value]),
        )
        .first()
    )
    if in_flight:
        return JSONResponse(
            status_code=202,
            content={
                "job_id": str(in_flight.id),
                "status": in_flight.status,
                "photo_count": in_flight.photo_count,
                "total_bytes": in_flight.total_bytes,
                "processed_photos": in_flight.processed_photos,
                "processed_bytes": in_flight.processed_bytes,
            },
        )

    # 3. Create new job
    archive = ZipArchive(
        guest_id=guest.id,
        event_id=event.id,
        match_set_hash=match_set_hash,
        status=ZipStatus.PENDING.value,
        photo_count=len(photo_ids),
    )
    db.add(archive)
    db.commit()
    db.refresh(archive)

    # Dispatch background worker
    try:
        task_fn: Any = generate_guest_zip
        task_fn.delay(str(archive.id))
    except Exception:
        # Fallback if Celery broker is offline in simple test mode: call task function directly
        generate_guest_zip(str(archive.id))
        db.refresh(archive)

    return JSONResponse(
        status_code=202,
        content={
            "job_id": str(archive.id),
            "status": archive.status,
            "photo_count": archive.photo_count,
            "total_bytes": archive.total_bytes,
            "processed_photos": archive.processed_photos,
            "processed_bytes": archive.processed_bytes,
        },
    )


@router.get("/guest/{token}/zip/{job_id}")
def poll_guest_zip_status(
    token: str,
    job_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Poll status of a ZIP generation job (2s polling convention).
    """
    _token_row, guest, _event = _validate_access_code(db, token)

    archive = (
        db.query(ZipArchive)
        .filter(
            ZipArchive.id == job_id,
            ZipArchive.guest_id == guest.id,
        )
        .first()
    )
    if not archive:
        raise HTTPException(status_code=404, detail="ZIP job not found")

    download_url = None
    if archive.status == ZipStatus.COMPLETED.value:
        download_url = f"/api/v1/public/guest/{token}/zip/{archive.id}/download"

    return {
        "job_id": str(archive.id),
        "status": archive.status,
        "photo_count": archive.photo_count,
        "total_bytes": archive.total_bytes,
        "processed_photos": archive.processed_photos,
        "processed_bytes": archive.processed_bytes,
        "error_message": archive.error_message,
        "download_url": download_url,
    }


@router.get("/guest/{token}/zip/{job_id}/download")
def download_guest_zip(
    token: str,
    job_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Stream completed ZIP archive with range request support (HTTP 206) and sanitized filename.
    """
    _token_row, guest, event = _validate_access_code(db, token)

    archive = (
        db.query(ZipArchive)
        .filter(
            ZipArchive.id == job_id,
            ZipArchive.guest_id == guest.id,
        )
        .first()
    )
    now = datetime.now(timezone.utc)
    if (
        not archive
        or archive.status != ZipStatus.COMPLETED.value
        or not archive.file_path
        or not os.path.exists(archive.file_path)
        or (archive.expires_at and archive.expires_at < now)
    ):
        raise HTTPException(status_code=404, detail="ZIP archive not found or expired")

    file_size = os.path.getsize(str(archive.file_path))
    event_slug = _sanitize_filename(str(event.title))
    download_filename = f"{event_slug}-photos.zip"

    range_header = request.headers.get("range")
    if range_header:
        match = re.match(r"bytes=(\d+)-(\d+)?", range_header)
        if match:
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else file_size - 1
            if start >= file_size or end >= file_size or start > end:
                return Response(
                    status_code=416,
                    headers={"Content-Range": f"bytes */{file_size}"},
                )
            length = end - start + 1
            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(length),
                "Content-Type": "application/zip",
                "Content-Disposition": f'attachment; filename="{download_filename}"',
            }
            return StreamingResponse(
                _file_chunk_generator(archive.file_path, start, length),
                status_code=206,
                headers=headers,
            )

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Content-Type": "application/zip",
        "Content-Disposition": f'attachment; filename="{download_filename}"',
    }
    return StreamingResponse(
        _file_chunk_generator(archive.file_path, 0, file_size),
        status_code=200,
        headers=headers,
    )
