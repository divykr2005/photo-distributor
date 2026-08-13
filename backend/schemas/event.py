from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from models.event import EventStatus


class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = None
    date: datetime
    portal_enabled: bool = False
    portal_expires_at: Optional[datetime] = None
    selfie_search_enabled: bool = False
    timezone: str = "UTC"
    selfie_threshold: Optional[float] = None


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = None
    date: Optional[datetime] = None
    status: Optional[EventStatus] = None
    portal_enabled: Optional[bool] = None
    portal_expires_at: Optional[datetime] = None
    selfie_search_enabled: Optional[bool] = None
    timezone: Optional[str] = None
    selfie_threshold: Optional[float] = None


class EventResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    date: datetime
    status: EventStatus
    portal_enabled: bool = False
    portal_expires_at: Optional[datetime] = None
    selfie_search_enabled: bool = False
    timezone: str = "UTC"
    selfie_threshold: Optional[float] = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
