import os
from unittest.mock import patch
from fastapi.testclient import TestClient

def test_register_and_login(client: TestClient):
    # Register user
    resp = client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "test@example.com"
    
    # Duplicate registration should fail
    resp2 = client.post("/api/v1/auth/register", json={
        "name": "Test User 2",
        "email": "test@example.com",
        "password": "password123"
    })
    assert resp2.status_code == 409
    
    # Login
    login_resp = client.post("/api/v1/auth/login", data={
        "username": "test@example.com",
        "password": "password123"
    })
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data

def test_events_crud(client: TestClient):
    # Register & Login
    client.post("/api/v1/auth/register", json={"name": "E", "email": "e@ex.com", "password": "p"})
    token = client.post("/api/v1/auth/login", data={"username": "e@ex.com", "password": "p"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create Event
    ev_resp = client.post("/api/v1/events/", json={
        "title": "My Event",
        "date": "2026-10-01T10:00:00Z"
    }, headers=headers)
    assert ev_resp.status_code == 201
    event_id = ev_resp.json()["id"]
    
    # List Events
    list_resp = client.get("/api/v1/events/", headers=headers)
    assert len(list_resp.json()) == 1
    
    # Edit Event
    edit_resp = client.put(f"/api/v1/events/{event_id}", json={
        "title": "Updated Event"
    }, headers=headers)
    assert edit_resp.status_code == 200
    assert edit_resp.json()["title"] == "Updated Event"
    
def test_guest_registration_and_photo(client: TestClient, tmp_path):
    # Setup
    client.post("/api/v1/auth/register", json={"name": "G", "email": "g@ex.com", "password": "p"})
    token = client.post("/api/v1/auth/login", data={"username": "g@ex.com", "password": "p"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    ev_resp = client.post("/api/v1/events/", json={"title": "Guest Event", "date": "2026-10-01T10:00:00Z"}, headers=headers)
    event_id = ev_resp.json()["id"]
    
    # Register Guest
    guest_resp = client.post("/api/v1/guests/", json={
        "first_name": "John",
        "last_name": "Doe",
        "phone": "1234567890",
        "event_id": event_id
    }, headers=headers)
    assert guest_resp.status_code == 201
    guest_id = guest_resp.json()["id"]
    assert guest_resp.json()["embedding_status"] == "pending"
    
    # Create a dummy image file
    test_img_path = tmp_path / "test.jpg"
    test_img_path.write_bytes(b"dummy image data")
    
    # Mock FaceProcessor to bypass actual DeepFace/OpenCV logic
    with patch("worker.face_processor.FaceProcessor.process_image") as mock_process:
        # 512-dim embedding dummy
        mock_process.return_value = ([0.1] * 512, 0.99)
        
        with open(test_img_path, "rb") as f:
            photo_resp = client.post(f"/api/v1/guests/{guest_id}/photo", files={"file": ("test.jpg", f, "image/jpeg")}, headers=headers)
            
        assert photo_resp.status_code == 200
        assert photo_resp.json()["embedding_status"] == "success"
        
    # Get guest to check status
    get_resp = client.get(f"/api/v1/guests/{guest_id}", headers=headers)
    assert get_resp.json()["embedding_status"] == "success"
    
    # Delete Guest
    del_resp = client.delete(f"/api/v1/guests/{guest_id}", headers=headers)
    assert del_resp.status_code == 204
