from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel


class UploadBatchCreate(BaseModel):
    total_files: int = 0


class UploadBatchResponse(BaseModel):
    id: UUID
    event_id: UUID
    created_by: UUID
    total_files: int
    received_files: int
    duplicate_files: int
    rejected_files: int
    processed_files: int = 0
    failed_files: int = 0
    faces_found: int = 0
    matches_created: int = 0
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
