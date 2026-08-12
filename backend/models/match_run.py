import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, backref

from database.session import Base


class MatchRun(Base):
    __tablename__ = "match_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)

    trigger = Column(String(50), nullable=False)  # photo_ingest, guest_registered, manual_rerun, threshold_change
    scope = Column(String(50), nullable=False)    # full_event, new_photos, new_guests
    params = Column(JSONB, nullable=True)

    faces_scanned = Column(Integer, nullable=False, default=0)
    guests_scanned = Column(Integer, nullable=False, default=0)

    auto_confirmed = Column(Integer, nullable=False, default=0)
    sent_to_review = Column(Integer, nullable=False, default=0)
    rejected = Column(Integer, nullable=False, default=0)
    protected_rows = Column(Integer, nullable=False, default=0)

    status = Column(String(50), nullable=False, default="running")  # running, completed, failed
    error = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    event = relationship("Event", backref=backref("match_runs", cascade="all, delete-orphan"))
