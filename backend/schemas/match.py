from datetime import datetime
from uuid import UUID
from typing import Optional, List, Any
from pydantic import BaseModel


class CandidateItem(BaseModel):
    guest_id: str
    guest_name: Optional[str] = None
    score: float
    rank: int


class MatchResponse(BaseModel):
    id: UUID
    event_id: UUID
    guest_id: UUID
    photo_id: UUID
    photo_face_id: UUID
    match_run_id: Optional[UUID] = None
    similarity: float
    threshold_used: float
    decision: str
    status: str
    second_guest_id: Optional[UUID] = None
    second_similarity: Optional[float] = None
    margin: Optional[float] = None
    review_reason: Optional[str] = None
    top_candidates: Optional[List[Any]] = None
    model_version: str
    matched_at: datetime
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MatchActionRequest(BaseModel):
    action: str  # confirm, reject


class ManualMatchRequest(BaseModel):
    photo_face_id: UUID
    guest_id: UUID
