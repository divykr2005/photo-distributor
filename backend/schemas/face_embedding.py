from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FaceEmbeddingResponse(BaseModel):
    """
    Public-facing schema for face embedding records.
    NOTE: The 'embedding' vector is intentionally excluded — it must never
    appear in API responses (security requirement from Week 1 spec).
    """
    id: UUID
    guest_id: UUID
    model_version: str
    embedding_dim: int
    quality_score: float | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
