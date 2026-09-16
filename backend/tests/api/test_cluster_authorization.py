from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from core.security import create_access_token
from models.event import Event
from models.user import User


def _user(db_session, label: str) -> User:
    user = User(name=label, email=f"{label}-{uuid4()}@example.com", password_hash="hash")
    db_session.add(user)
    db_session.flush()
    return user


def _authenticate(client: TestClient, user: User) -> dict[str, str]:
    client.cookies.set("access_token", create_access_token({"sub": str(user.id)}))
    client.cookies.set("csrf_token", "cluster-test")
    return {"x-csrf-token": "cluster-test"}


def test_cluster_list_requires_authentication(client: TestClient):
    response = client.get(f"/api/v1/events/{uuid4()}/clusters")
    assert response.status_code == 401


def test_cluster_list_hides_another_organizers_event(client: TestClient, db_session):
    owner = _user(db_session, "owner")
    attacker = _user(db_session, "attacker")
    event = Event(title="Owned Event", date=datetime.now(timezone.utc), created_by=owner.id)
    db_session.add(event)
    db_session.commit()

    headers = _authenticate(client, attacker)
    response = client.get(f"/api/v1/events/{event.id}/clusters", headers=headers)
    assert response.status_code == 404
