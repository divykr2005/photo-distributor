from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class PublicEventInfo(BaseModel):
    """Public info returned for /public/events/{event_id}/info."""
    id: UUID
    title: str
    date: datetime
    selfie_search_enabled: bool


class SelfieSearchPhotoItem(BaseModel):
    """Photo item returned in selfie search results."""
    id: UUID
    thumb_url: str
    web_url: str
    taken_at: Optional[datetime] = None
    filename: Optional[str] = None


class SelfieSearchResponse(BaseModel):
    """Result returned by POST /public/events/{event_id}/search-selfie."""
    session_id: str
    total: int
    photos: List[SelfieSearchPhotoItem]
