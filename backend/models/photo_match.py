import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.session import Base

class PhotoMatch(Base):
    __tablename__ = "photo_matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    event_photo_id = Column(UUID(as_uuid=True), ForeignKey("event_photos.id", ondelete="CASCADE"), nullable=False)
    guest_id = Column(UUID(as_uuid=True), ForeignKey("guests.id", ondelete="CASCADE"), nullable=False)
    
    confidence = Column(Float, nullable=False)  # cosine similarity score
    is_solo = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    photo = relationship("EventPhoto", backref="matches")
    guest = relationship("Guest", backref="matches")
