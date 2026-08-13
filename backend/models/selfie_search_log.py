import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref

from database.session import Base


class SelfieSearchLog(Base):
    __tablename__ = "selfie_search_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ip_hash = Column(String(64), nullable=False, index=True)
    user_agent_hash = Column(String(64), nullable=True)

    faces_detected = Column(Integer, nullable=False, default=0)
    threshold_used = Column(Float, nullable=False)
    results_count = Column(Integer, nullable=False, default=0)
    top_similarity = Column(Float, nullable=True)
    session_id = Column(String(64), nullable=True)
    latency_ms = Column(Integer, nullable=False, default=0)
    rejected_reason = Column(String(255), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    event = relationship("Event", backref=backref("selfie_search_logs", cascade="all, delete-orphan"))
