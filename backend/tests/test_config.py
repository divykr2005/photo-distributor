import os
import pytest
from pydantic import ValidationError

def test_prod_env_rejects_localhost_urls():
    """
    Test that when ENVIRONMENT=prod, attempting to use a localhost URL
    for FRONTEND_URL or API_BASE_URL raises a ValueError (from our @model_validator).
    """
    # Temporarily set environment variables
    os.environ["ENVIRONMENT"] = "prod"
    os.environ["FRONTEND_URL"] = "http://localhost:3000"
    os.environ["API_BASE_URL"] = "http://localhost:8000/api/v1"
    
    # Need to defer importing settings so it picks up the patched env
    from backend.core.config import Settings
    
    with pytest.raises(ValidationError) as exc:
        Settings()
    
    assert "localhost URL in prod" in str(exc.value)
    
    # Cleanup
    del os.environ["ENVIRONMENT"]
    del os.environ["FRONTEND_URL"]
    del os.environ["API_BASE_URL"]

def test_dev_env_allows_localhost_urls():
    """
    Test that when ENVIRONMENT=dev, localhost URLs are permitted.
    """
    os.environ["ENVIRONMENT"] = "dev"
    os.environ["FRONTEND_URL"] = "http://localhost:3000"
    os.environ["API_BASE_URL"] = "http://localhost:8000/api/v1"
    
    from backend.core.config import Settings
    
    settings = Settings()
    assert str(settings.FRONTEND_URL).rstrip("/") == "http://localhost:3000"
    assert str(settings.API_BASE_URL).rstrip("/") == "http://localhost:8000/api/v1"
    
    # Cleanup
    del os.environ["ENVIRONMENT"]
    del os.environ["FRONTEND_URL"]
    del os.environ["API_BASE_URL"]
