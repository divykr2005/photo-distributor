def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_readyz_success(client):
    response = client.get("/readyz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
    assert data["redis"] == "ok"

def test_readyz_db_failure(client, monkeypatch):
    # Mock get_db to raise an exception
    from api.dependencies import get_db
    from main import app
    
    def override_get_db_fail():
        raise Exception("DB connection failed")
        yield
        
    app.dependency_overrides[get_db] = override_get_db_fail
    
    response = client.get("/readyz")
    assert response.status_code == 503
    
    app.dependency_overrides.clear()
