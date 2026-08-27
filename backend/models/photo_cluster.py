import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.session import Base

class PhotoCluster(Base):
    __tablename__ = "photo_clusters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    membership_hash = Column(String(64), nullable=False)
    size = Column(Integer, nullable=False, default=1)
    
    representative_photo_id = Column(UUID(as_uuid=True), ForeignKey("photos.id", ondelete="SET NULL"), nullable=True)
    mean_quality = Column(Float, nullable=True)
    time_span_s = Column(Float, nullable=True)
    
    params = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint('event_id', 'membership_hash', name='uq_photoclusters_event_membership'),
    )

    event = relationship("Event")
    representative_photo = relationship("Photo", foreign_keys=[representative_photo_id])
