import pytest
from uuid import uuid4
from datetime import datetime, timezone
import json
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.testclient import TestClient

from models.user import User
from models.event import Event
from models.guest import Guest
from core.security import get_password_hash
from main import app

@pytest.fixture
def setup_data(db_session: Session):
    user = User(
        name="Test Organizer",
        email=f"org_{uuid4()}@example.com",
        password_hash=get_password_hash("password")
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    event = Event(
        title="Test Event",
        date=datetime.now(timezone.utc),
        created_by=user.id
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    guest = Guest(
        event_id=event.id,
        first_name="John",
        last_name="Doe",
        phone="+1234567890",
        embedding_status="success"
    )
    db_session.add(guest)
    db_session.commit()
    db_session.refresh(guest)
    
    # Mock an embedding (512 dimensions)
    mock_embedding = "[" + ",".join(["0.1"] * 512) + "]"
    db_session.execute(
        text("""
        INSERT INTO face_embeddings (guest_id, embedding)
        VALUES (:guest_id, :embedding)
        """),
        {"guest_id": guest.id, "embedding": mock_embedding}
    )
    db_session.commit()

    return {"user": user, "event": event, "guest": guest}

def get_auth_cookies_and_headers(client: TestClient, user: User):
    # Log in
    resp = client.post("/api/v1/auth/login", data={"username": user.email, "password": "password"})
    assert resp.status_code == 200
    access_token = resp.cookies.get("access_token")
    csrf_token = resp.cookies.get("csrf_token")
    return {"access_token": access_token, "csrf_token": csrf_token}, {"X-CSRF-Token": csrf_token}

def test_guest_update_forbids_embedding(client: TestClient, db_session: Session, setup_data):
    guest = setup_data["guest"]
    cookies, headers = get_auth_cookies_and_headers(client, setup_data["user"])

    # Attempt to inject embedding
    payload = {
        "first_name": "Johnny",
        "embedding": [0.9, 0.8, 0.7]
    }
    resp = client.put(f"/api/v1/guests/{guest.id}", json=payload, cookies=cookies, headers=headers)
    
    # Should be 422 Unprocessable Entity due to extra="forbid"
    assert resp.status_code == 422
    assert "extra_forbidden" in resp.text

def test_guest_update_preserves_embedding(client: TestClient, db_session: Session, setup_data):
    guest = setup_data["guest"]
    cookies, headers = get_auth_cookies_and_headers(client, setup_data["user"])

    payload = {
        "first_name": "Johnny",
        "last_name": "Doe",
        "phone": "+1234567890"
    }
    resp = client.put(f"/api/v1/guests/{guest.id}", json=payload, cookies=cookies, headers=headers)
    assert resp.status_code == 200
    
    # Check that embedding is still intact
    result = db_session.execute(
        text("SELECT embedding::text FROM face_embeddings WHERE guest_id = :guest_id"),
        {"guest_id": guest.id}
    ).scalar()
    assert result is not None
    assert "[0.1" in result # It should be the original embedding

def test_guest_update_optimistic_concurrency(client: TestClient, db_session: Session, setup_data):
    guest = setup_data["guest"]
    cookies, headers = get_auth_cookies_and_headers(client, setup_data["user"])

    # Get current guest to read updated_at
    resp = client.get(f"/api/v1/guests/{guest.id}", cookies=cookies, headers=headers)
    assert resp.status_code == 200
    
    # Refresh guest from db to get exact datetime
    db_session.refresh(guest)
    server_etag = str(guest.updated_at.timestamp())
    
    # Valid If-Match
    headers["If-Match"] = server_etag
    payload = {"first_name": "Jane"}
    resp = client.put(f"/api/v1/guests/{guest.id}", json=payload, cookies=cookies, headers=headers)
    assert resp.status_code == 200

    # Try again with the old ETag (should fail)
    payload = {"first_name": "Jack"}
    resp = client.put(f"/api/v1/guests/{guest.id}", json=payload, cookies=cookies, headers=headers)
    assert resp.status_code == 412
    assert "Precondition Failed" in resp.text
