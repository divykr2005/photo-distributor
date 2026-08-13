import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref

from database.session import Base


class NotificationChannel(str, enum.Enum):
    CONSOLE = "console"
    SMTP = "smtp"
    WEBHOOK = "webhook"
    TWILIO_SMS = "twilio_sms"
    TWILIO_WHATSAPP = "twilio_whatsapp"


class NotificationStatus(str, enum.Enum):
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    SKIPPED_OPT_OUT = "skipped_opt_out"
    SKIPPED_DUPLICATE = "skipped_duplicate"


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guest_id = Column(
        UUID(as_uuid=True),
        ForeignKey("guests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel = Column(String(50), nullable=False)
    notification_type = Column(String(50), nullable=False, default="magic_link")
    dedupe_key = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="queued")
    provider = Column(String(100), nullable=True)
    provider_message_id = Column(String(255), nullable=True)
    error = Column(Text, nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    guest = relationship("Guest", backref=backref("notification_logs", cascade="all, delete-orphan"))
    event = relationship("Event", backref=backref("notification_logs", cascade="all, delete-orphan"))
