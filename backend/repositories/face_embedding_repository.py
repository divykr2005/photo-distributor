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
        from services.crypto.envelope import get_or_unwrap_kek, get_or_unwrap_dek, encrypt_embedding
        import json
        
        # Dual-write: encrypt the embedding first
        guest = self.db.query(Guest).filter(Guest.id == guest_id).first()
        ciphertext, nonce = None, None
        
        if guest and guest.wrapped_dek:
            from models.event import Event
            event = self.db.query(Event).filter(Event.id == guest.event_id).first()
            if event and event.wrapped_kek:
                kek_blob = event.wrapped_kek # type: ignore
                kek_nonce, kek_wrapped = kek_blob[:12], kek_blob[12:]
                import typing
                kek = get_or_unwrap_kek(str(event.id), typing.cast(bytes, kek_wrapped), typing.cast(bytes, kek_nonce))
                
                dek_blob = guest.wrapped_dek # type: ignore
                dek_nonce, dek_wrapped = dek_blob[:12], dek_blob[12:]
                dek = get_or_unwrap_dek(str(guest_id), typing.cast(bytes, dek_wrapped), typing.cast(bytes, dek_nonce), kek)
                
                # Mock an ID since it's AAD. But FaceEmbedding hasn't been created yet.
                # To bind AAD to row ID properly, we need the UUID before inserting.
                import uuid
                fe_id = uuid.uuid4()
                
                embedding_bytes = json.dumps(embedding).encode('utf-8')
                ciphertext, nonce = encrypt_embedding(
                    embedding_bytes, dek, str(guest_id), str(event.id), str(fe_id), model_version
                )
            else:
                import uuid
                fe_id = uuid.uuid4()
        else:
            import uuid
            fe_id = uuid.uuid4()
            
        record = FaceEmbedding(
            id=fe_id,
            guest_id=guest_id,
            model_version=model_version,
            embedding_dim=embedding_dim,
            quality_score=quality_score,
            embedding_enc=ciphertext,
            enc_nonce=nonce,
            enc_key_id="local" if ciphertext else None,
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
        guest.embedding_status = status # type: ignore
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

