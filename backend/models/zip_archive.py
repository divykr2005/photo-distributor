import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, BigInteger, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.session import Base


class ZipStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ZipArchive(Base):
    __tablename__ = "zip_archives"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guest_id = Column(UUID(as_uuid=True), ForeignKey("guests.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    match_set_hash = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default=ZipStatus.PENDING.value, index=True)
    file_path = Column(String(512), nullable=True)
    photo_count = Column(Integer, nullable=False, default=0)
    total_bytes = Column(BigInteger, nullable=False, default=0)
    processed_photos = Column(Integer, nullable=False, default=0)
    processed_bytes = Column(BigInteger, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    guest = relationship("Guest", back_populates="zip_archives")
    event = relationship("Event")
