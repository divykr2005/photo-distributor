from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from models.guest import EmbeddingStatus


class GuestCreate(BaseModel):
    event_id: UUID
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=7, max_length=20)
    email: str | None = None
    gender: str | None = None
    notes: str | None = None


class GuestUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    phone: str | None = Field(None, min_length=7, max_length=20)
    email: str | None = None
    gender: str | None = None
    notes: str | None = None


class GuestResponse(BaseModel):
    id: UUID
    event_id: UUID
    first_name: str
    last_name: str
    phone: str
    email: str | None
    gender: str | None
    notes: str | None
    image_path: str | None
    embedding_status: EmbeddingStatus
    consent_given_at: datetime | None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True
