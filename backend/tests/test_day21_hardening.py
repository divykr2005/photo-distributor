import hashlib
import io
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from main import app
from database.session import SessionLocal
from models.event import Event
from models.guest import Guest
from models.guest_access_token import GuestAccessToken
from models.photo import Photo
from models.match import Match
from api.endpoints.magic_links import _generate_token, _hash_token


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _create_dummy_jpeg(width: int = 200, height: int = 200) -> bytes:
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ── 1. Security Headers Test ──

def test_security_headers(client):
    response = client.get("/api/v1/public/guest/randomnonexistentcode123")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("Referrer-Policy") == "no-referrer"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "default-src 'self'" in response.headers.get("Content-Security-Policy", "")


from models.user import User


@pytest.fixture
def user(db):
    user_obj = User(
        email=f"organizer_{uuid4().hex[:8]}@example.com",
        password_hash="hashed_pw",
        name="Organizer Test",
    )
    db.add(user_obj)
    db.flush()
    return user_obj


# ── 2. Robots.txt Test ──

def test_robots_txt(client):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "Disallow: /g/" in response.text
    assert "Disallow: /events/*/find" in response.text


# ── 3. Enumeration Defense & Token Lifecycle Test ──

def test_enumeration_defense_and_token_lifecycle(db, client, user):
    # Setup test event and guest
    event = Event(title="Hardening Gala", date=datetime.now(timezone.utc), selfie_search_enabled=True, created_by=user.id)
    db.add(event)
    db.flush()

    guest = Guest(event_id=event.id, first_name="Alice", last_name="Smith", phone="+15550001111")
    db.add(guest)
    db.flush()

    # Active token (will be revoked)
    _, raw_revoked = _generate_token(db, guest, event, user.id)
    db.commit()

    # Expired token
    token_row_expired, raw_expired = _generate_token(db, guest, event, user.id)
    db.commit()

    # Active token (will be live)
    token_row_new, raw_new = _generate_token(db, guest, event, user.id)
    db.commit()

    # Configure exact test states
    token_row_expired.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    token_row_expired.revoked_at = None
    token_row_new.revoked_at = None
    token_row_new.expires_at = datetime.now(timezone.utc) + timedelta(days=90)
    db.commit()

    # 1. Invalid / malformed code -> 404 uniform body
    res1 = client.get("/api/v1/public/guest/nonexistentcode9999999")
    assert res1.status_code == 404
    assert res1.json() == {"detail": "Link not found"}

    # 2. Revoked code -> 404 uniform body
    res2 = client.get(f"/api/v1/public/guest/{raw_revoked}")
    assert res2.status_code == 404
    assert res2.json() == {"detail": "Link not found"}

    # 3. Expired code -> 410 Gone
    res3 = client.get(f"/api/v1/public/guest/{raw_expired}")
    assert res3.status_code == 410
    assert res3.json() == {"detail": "This link has expired. Please contact your event organizer for a new one."}

    # 4. Valid active new code -> 200 OK
    res4 = client.get(f"/api/v1/public/guest/{raw_new}")
    assert res4.status_code == 200
    assert res4.json()["first_name"] == "Alice"


from services.storage import get_storage_backend


from models.photo_face import PhotoFace


# ── 4. Full Guest Journey Integration Test ──

def test_full_guest_journey_integration(db, client, user, monkeypatch):
    monkeypatch.setattr("api.endpoints.public_zip._check_disk_watermark", lambda path=".": True)
    storage = get_storage_backend()

    event = Event(title="EndToEnd Gala", date=datetime.now(timezone.utc), selfie_search_enabled=True, created_by=user.id)
    db.add(event)
    db.flush()

    guest = Guest(event_id=event.id, first_name="Bob", last_name="Doe", phone="+15552223333")
    db.add(guest)
    db.flush()

    # Create original photo file
    img_bytes = _create_dummy_jpeg()
    orig_key = f"tests/orig_{uuid4().hex}.jpg"
    thumb_key = f"tests/thumb_{uuid4().hex}.jpg"
    web_key = f"tests/web_{uuid4().hex}.jpg"

    storage.put(orig_key, img_bytes)
    storage.put(thumb_key, img_bytes)
    storage.put(web_key, img_bytes)

    photo = Photo(
        event_id=event.id,
        uploaded_by=user.id,
        storage_key=orig_key,
        thumb_key=thumb_key,
        web_key=web_key,
        content_hash=hashlib.sha256(img_bytes).hexdigest(),
        mime_type="image/jpeg",
        file_size=len(img_bytes),
        original_filename="bob_portrait.jpg",
    )
    db.add(photo)
    db.flush()

    face = PhotoFace(
        photo_id=photo.id,
        event_id=event.id,
        bbox_x=10,
        bbox_y=10,
        bbox_w=50,
        bbox_h=50,
        det_score=0.99,
        quality_score=0.95,
        embedding=[0.1] * 512,
    )
    db.add(face)
    db.flush()

    match = Match(
        event_id=event.id,
        photo_id=photo.id,
        guest_id=guest.id,
        photo_face_id=face.id,
        similarity=0.92,
        threshold_used=0.45,
        decision="confirmed",
        status="active",
    )
    db.add(match)
    db.commit()

    # 1. Generate magic link
    _, raw_token = _generate_token(db, guest, event, user.id)
    db.commit()

    # 2. Access Portal
    res_portal = client.get(f"/api/v1/public/guest/{raw_token}")
    assert res_portal.status_code == 200
    assert res_portal.json()["photo_count"] == 1

    # 3. Fetch Photos list
    res_photos = client.get(f"/api/v1/public/guest/{raw_token}/photos")
    assert res_photos.status_code == 200
    assert len(res_photos.json()["photos"]) == 1

    # 4. Fetch Media derivative (thumb)
    res_thumb = client.get(f"/api/v1/public/media/{photo.id}/thumb?token={raw_token}")
    assert res_thumb.status_code == 200
    assert res_thumb.headers["content-type"] == "image/jpeg"

    # 5. Download Original photo
    res_dl = client.get(f"/api/v1/public/photos/{photo.id}/download?token={raw_token}")
    assert res_dl.status_code == 200
    assert len(res_dl.content) == len(img_bytes)

    # 6. Request ZIP Archive
    res_zip = client.post(f"/api/v1/public/guest/{raw_token}/zip")
    assert res_zip.status_code in (200, 202)
    job_id = res_zip.json()["job_id"]
    assert job_id is not None
