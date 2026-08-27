import enum
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref

from database.session import Base


class EmbeddingStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class Guest(Base):
    __tablename__ = "guests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(255), nullable=True)
    gender = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    image_path = Column(String(500), nullable=True)
    embedding_status = Column(
        Enum(EmbeddingStatus, values_callable=lambda obj: [e.value for e in obj]), default=EmbeddingStatus.PENDING, nullable=False
    )
    consent_given_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    wrapped_dek = Column(LargeBinary, nullable=True)
    dek_key_id = Column(String(100), nullable=True)
    expires_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) + timedelta(days=15),
    )

    # Week 3: notification fields
    notify_opt_out_at = Column(DateTime(timezone=True), nullable=True)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)

    event = relationship("Event", backref=backref("guests", cascade="all, delete-orphan"))
    zip_archives = relationship("ZipArchive", back_populates="guest", cascade="all, delete-orphan")

