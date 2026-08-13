import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref

from database.session import Base


class EventStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(300), nullable=True)
    date = Column(DateTime(timezone=True), nullable=False)
    status = Column(
        Enum(EventStatus, values_callable=lambda obj: [e.value for e in obj]), default=EventStatus.DRAFT, nullable=False
    )
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    match_threshold = Column(Float, nullable=True)
    review_floor = Column(Float, nullable=True)
    match_margin = Column(Float, nullable=True)

    # Week 3: portal & selfie search config
    portal_enabled = Column(Boolean, nullable=False, default=False)
    portal_expires_at = Column(DateTime(timezone=True), nullable=True)
    selfie_search_enabled = Column(Boolean, nullable=False, default=False)
    timezone = Column(String(64), nullable=False, default="UTC")
    selfie_threshold = Column(Float, nullable=True)  # per-event override (D23)

    creator = relationship("User", backref=backref("events", cascade="all, delete-orphan"))
