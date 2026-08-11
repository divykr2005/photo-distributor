import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref

from database.session import Base

class EventPhoto(Base):
    __tablename__ = "event_photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    
    faces_detected = Column(Integer, default=0)
    status = Column(String, default="pending")  # pending, processing, success, failed
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    event = relationship("Event", backref=backref("photos", cascade="all, delete-orphan"))
    uploader = relationship("User")
