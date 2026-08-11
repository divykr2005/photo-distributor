from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from models.face_embedding import FaceEmbedding
from models.guest import Guest, EmbeddingStatus


class FaceEmbeddingRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        guest_id: UUID,
        embedding: list[float],
        quality_score: float | None = None,
        model_version: str = "ArcFace",
        embedding_dim: int = 512,
    ) -> FaceEmbedding:
        record = FaceEmbedding(
            guest_id=guest_id,
            embedding=embedding,
            model_version=model_version,
            embedding_dim=embedding_dim,
            quality_score=quality_score,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_latest_by_guest(self, guest_id: UUID) -> FaceEmbedding | None:
        return (
            self.db.query(FaceEmbedding)
            .filter(FaceEmbedding.guest_id == guest_id)
            .order_by(FaceEmbedding.created_at.desc())
            .first()
        )

    def set_guest_embedding_status(
        self, guest: Guest, status: EmbeddingStatus
    ) -> None:
        guest.embedding_status = status
        self.db.commit()
        self.db.refresh(guest)

    def find_matches(
        self,
        query_embedding: list[float],
        event_id: UUID,
        threshold: float = 0.6,
        limit: int = 20,
    ) -> list[dict]:
        """
        Find guest embeddings similar to query_embedding using pgvector cosine distance.

        Returns list of dicts: [{"guest_id": UUID, "confidence": float}, ...]
        Only returns matches where confidence >= threshold.
        Scoped to guests in the given event.
        """
        # pgvector <=> is cosine distance (0 = identical, 2 = opposite).
        # Cosine similarity = 1 - cosine_distance.
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        sql = text("""
            SELECT
                fe.guest_id,
                1 - (fe.embedding <=> :query_vec) AS confidence
            FROM face_embeddings fe
            JOIN guests g ON g.id = fe.guest_id
            WHERE g.event_id = :event_id
              AND 1 - (fe.embedding <=> :query_vec) >= :threshold
            ORDER BY confidence DESC
            LIMIT :lim
        """)

        rows = self.db.execute(
            sql,
            {
                "query_vec": embedding_str,
                "event_id": str(event_id),
                "threshold": threshold,
                "lim": limit,
            },
        ).fetchall()

        return [
            {"guest_id": row.guest_id, "confidence": round(float(row.confidence), 4)}
            for row in rows
        ]

