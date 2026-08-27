import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, UniqueConstraint, BigInteger, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref

from database.session import Base


class Photo(Base):
    __tablename__ = "photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("upload_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    original_filename = Column(String(255), nullable=False)
    storage_key = Column(String(512), nullable=False)
    web_key = Column(String(512), nullable=True)
    thumb_key = Column(String(512), nullable=True)

    content_hash = Column(String(64), nullable=False)
    mime_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)

    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    exif_taken_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(String(50), nullable=False, default="pending", index=True)  # pending, queued, processing, processed, failed
    face_count = Column(Integer, nullable=False, default=0)
    download_count = Column(Integer, nullable=False, default=0)
    processing_error = Column(Text, nullable=True)
    attempts = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    phash = Column(BigInteger, nullable=True)
    dhash = Column(BigInteger, nullable=True)
    hash_computed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    dup_cluster_id = Column(UUID(as_uuid=True), ForeignKey("photo_clusters.id", ondelete="SET NULL"), nullable=True, index=True)
    is_cluster_representative = Column(Boolean, default=False)
    storage_tier = Column(Enum("local", "s3", name="storage_tier_enum"), default="local", index=True)

    __table_args__ = (
        UniqueConstraint('event_id', 'content_hash', name='uq_photos_event_content_hash'),
    )

    event = relationship("Event", backref=backref("photo_records", cascade="all, delete-orphan"))
    batch = relationship("UploadBatch", backref=backref("photos", cascade="all, delete-orphan"))
    uploader = relationship("User")
