"""
conftest.py for unit tests that do NOT need a real database.

The global tests/conftest.py auto-uses setup_test_db which spins up a full
Postgres instance. The P0 hardening tests are pure unit tests and must be
runnable without any DB. This file overrides that fixture locally.
"""
import os
import pytest

# Prevent the global session-scoped DB setup from running for this directory.
# We set a dummy DATABASE_URL so Settings can parse without erroring out.
os.environ.setdefault("POSTGRES_DB", "eventphotos_test")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("API_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """No-op: unit tests in this package do not need a live database."""
    yield
