import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref

from database.session import Base


class UploadBatch(Base):
    __tablename__ = "upload_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    total_files = Column(Integer, nullable=False, default=0)
    received_files = Column(Integer, nullable=False, default=0)
    duplicate_files = Column(Integer, nullable=False, default=0)
    rejected_files = Column(Integer, nullable=False, default=0)
    status = Column(String(50), nullable=False, default="active")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    event = relationship("Event", backref=backref("upload_batches", cascade="all, delete-orphan"))
    creator = relationship("User")
