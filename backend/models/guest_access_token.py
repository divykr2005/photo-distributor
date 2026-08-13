import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref

from database.session import Base


class GuestAccessToken(Base):
    __tablename__ = "guest_access_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guest_id = Column(
        UUID(as_uuid=True),
        ForeignKey("guests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    token_prefix = Column(String(8), nullable=False)

    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    access_count = Column(Integer, nullable=False, default=0)

    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
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

    guest = relationship("Guest", backref=backref("access_tokens", cascade="all, delete-orphan"))
    event = relationship("Event", backref=backref("guest_access_tokens", cascade="all, delete-orphan"))
    creator = relationship("User")
