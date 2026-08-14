import hashlib
import logging
import os
import shutil
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from celery import shared_task

from database.session import SessionLocal
from models.photo import Photo
from models.selfie_search_log import SelfieSearchLog
from models.zip_archive import ZipArchive, ZipStatus
from services.storage import get_storage_backend
from services.visibility import visible_photo_ids
from sqlalchemy import text

logger = logging.getLogger(__name__)


@shared_task(name="workers.zip.generate_guest_zip")
def generate_guest_zip(zip_archive_id: str):
    """
    Celery task to build an uncompressed ZIP archive (ZIP_STORED per D25)
    for all visible photos of a guest.
    """
    db = SessionLocal()
    temp_zip_path = None
    try:
        archive: Any = db.query(ZipArchive).filter(ZipArchive.id == UUID(zip_archive_id)).first()
        if not archive:
            logger.error(f"ZipArchive {zip_archive_id} not found")
            return

        if archive.status == ZipStatus.COMPLETED.value:
            logger.info(f"ZipArchive {zip_archive_id} is already completed")
            return

        archive.status = ZipStatus.PROCESSING.value
        archive.updated_at = datetime.now(timezone.utc)
        db.commit()

        photo_ids = visible_photo_ids(db, UUID(str(archive.guest_id)))
        if not photo_ids:
            archive.status = ZipStatus.FAILED.value
            archive.error_message = "No visible photos found for guest"
            archive.updated_at = datetime.now(timezone.utc)
            db.commit()
            return

        photos = db.query(Photo).filter(Photo.id.in_(photo_ids)).all()
        photo_map = {p.id: p for p in photos}
        ordered_photos = [photo_map[pid] for pid in photo_ids if pid in photo_map]

        archive.photo_count = len(ordered_photos)
        archive.processed_photos = 0
        archive.processed_bytes = 0

        storage = get_storage_backend()
        file_items = []
        total_bytes = 0

        for i, photo in enumerate(ordered_photos, start=1):
            file_path = storage.get_path(str(photo.storage_key))
            if file_path and os.path.exists(file_path):
                fsize = os.path.getsize(file_path)
                total_bytes += fsize
                ext = photo.original_filename.rsplit(".", 1)[-1] if (photo.original_filename and "." in photo.original_filename) else "jpg"
                arc_name = f"photo_{i:04d}_{str(photo.id)[:8]}.{ext}"
                file_items.append((file_path, arc_name, fsize))

        archive.total_bytes = total_bytes
        db.commit()

        storage_root = getattr(storage, "root_dir", None) or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads"
        )
        zip_dir = os.path.abspath(os.path.join(storage_root, "zips", str(archive.event_id)))
        os.makedirs(zip_dir, exist_ok=True)

        final_zip_path = os.path.join(zip_dir, f"guest_{archive.guest_id}_{archive.id}.zip")
        temp_zip_path = f"{final_zip_path}.tmp"

        try:
            import pyzipper  # type: ignore
            zf = pyzipper.AESZipFile(temp_zip_path, "w", compression=pyzipper.ZIP_STORED, encryption=pyzipper.WZ_AES)
            zf.setpassword(b"secret") # ponytail: hardcoded secret, pass from UI when needed
        except ImportError:
            zf = zipfile.ZipFile(temp_zip_path, "w", compression=zipfile.ZIP_STORED)

        with zf:
            processed_bytes = 0
            for idx, (fpath, arc_name, fsize) in enumerate(file_items, start=1):
                zf.write(fpath, arcname=arc_name)
                processed_bytes += fsize

                archive.processed_photos = idx
                archive.processed_bytes = processed_bytes
                archive.updated_at = datetime.now(timezone.utc)
                db.commit()

        if os.path.exists(final_zip_path):
            os.remove(final_zip_path)
        os.rename(temp_zip_path, final_zip_path)

        archive.status = ZipStatus.COMPLETED.value
        archive.file_path = final_zip_path
        archive.expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
        archive.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"ZipArchive {zip_archive_id} created successfully at {final_zip_path}")

    except Exception as e:
        logger.exception(f"Error generating ZIP archive {zip_archive_id}: {e}")
        db.rollback()
        if temp_zip_path and os.path.exists(temp_zip_path):
            try:
                os.remove(temp_zip_path)
            except Exception:
                pass

        err_archive: Any = db.query(ZipArchive).filter(ZipArchive.id == UUID(zip_archive_id)).first()
        if err_archive:
            err_archive.status = ZipStatus.FAILED.value
            err_archive.error_message = str(e)
            err_archive.updated_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


@shared_task(name="workers.zip.sweep_expired_zips")
def sweep_expired_zips():
    """
    Celery Beat hourly task per D25:
    - Purges expired ZIP archives and deletes physical .zip files from disk.
    - Purges SelfieSearchLogs older than 30 days.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        expired_archives = db.query(ZipArchive).filter(
            (ZipArchive.expires_at < now) | (ZipArchive.status == ZipStatus.FAILED.value)
        ).all()

        deleted_files = 0
        for archive in expired_archives:
            path_str = str(archive.file_path) if archive.file_path else None
            if path_str and os.path.exists(path_str):
                try:
                    os.remove(path_str)
                    deleted_files += 1
                except Exception as e:
                    logger.error(f"Failed to remove zip file {path_str}: {e}")
            db.delete(archive)

        missing_file_archives = db.query(ZipArchive).filter(
            ZipArchive.status == ZipStatus.COMPLETED.value
        ).all()
        for archive in missing_file_archives:
            path_str = str(archive.file_path) if archive.file_path else None
            if path_str and not os.path.exists(path_str):
                db.delete(archive)

        cutoff = now - timedelta(days=30)
        purged_logs = db.query(SelfieSearchLog).filter(SelfieSearchLog.created_at < cutoff).delete(synchronize_session=False)

        bio_cutoff = now - timedelta(days=15)
        db.execute(text("DELETE FROM face_embeddings WHERE created_at < :cutoff"), {"cutoff": bio_cutoff})

        db.commit()
        logger.info(f"Zip sweep complete: deleted {deleted_files} files, purged {purged_logs} logs, purged old biometrics")
    except Exception as e:
        logger.exception(f"Error sweeping expired ZIP archives: {e}")
        db.rollback()
    finally:
        db.close()
