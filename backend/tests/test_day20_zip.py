import hashlib
import io
import os
import uuid
import zipfile
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from models.event import Event
from models.guest import Guest
from models.guest_access_token import GuestAccessToken
from models.match import Match
from models.photo import Photo
from models.photo_face import PhotoFace
from models.selfie_search_log import SelfieSearchLog
from models.user import User
from models.zip_archive import ZipArchive, ZipStatus
from services.storage import LocalStorage
from workers.zip_worker import sweep_expired_zips, generate_guest_zip


def setup_zip_fixtures(db: Session, tmp_path):
    """Set up test user, event, guest, magic link, photos, and matches for Day 20 tests."""
    storage_dir = os.path.join(tmp_path, "uploads")
    os.makedirs(storage_dir, exist_ok=True)
    storage = LocalStorage(root_dir=storage_dir)

    user = User(
        email=f"zip_organizer_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="fakehash",
        name="Zip Organizer",
    )
    db.add(user)
    db.flush()

    event = Event(
        title="Gala Night 2026",
        date=datetime.now(timezone.utc),
        created_by=user.id,
    )
    db.add(event)
    db.flush()

    guest = Guest(
        event_id=event.id,
        first_name="Charlie",
        last_name="Brown",
        phone="+15559990000",
        email="charlie@example.com",
    )
    db.add(guest)
    db.flush()

    raw_token = f"token_charlie_{uuid.uuid4().hex[:12]}"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    access_token = GuestAccessToken(
        guest_id=guest.id,
        event_id=event.id,
        token_hash=token_hash,
        token_prefix=raw_token[:6],
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(access_token)

    photos = []
    matches = []
    for i in range(3):
        fake_content = f"Fake JPEG image content {i} - {uuid.uuid4()}".encode("utf-8")
        key = f"events/{event.id}/photo_{i}.jpg"
        storage.put(key, fake_content)

        p = Photo(
            event_id=event.id,
            uploaded_by=user.id,
            storage_key=key,
            original_filename=f"party_{i}.jpg",
            content_hash=hashlib.sha256(fake_content).hexdigest(),
            mime_type="image/jpeg",
            file_size=len(fake_content),
            width=800,
            height=600,
            status="processed",
        )
        db.add(p)
        db.flush()
        photos.append(p)

        pf = PhotoFace(
            photo_id=p.id,
            event_id=event.id,
            bbox_x=10.0,
            bbox_y=10.0,
            bbox_w=50.0,
            bbox_h=50.0,
            det_score=0.95,
            embedding=[0.1] * 512,
        )
        db.add(pf)
        db.flush()

        m = Match(
            event_id=event.id,
            guest_id=guest.id,
            photo_id=p.id,
            photo_face_id=pf.id,
            similarity=0.92,
            threshold_used=0.55,
            decision="auto_confirmed",
            status="active",
        )
        db.add(m)
        matches.append(m)

    db.commit()

    return {
        "user": user,
        "event": event,
        "guest": guest,
        "token": raw_token,
        "photos": photos,
        "matches": matches,
        "storage": storage,
        "storage_dir": storage_dir,
    }


def test_zip_request_worker_and_download(db_session: Session, tmp_path, monkeypatch):
    fixtures = setup_zip_fixtures(db_session, tmp_path)
    monkeypatch.setattr("api.endpoints.public_zip._check_disk_watermark", lambda path=".": True)
    monkeypatch.setattr("api.endpoints.public_zip.get_storage_backend", lambda: fixtures["storage"])
    monkeypatch.setattr("workers.zip_worker.get_storage_backend", lambda: fixtures["storage"])

    client = TestClient(app)
    token = fixtures["token"]

    # 1. POST request for zip archive
    res_post = client.post(f"/api/v1/public/guest/{token}/zip")
    assert res_post.status_code in (200, 202)
    data_post = res_post.json()
    assert "job_id" in data_post
    job_id = data_post["job_id"]

    # Execute worker inline to complete the job
    generate_guest_zip(job_id)

    # 2. Poll job status
    res_poll = client.get(f"/api/v1/public/guest/{token}/zip/{job_id}")
    assert res_poll.status_code == 200
    data_poll = res_poll.json()
    assert data_poll["status"] == "completed"
    assert data_poll["photo_count"] == 3
    assert data_poll["download_url"] is not None

    # 3. Download the zip archive
    res_dl = client.get(data_poll["download_url"])
    assert res_dl.status_code == 200
    assert res_dl.headers["content-type"] == "application/zip"
    assert "attachment; filename=" in res_dl.headers["content-disposition"]

    # Verify extracted zip contents
    zip_bytes = res_dl.content
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        namelist = zf.namelist()
        assert len(namelist) == 3
        for fname in namelist:
            assert fname.startswith("photo_")


def test_zip_idempotency_and_cache_hit(db_session: Session, tmp_path, monkeypatch):
    fixtures = setup_zip_fixtures(db_session, tmp_path)
    monkeypatch.setattr("api.endpoints.public_zip._check_disk_watermark", lambda path=".": True)
    monkeypatch.setattr("api.endpoints.public_zip.get_storage_backend", lambda: fixtures["storage"])
    monkeypatch.setattr("workers.zip_worker.get_storage_backend", lambda: fixtures["storage"])

    client = TestClient(app)
    token = fixtures["token"]

    # Initial request
    res1 = client.post(f"/api/v1/public/guest/{token}/zip")
    assert res1.status_code in (200, 202)
    job_id1 = res1.json()["job_id"]

    # Complete the job via worker
    generate_guest_zip(job_id1)

    # Second request (Cache hit check)
    res2 = client.post(f"/api/v1/public/guest/{token}/zip")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["job_id"] == job_id1
    assert data2["status"] == "completed"
    assert "download_url" in data2


def test_disk_watermark_guard(db_session: Session, tmp_path, monkeypatch):
    fixtures = setup_zip_fixtures(db_session, tmp_path)
    monkeypatch.setattr("api.endpoints.public_zip._check_disk_watermark", lambda: False)

    client = TestClient(app)
    token = fixtures["token"]

    res = client.post(f"/api/v1/public/guest/{token}/zip")
    assert res.status_code == 503
    assert res.headers.get("retry-after") == "300"
    assert "Disk watermark exceeded" in res.json()["detail"]


def test_sweep_expired_zips(db_session: Session, tmp_path):
    fixtures = setup_zip_fixtures(db_session, tmp_path)
    guest = fixtures["guest"]
    event = fixtures["event"]

    # Create dummy zip file on disk
    dummy_zip_path = os.path.join(tmp_path, "expired_test.zip")
    with open(dummy_zip_path, "wb") as f:
        f.write(b"PK\x05\x06" + b"\x00" * 18)  # Empty ZIP bytes

    # Create expired archive record in DB
    expired_archive = ZipArchive(
        guest_id=guest.id,
        event_id=event.id,
        match_set_hash="dummyhash123",
        status=ZipStatus.COMPLETED.value,
        file_path=dummy_zip_path,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db_session.add(expired_archive)

    # Create old selfie search log (>30 days)
    old_selfie_log = SelfieSearchLog(
        event_id=event.id,
        ip_hash="testiphash",
        faces_detected=1,
        threshold_used=0.45,
        results_count=2,
        created_at=datetime.now(timezone.utc) - timedelta(days=32),
    )
    db_session.add(old_selfie_log)
    db_session.commit()

    archive_id = expired_archive.id
    log_id = old_selfie_log.id

    # Run sweep
    sweep_expired_zips()

    # Verify physical file deleted
    assert not os.path.exists(dummy_zip_path)

    # Verify DB records purged
    arch_db = db_session.query(ZipArchive).filter(ZipArchive.id == archive_id).first()
    assert arch_db is None

    log_db = db_session.query(SelfieSearchLog).filter(SelfieSearchLog.id == log_id).first()
    assert log_db is None
