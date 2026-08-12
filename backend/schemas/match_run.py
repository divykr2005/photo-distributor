from datetime import datetime
from uuid import UUID
from typing import Optional, Any
from pydantic import BaseModel


class MatchRunCreate(BaseModel):
    force: bool = False
    scope: Optional[str] = "new_photos"  # full_event, new_photos, new_guests


class MatchRunResponse(BaseModel):
    id: UUID
    event_id: UUID
    trigger: str
    scope: str
    params: Optional[Any] = None
    faces_scanned: int
    guests_scanned: int
    auto_confirmed: int
    sent_to_review: int
    rejected: int
    protected_rows: int
    status: str
    error: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True
