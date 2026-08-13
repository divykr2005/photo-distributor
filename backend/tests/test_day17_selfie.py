from unittest.mock import patch
import uuid
from fastapi.testclient import TestClient
from worker.face_processor import FaceQualityError


def test_public_event_info_and_selfie_disabled(client: TestClient):
    # Register & Login user
    client.post("/api/v1/auth/register", json={"name": "S", "email": "s@ex.com", "password": "p"})
    token = client.post("/api/v1/auth/login", data={"username": "s@ex.com", "password": "p"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create event with default selfie_search_enabled = False
    ev_resp = client.post("/api/v1/events/", json={"title": "Disabled Event", "date": "2026-10-01T10:00:00Z"}, headers=headers)
    event_id = ev_resp.json()["id"]

    # Public info endpoint should return 404 when disabled
    info_resp = client.get(f"/api/v1/public/events/{event_id}/info")
    assert info_resp.status_code == 404

    # Search endpoint should return 404 when disabled
    files = {"file": ("selfie.jpg", b"fakebytes", "image/jpeg")}
    search_resp = client.post(f"/api/v1/public/events/{event_id}/search-selfie", files=files)
    assert search_resp.status_code == 404


def test_selfie_search_flow(client: TestClient, tmp_path):
    # Setup user & event with selfie_search_enabled = True
    client.post("/api/v1/auth/register", json={"name": "S2", "email": "s2@ex.com", "password": "p"})
    token = client.post("/api/v1/auth/login", data={"username": "s2@ex.com", "password": "p"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ev_resp = client.post("/api/v1/events/", json={"title": "Selfie Event", "date": "2026-10-01T10:00:00Z"}, headers=headers)
    event_id = ev_resp.json()["id"]

    # Enable selfie search on event
    edit_resp = client.put(f"/api/v1/events/{event_id}", json={"selfie_search_enabled": True}, headers=headers)
    assert edit_resp.status_code == 200

    # Verify public info works
    info_resp = client.get(f"/api/v1/public/events/{event_id}/info")
    assert info_resp.status_code == 200
    assert info_resp.json()["selfie_search_enabled"] is True

    # 1. Quality gate rejection test (422)
    with patch("worker.face_processor.FaceProcessor.process_image") as mock_process:
        mock_process.side_effect = FaceQualityError("We found two faces — please upload a photo of just yourself.")
        files = {"file": ("multiface.jpg", b"dummybytes", "image/jpeg")}
        rej_resp = client.post(f"/api/v1/public/events/{event_id}/search-selfie", files=files)
        assert rej_resp.status_code == 422
        assert "two faces" in rej_resp.json()["detail"]

    # 2. Successful search test
    dummy_vec = [0.1] * 512
    with patch("worker.face_processor.FaceProcessor.process_image") as mock_process:
        mock_process.return_value = (dummy_vec, 0.95)
        files = {"file": ("selfie.jpg", b"validselfiebytes", "image/jpeg")}
        search_resp = client.post(f"/api/v1/public/events/{event_id}/search-selfie", files=files)
        assert search_resp.status_code == 200
        res_data = search_resp.json()
        assert "session_id" in res_data
        assert res_data["total"] == 0
        session_id = res_data["session_id"]

    # 3. Session media authorization check (unauthorized photo returns 403)
    random_photo_id = str(uuid.uuid4())
    media_resp = client.get(f"/api/v1/public/media/{random_photo_id}/thumb?session={session_id}")
    assert media_resp.status_code == 403
