import os
from uuid import uuid4
from fastapi.testclient import TestClient

import pytest
from models.user import User

@pytest.fixture
def test_user(db_session):
    user = User(
        id=uuid4(),
        email="test@example.com",
        name="Test User"
    )
    db_session.add(user)
    db_session.commit()
    return user

def test_guest_patch_preserves_biometrics(client: TestClient, db_session, test_user):
    from models.event import Event
    from models.guest import Guest

    # 1. Create an event
    from datetime import datetime, timezone
    event = Event(id=uuid4(), title="Test Event", date=datetime.now(timezone.utc), created_by=test_user.id)
    db_session.add(event)

    # 2. Create a guest with biometric fields
    guest = Guest(
        id=uuid4(),
        event_id=event.id,
        first_name="Original",
        last_name="Name",
        phone="1234567890",
        image_path="uploads/guests/fake.jpg",
        embedding_status="success",
        wrapped_dek=b"dummy_dek",
        dek_key_id="local"
    )
    db_session.add(guest)
    db_session.commit()

    # Authenticate the client as test_user by overriding dependency
    from api.dependencies import get_current_user
    client.app.dependency_overrides[get_current_user] = lambda: test_user

    # 3. Patch the guest name
    response = client.patch(
        f"/api/v1/guests/{guest.id}",
        json={"first_name": "Updated"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["last_name"] == "Name"
    assert data["image_path"] == "uploads/guests/fake.jpg"
    assert data["embedding_status"] == "success"

    # Verify DB state directly
    db_session.refresh(guest)
    assert guest.first_name == "Updated"
    assert guest.image_path == "uploads/guests/fake.jpg"
    assert guest.embedding_status == "success"

    # Cleanup override
    client.app.dependency_overrides.pop(get_current_user, None)
