import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref

from database.session import Base

class PhotoMatch(Base):
    __tablename__ = "photo_matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    event_photo_id = Column(UUID(as_uuid=True), ForeignKey("event_photos.id", ondelete="CASCADE"), nullable=False, index=True)
    guest_id = Column(UUID(as_uuid=True), ForeignKey("guests.id", ondelete="CASCADE"), nullable=False, index=True)

    confidence = Column(Float, nullable=False)  # cosine similarity score (0–1)
    face_index = Column(Integer, nullable=False, default=0)  # which face in the photo matched
    is_solo = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    photo = relationship("EventPhoto", backref=backref("matches", cascade="all, delete-orphan"))
    guest = relationship("Guest", backref=backref("matches", cascade="all, delete-orphan"))
