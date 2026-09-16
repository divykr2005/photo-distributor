import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.session import Base

class BiometricConsent(Base):
    __tablename__ = "biometric_consents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guest_id = Column(
        UUID(as_uuid=True),
        ForeignKey("guests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    consent_text_version = Column(String(50), nullable=False)
    phone_e164 = Column(String(20), nullable=False)
    given_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    # Populated when the guest explicitly withdraws biometric consent.
    # A non-null value blocks any further embedding extraction or matching.
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    # Human-readable evidence: the exact notice text that was shown, not just a version.
    notice_text_snapshot = Column(Text, nullable=True)

    guest = relationship("Guest", backref="biometric_consents")
