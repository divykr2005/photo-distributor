import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# We will patch the config to use a test database
os.environ["POSTGRES_DB"] = "eventphotos_test"

from urllib.parse import quote_plus
from core.config import settings
from database.session import Base
from main import app
from api.dependencies import get_db

# Create test database URL
TEST_SQLALCHEMY_DATABASE_URI = (
    f"postgresql+psycopg://{quote_plus(settings.POSTGRES_USER)}:{quote_plus(settings.POSTGRES_PASSWORD)}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/eventphotos_test"
)

# Admin engine to create/drop the test database
ADMIN_URI = (
    f"postgresql+psycopg://{quote_plus(settings.POSTGRES_USER)}:{quote_plus(settings.POSTGRES_PASSWORD)}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/postgres"
)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    # Connect to default postgres database to create the test database
    import psycopg
    conn = psycopg.connect(
        dbname="postgres",
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        autocommit=True
    )
    cursor = conn.cursor()
    cursor.execute("DROP DATABASE IF EXISTS eventphotos_test")
    cursor.execute("CREATE DATABASE eventphotos_test")
    cursor.close()
    conn.close()

    # Now run migrations on the test database
    import alembic.config
    import alembic.command
    alembic_cfg = alembic.config.Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_SQLALCHEMY_DATABASE_URI.replace('%', '%%'))
    alembic.command.upgrade(alembic_cfg, "head")
    
    yield

    # Teardown
    engine = create_engine(TEST_SQLALCHEMY_DATABASE_URI)
    engine.dispose()
    
    conn = psycopg.connect(
        dbname="postgres",
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        autocommit=True
    )
    cursor = conn.cursor()
    # Force disconnect users from test db before dropping
    cursor.execute("""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = 'eventphotos_test'
        AND pid <> pg_backend_pid();
    """)
    cursor.execute("DROP DATABASE IF EXISTS eventphotos_test")
    cursor.close()
    conn.close()

@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(TEST_SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
    yield engine
    engine.dispose()

@pytest.fixture(scope="function")
def db_session(db_engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    yield session
    session.close()
    
    # Clean up tables between tests to ensure isolation
    with db_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
