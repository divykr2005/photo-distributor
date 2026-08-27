import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Float, String, DateTime, ForeignKey, UniqueConstraint, Index, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, backref

from database.session import Base


class Match(Base):
    __tablename__ = "matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    guest_id = Column(UUID(as_uuid=True), ForeignKey("guests.id", ondelete="CASCADE"), nullable=False, index=True)
    photo_id = Column(UUID(as_uuid=True), ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True)
    photo_face_id = Column(UUID(as_uuid=True), ForeignKey("photo_faces.id", ondelete="CASCADE"), nullable=False, unique=True)

    match_run_id = Column(UUID(as_uuid=True), ForeignKey("match_runs.id", ondelete="SET NULL"), nullable=True)

    similarity = Column(Float, nullable=False)
    threshold_used = Column(Float, nullable=False)

    decision = Column(String(50), nullable=False)  # auto_confirmed, review, rejected
    status = Column(String(50), nullable=False, default="active")  # active, rejected_by_organizer, manually_added

    second_guest_id = Column(UUID(as_uuid=True), nullable=True)
    second_similarity = Column(Float, nullable=True)
    margin = Column(Float, nullable=True)
    review_reason = Column(String(100), nullable=True)  # in_review_band, below_margin

    top_candidates = Column(JSONB, nullable=True)  # JSON list of top 3 distinct guest candidates
    model_version = Column(String(100), nullable=False, default="buffalo_l")

    matched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Day 23: Best-of-Burst Ranking
    cluster_rank = Column(Integer, nullable=True)
    ranked_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint('photo_face_id', name='uq_matches_photo_face_id'),
        Index('ix_matches_gallery', guest_id, status, cluster_rank, similarity.desc()),
    )

    event = relationship("Event", backref=backref("match_records", cascade="all, delete-orphan"))
    guest = relationship("Guest", backref=backref("match_records", cascade="all, delete-orphan"))
    photo = relationship("Photo", backref=backref("match_records", cascade="all, delete-orphan"))
    photo_face = relationship("PhotoFace", backref=backref("match_record", uselist=False, cascade="all, delete-orphan"))
    match_run = relationship("MatchRun", backref=backref("matches"))
    reviewer = relationship("User")
