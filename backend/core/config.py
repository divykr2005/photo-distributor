from typing import Literal
from urllib.parse import quote_plus

from pydantic import AnyHttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Event Photo Distribution"
    API_V1_STR: str = "/api/v1"

    # App & Env fields
    APP_NAME: str = "AI Event Photo Distribution"
    ENVIRONMENT: Literal["dev", "staging", "prod"] = "dev"
    PORT: int = 8000
    JWT_EXPIRE_MINUTES: int = 30
    FACE_MODEL: str = "buffalo_l"
    SIMILARITY_THRESHOLD: float = 0.55

    # Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "db@123456"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "eventphotos"

    DATABASE_URL: str | None = None

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            # SQLAlchemy async might need postgresql+psycopg but Neon usually gives postgresql://
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            if url.startswith("postgresql://") and not url.startswith("postgresql+psycopg://"):
                url = url.replace("postgresql://", "postgresql+psycopg://", 1)
            return url
        return (
            f"postgresql+psycopg://{quote_plus(self.POSTGRES_USER)}:{quote_plus(self.POSTGRES_PASSWORD)}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Security
    JWT_SECRET: str = "replace_with_secure_secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    COOKIE_DOMAIN: str | None = None

    # SMTP / Email
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str = "noreply@eventphotos.com"
    SMTP_TLS: bool = True

    # Meta WhatsApp Business API
    META_WHATSAPP_TOKEN: str | None = None
    META_WHATSAPP_PHONE_ID: str | None = None
    META_WHATSAPP_TEMPLATE_NAME: str = "event_photo_ready"
    META_WHATSAPP_TEMPLATE_LANG: str = "en_US"
    WHATSAPP_VERIFY_TOKEN: str = "set_a_random_secret_here"

    # Google OAuth & Drive
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_DRIVE_API_KEY: str | None = None

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # Matching pipeline
    MATCH_CONFIDENCE_THRESHOLD: float = 0.6

    # Frontend & External Access
    FRONTEND_URL: AnyHttpUrl
    API_BASE_URL: AnyHttpUrl
    MAGIC_LINK_TTL_MINUTES: int = 60

    @model_validator(mode="after")
    def no_localhost_in_prod(self):
        if self.ENVIRONMENT == "prod":
            for u in (self.FRONTEND_URL, self.API_BASE_URL):
                if "localhost" in str(u) or "127.0.0.1" in str(u):
                    raise ValueError(f"localhost URL in prod: {u}")
        return self
    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")


settings = Settings()


def get_redis_url() -> str:
    """Return REDIS_URL with ssl_cert_reqs normalized for redis-py compatibility."""
    url = settings.REDIS_URL
    if "ssl_cert_reqs=CERT_NONE" in url:
        url = url.replace("ssl_cert_reqs=CERT_NONE", "ssl_cert_reqs=none")
    return url
