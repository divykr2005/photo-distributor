from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from core.security import create_access_token
from models.consent import BiometricConsent
from models.event import Event
from models.guest import Guest
from models.match import Match
from models.photo import Photo
from models.photo_face import PhotoFace
from models.user import User


def _authenticate(client: TestClient, user: User) -> dict[str, str]:
    client.cookies.set("access_token", create_access_token({"sub": str(user.id)}))
    client.cookies.set("csrf_token", "privacy-test")
    return {"x-csrf-token": "privacy-test"}


def _user(db_session, label: str) -> User:
    user = User(name=label, email=f"{label}-{uuid4()}@example.com", password_hash="hash")
    db_session.add(user)
    db_session.flush()
    return user


def test_dsar_export_returns_404_for_unknown_guest(client: TestClient, db_session):
    user = _user(db_session, "owner")
    db_session.commit()
    headers = _authenticate(client, user)
    response = client.get(f"/api/v1/guests/{uuid4()}/dsar-export", headers=headers)
    assert response.status_code == 404


def test_dsar_export_uses_current_consent_and_match_models(client: TestClient, db_session):
    user = _user(db_session, "owner")
    event = Event(title="Privacy Event", date=datetime.now(timezone.utc), created_by=user.id)
    db_session.add(event)
    db_session.flush()
    guest = Guest(
        event_id=event.id,
        first_name="Ada",
        last_name="Lovelace",
        phone="+15550001111",
        email="ada@example.com",
    )
    db_session.add(guest)
    db_session.flush()
    consent = BiometricConsent(
        guest_id=guest.id,
        consent_text_version="v1",
        phone_e164=guest.phone,
        notice_text_snapshot="Test notice",
    )
    photo = Photo(
        event_id=event.id,
        uploaded_by=user.id,
        original_filename="photo.jpg",
        storage_key="tests/photo.jpg",
        content_hash=uuid4().hex,
        mime_type="image/jpeg",
        file_size=10,
        status="processed",
    )
    db_session.add_all([consent, photo])
    db_session.flush()
    face = PhotoFace(
        photo_id=photo.id,
        event_id=event.id,
        bbox_x=0,
        bbox_y=0,
        bbox_w=10,
        bbox_h=10,
        det_score=0.99,
        embedding=[0.1] * 512,
    )
    db_session.add(face)
    db_session.flush()
    db_session.add(Match(
        event_id=event.id,
        guest_id=guest.id,
        photo_id=photo.id,
        photo_face_id=face.id,
        similarity=0.91,
        threshold_used=0.6,
        decision="auto_confirmed",
        status="active",
    ))
    db_session.commit()

    headers = _authenticate(client, user)
    response = client.get(f"/api/v1/guests/{guest.id}/dsar-export", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["consent_records"][0]["consent_text_version"] == "v1"
    assert payload["matches"][0]["photo_id"] == str(photo.id)
    assert payload["matches"][0]["similarity"] == 0.91


def test_dsar_export_forbids_another_organizer(client: TestClient, db_session):
    owner = _user(db_session, "owner")
    attacker = _user(db_session, "attacker")
    event = Event(title="Private Event", date=datetime.now(timezone.utc), created_by=owner.id)
    db_session.add(event)
    db_session.flush()
    guest = Guest(event_id=event.id, first_name="Private", last_name="Guest", phone="+15550002222")
    db_session.add(guest)
    db_session.commit()

    headers = _authenticate(client, attacker)
    response = client.get(f"/api/v1/guests/{guest.id}/dsar-export", headers=headers)
    assert response.status_code == 403
