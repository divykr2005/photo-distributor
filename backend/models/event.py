import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Index, String, Text, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref

from database.session import Base


class EventStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class UploadMode(str, enum.Enum):
    # Only allow biometric extraction when the organizer has confirmed that
    # every subject in every uploaded image has given prior explicit consent.
    CONTROLLED = "controlled"
    # Default. Organizer-uploaded photos contain unknown bystanders.
    # Biometric extraction is BLOCKED; only non-biometric workflows run.
    OPEN = "open"


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

    wrapped_kek = Column(LargeBinary, nullable=True)
    kek_key_id = Column(String(100), nullable=True)

    match_threshold = Column(Float, nullable=True)
    review_floor = Column(Float, nullable=True)
    match_margin = Column(Float, nullable=True)

    # Week 3: portal & selfie search config
    portal_enabled = Column(Boolean, nullable=False, default=False)
    portal_expires_at = Column(DateTime(timezone=True), nullable=True)
    selfie_search_enabled = Column(Boolean, nullable=False, default=False)
    timezone = Column(String(64), nullable=False, default="UTC")
    selfie_threshold = Column(Float, nullable=True)  # per-event override (D23)
    # Controls whether biometric face extraction is allowed for uploaded photos.
    # Defaults to 'open' (blocked). Must be explicitly set to 'controlled' by
    # the organizer after confirming all subjects have given prior consent.
    upload_mode = Column(
        Enum(UploadMode, values_callable=lambda obj: [e.value for e in obj]),
        default=UploadMode.OPEN,
        nullable=False,
    )
    # P1: Organizer must confirm that no children under 16 are subjects in this
    # event's photos before biometric extraction is enabled.
    # COPPA (US) / UK-GDPR / GDPR Art.8 all require special handling for under-16s.
    # Default False means extraction is blocked until explicitly confirmed.
    min_age_confirmed = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_events_owner_date", created_by, date.desc(), id.desc()),
    )

    creator = relationship("User", backref=backref("events", cascade="all, delete-orphan"))
