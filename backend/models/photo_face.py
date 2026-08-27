import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, backref, deferred

from database.session import Base

try:
    from pgvector.sqlalchemy import Vector
    VECTOR_AVAILABLE = True
except ImportError:
    Vector = None  # type: ignore
    VECTOR_AVAILABLE = False


class PhotoFace(Base):
    __tablename__ = "photo_faces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    photo_id = Column(UUID(as_uuid=True), ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)

    bbox_x = Column(Float, nullable=False)
    bbox_y = Column(Float, nullable=False)
    bbox_w = Column(Float, nullable=False)
    bbox_h = Column(Float, nullable=False)

    det_score = Column(Float, nullable=False)

    # Defer loading embedding vector by default so standard queries don't pull 51MB into RAM
    embedding = deferred(Column(Vector(512) if VECTOR_AVAILABLE else Text, nullable=False))  # type: ignore
    model_version = Column(String(100), nullable=False, default="buffalo_l")
    embedding_dim = Column(Integer, nullable=False, default=512)

    quality_score = Column(Float, nullable=True)
    blur_score = Column(Float, nullable=True)
    face_area_ratio = Column(Float, nullable=True)
    yaw = Column(Float, nullable=True)
    pitch = Column(Float, nullable=True)
    roll = Column(Float, nullable=True)

    # Day 23: New Quality Scoring
    sharpness_score = Column(Float, nullable=True)
    eye_open_score = Column(Float, nullable=True)
    smile_score = Column(Float, nullable=True)
    frontality_score = Column(Float, nullable=True)
    exposure_score = Column(Float, nullable=True)
    composite_quality = Column(Float, nullable=True)
    scoring_model_version = Column(String(100), nullable=True)
    scored_at = Column(DateTime(timezone=True), nullable=True)
    erasure_redacted = Column(Boolean, nullable=False, default=False)

    is_matchable = Column(Boolean, nullable=False, default=True)
    quality_flags = Column(JSONB, nullable=True)

    crop_key = Column(String(512), nullable=True)
    matched_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    photo = relationship("Photo", backref=backref("faces", cascade="all, delete-orphan"))
    event = relationship("Event", backref=backref("photo_faces", cascade="all, delete-orphan"))
