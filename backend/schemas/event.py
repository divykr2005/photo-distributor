from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from models.event import EventStatus


class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    location: str | None = None
    date: datetime


class EventUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    location: str | None = None
    date: datetime | None = None
    status: EventStatus | None = None


class EventResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    location: str | None
    date: datetime
    status: EventStatus
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
