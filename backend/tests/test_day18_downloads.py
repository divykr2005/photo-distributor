import os
import uuid
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models.event import Event
from models.guest import Guest
from models.guest_access_token import GuestAccessToken
from models.match import Match
from models.photo import Photo
from models.photo_face import PhotoFace
from models.user import User
from services.storage import LocalStorage
import hashlib


def setup_test_fixtures(db: Session, tmp_path):
    """Set up database records and local storage file for testing download authorization."""
    # Create organizer user
    user = User(
        email=f"organizer_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="fakehash",
        name="Organizer",
    )
    db.add(user)
    db.flush()

    # Create event 1
    event1 = Event(
        title="Wedding Day",
        date=datetime.now(timezone.utc),
        created_by=user.id,
        selfie_search_enabled=True,
    )
    # Create event 2 (isolated event)
    event2 = Event(
        title="Corporate Gala",
        date=datetime.now(timezone.utc),
        created_by=user.id,
    )
    db.add_all([event1, event2])
    db.flush()

    # Create Guest A and Guest B for Event 1
    guest_a = Guest(event_id=event1.id, first_name="Alice", last_name="Smith", phone="+15550000001", email="alice@example.com")
    guest_b = Guest(event_id=event1.id, first_name="Bob", last_name="Jones", phone="+15550000002", email="bob@example.com")
    db.add_all([guest_a, guest_b])
    db.flush()

    # Create access token for Guest A
    raw_token_a = f"token_alice_{uuid.uuid4().hex[:12]}"
    token_hash_a = hashlib.sha256(raw_token_a.encode()).hexdigest()
    access_token_a = GuestAccessToken(
        guest_id=guest_a.id,
        event_id=event1.id,
        token_hash=token_hash_a,
        token_prefix=raw_token_a[:6],
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    # Create expired token for Guest B
    raw_token_expired = f"token_expired_{uuid.uuid4().hex[:12]}"
    token_hash_expired = hashlib.sha256(raw_token_expired.encode()).hexdigest()
    access_token_expired = GuestAccessToken(
        guest_id=guest_b.id,
        event_id=event1.id,
        token_hash=token_hash_expired,
        token_prefix=raw_token_expired[:6],
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )

    # Create revoked token for Guest B
    raw_token_revoked = f"token_revoked_{uuid.uuid4().hex[:12]}"
    token_hash_revoked = hashlib.sha256(raw_token_revoked.encode()).hexdigest()
    access_token_revoked = GuestAccessToken(
        guest_id=guest_b.id,
        event_id=event1.id,
        token_hash=token_hash_revoked,
        token_prefix=raw_token_revoked[:6],
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        revoked_at=datetime.now(timezone.utc),
    )

    db.add_all([access_token_a, access_token_expired, access_token_revoked])
    db.flush()

    # Create sample image file on storage
    storage = LocalStorage(root_dir=str(tmp_path))
    photo_content = b"JPEG_DUMMY_IMAGE_DATA_FOR_DAY_18_TESTS_" + b"0" * 100
    storage_key = f"events/{event1.id}/photos/original_test.jpg"
    
    # Save dummy file
    abs_path = os.path.join(str(tmp_path), storage_key)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb") as f:
        f.write(photo_content)

    # Photo 1 (Event 1): Matched to Guest A (active)
    photo1 = Photo(
        event_id=event1.id,
        uploaded_by=user.id,
        original_filename="alice_photo.jpg",
        storage_key=storage_key,
        content_hash=uuid.uuid4().hex,
        mime_type="image/jpeg",
        file_size=len(photo_content),
        status="processed",
    )
    # Photo 2 (Event 1): Matched to Guest B (active)
    photo2 = Photo(
        event_id=event1.id,
        uploaded_by=user.id,
        original_filename="bob_photo.jpg",
        storage_key=storage_key,
        content_hash=uuid.uuid4().hex,
        mime_type="image/jpeg",
        file_size=len(photo_content),
        status="processed",
    )
    # Photo 3 (Event 1): Matched to Guest A but in pending_review
    photo3 = Photo(
        event_id=event1.id,
        uploaded_by=user.id,
        original_filename="alice_pending.jpg",
        storage_key=storage_key,
        content_hash=uuid.uuid4().hex,
        mime_type="image/jpeg",
        file_size=len(photo_content),
        status="processed",
    )
    # Photo 4 (Event 2): Belongs to Event 2
    photo4 = Photo(
        event_id=event2.id,
        uploaded_by=user.id,
        original_filename="event2_photo.jpg",
        storage_key=storage_key,
        content_hash=uuid.uuid4().hex,
        mime_type="image/jpeg",
        file_size=len(photo_content),
        status="processed",
    )
    db.add_all([photo1, photo2, photo3, photo4])
    db.flush()

    # Create PhotoFace records
    dummy_vec = [0.1] * 512
    face1 = PhotoFace(photo_id=photo1.id, event_id=event1.id, bbox_x=0, bbox_y=0, bbox_w=100, bbox_h=100, det_score=0.95, embedding=dummy_vec)
    face2 = PhotoFace(photo_id=photo2.id, event_id=event1.id, bbox_x=0, bbox_y=0, bbox_w=100, bbox_h=100, det_score=0.95, embedding=dummy_vec)
    face3 = PhotoFace(photo_id=photo3.id, event_id=event1.id, bbox_x=0, bbox_y=0, bbox_w=100, bbox_h=100, det_score=0.95, embedding=dummy_vec)
    db.add_all([face1, face2, face3])
    db.flush()

    # Matches
    match_a_active = Match(event_id=event1.id, photo_id=photo1.id, photo_face_id=face1.id, guest_id=guest_a.id, similarity=0.92, threshold_used=0.45, decision="auto_confirmed", status="active")
    match_b_active = Match(event_id=event1.id, photo_id=photo2.id, photo_face_id=face2.id, guest_id=guest_b.id, similarity=0.88, threshold_used=0.45, decision="auto_confirmed", status="active")
    match_a_pending = Match(event_id=event1.id, photo_id=photo3.id, photo_face_id=face3.id, guest_id=guest_a.id, similarity=0.75, threshold_used=0.45, decision="review", status="pending_review")

    db.add_all([match_a_active, match_b_active, match_a_pending])
    db.commit()

    return {
        "event1": event1,
        "event2": event2,
        "guest_a": guest_a,
        "guest_b": guest_b,
        "raw_token_a": raw_token_a,
        "raw_token_expired": raw_token_expired,
        "raw_token_revoked": raw_token_revoked,
        "photo1": photo1,
        "photo2": photo2,
        "photo3": photo3,
        "photo4": photo4,
        "photo_content": photo_content,
        "storage": storage,
    }


def test_download_happy_path_token(client: TestClient, db_session: Session, tmp_path, monkeypatch):
    """Verify photo download happy path using valid magic link token."""
    fixtures = setup_test_fixtures(db_session, tmp_path)
    monkeypatch.setattr("api.endpoints.public_download.get_storage_backend", lambda: fixtures["storage"])

    token = fixtures["raw_token_a"]
    photo_id = fixtures["photo1"].id

    resp = client.get(f"/api/v1/public/photos/{photo_id}/download?token={token}")
    assert resp.status_code == 200
    assert resp.content == fixtures["photo_content"]
    assert "attachment; filename=" in resp.headers.get("content-disposition", "")
    assert resp.headers.get("accept-ranges") == "bytes"

    # Verify download count incremented
    photo_db = db_session.query(Photo).filter(Photo.id == photo_id).first()
    assert photo_db.download_count == 1


def test_download_range_request(client: TestClient, db_session: Session, tmp_path, monkeypatch):
    """Verify HTTP Range header handling (206 Partial Content) for mobile download resume."""
    fixtures = setup_test_fixtures(db_session, tmp_path)
    monkeypatch.setattr("api.endpoints.public_download.get_storage_backend", lambda: fixtures["storage"])

    token = fixtures["raw_token_a"]
    photo_id = fixtures["photo1"].id

    headers = {"Range": "bytes=0-15"}
    resp = client.get(f"/api/v1/public/photos/{photo_id}/download?token={token}", headers=headers)
    assert resp.status_code == 206
    assert resp.content == fixtures["photo_content"][:16]
    assert resp.headers.get("content-range") == f"bytes 0-15/{len(fixtures['photo_content'])}"
    assert resp.headers.get("content-length") == "16"


def test_download_happy_path_selfie_session(client: TestClient, db_session: Session, tmp_path, monkeypatch):
    """Verify download authorized via selfie search session token."""
    fixtures = setup_test_fixtures(db_session, tmp_path)
    monkeypatch.setattr("api.endpoints.public_download.get_storage_backend", lambda: fixtures["storage"])

    photo_id = fixtures["photo1"].id
    session_id = f"session_{uuid.uuid4().hex}"

    # Mock SelfieSearchService.validate_session_photo to return True for photo1
    with monkeypatch.context() as m:
        m.setattr(
            "services.selfie_service.SelfieSearchService.validate_session_photo",
            lambda self, sess, pid: sess == session_id and str(pid) == str(photo_id),
        )
        resp = client.get(f"/api/v1/public/photos/{photo_id}/download?session={session_id}")
        assert resp.status_code == 200
        assert resp.content == fixtures["photo_content"]


def test_download_negative_cases(client: TestClient, db_session: Session, tmp_path, monkeypatch):
    """Verify negative authorization cases return 403 / 404 / 410 appropriately."""
    fixtures = setup_test_fixtures(db_session, tmp_path)
    monkeypatch.setattr("api.endpoints.public_download.get_storage_backend", lambda: fixtures["storage"])

    token_a = fixtures["raw_token_a"]
    photo1_id = fixtures["photo1"].id  # Matched to A (active)
    photo2_id = fixtures["photo2"].id  # Matched to B (active)
    photo3_id = fixtures["photo3"].id  # Matched to A (pending_review)
    photo4_id = fixtures["photo4"].id  # Event 2 photo

    # 1. No token or session provided -> 403
    r1 = client.get(f"/api/v1/public/photos/{photo1_id}/download")
    assert r1.status_code == 403

    # 2. Expired token -> 410
    r2 = client.get(f"/api/v1/public/photos/{photo2_id}/download?token={fixtures['raw_token_expired']}")
    assert r2.status_code == 410

    # 3. Revoked token -> 404
    r3 = client.get(f"/api/v1/public/photos/{photo2_id}/download?token={fixtures['raw_token_revoked']}")
    assert r3.status_code == 404

    # 4. Token A attempting to download photo matched to Guest B -> 403
    r4 = client.get(f"/api/v1/public/photos/{photo2_id}/download?token={token_a}")
    assert r4.status_code == 403

    # 5. Token A attempting to download photo in pending_review status -> 403
    r5 = client.get(f"/api/v1/public/photos/{photo3_id}/download?token={token_a}")
    assert r5.status_code == 403

    # 6. Token A attempting to download photo from another event -> 403
    r6 = client.get(f"/api/v1/public/photos/{photo4_id}/download?token={token_a}")
    assert r6.status_code == 403

    # 7. Invalid selfie search session -> 403
    with monkeypatch.context() as m:
        m.setattr(
            "services.selfie_service.SelfieSearchService.validate_session_photo",
            lambda self, sess, pid: False,
        )
        r7 = client.get(f"/api/v1/public/photos/{photo1_id}/download?session=invalid_session")
        assert r7.status_code == 403
