
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Event Photo Distribution"
    API_V1_STR: str = "/api/v1"

    # App & Env fields
    APP_NAME: str = "AI Event Photo Distribution"
    ENV: str = "development"
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

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql+psycopg://{quote_plus(self.POSTGRES_USER)}:{quote_plus(self.POSTGRES_PASSWORD)}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Security
    JWT_SECRET: str = "replace_with_secure_secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # Google OAuth & Drive
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_DRIVE_API_KEY: str | None = None

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # Matching pipeline
    MATCH_CONFIDENCE_THRESHOLD: float = 0.6

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")


settings = Settings()
