import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref

from database.session import Base

try:
    from pgvector.sqlalchemy import Vector
    VECTOR_AVAILABLE = True
except ImportError:
    from sqlalchemy import Text
    VECTOR_AVAILABLE = False


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guest_id = Column(
        UUID(as_uuid=True),
        ForeignKey("guests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    embedding = Column(Vector(512) if VECTOR_AVAILABLE else Text, nullable=False)
    model_version = Column(String(100), nullable=False, default="ArcFace")
    embedding_dim = Column(Integer, nullable=False, default=512)
    quality_score = Column(Float, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    guest = relationship("Guest", backref=backref("face_embeddings", cascade="all, delete-orphan"))
