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
        content_hash: str | None = None,
        model_version: str = "ArcFace",
        embedding_dim: int = 512,
    ) -> FaceEmbedding:
        import json
        import uuid
        import logging
        import typing
        from services.crypto.envelope import get_or_unwrap_kek, get_or_unwrap_dek, encrypt_embedding

        _log = logging.getLogger(__name__)

        guest = self.db.query(Guest).filter(Guest.id == guest_id).first()
        if not guest:
            raise ValueError(f"Guest {guest_id} not found — cannot create embedding.")

        ciphertext: bytes | None = None
        nonce: bytes | None = None
        fe_id = uuid.uuid4()

        if guest.wrapped_dek:
            from models.event import Event
            event = self.db.query(Event).filter(Event.id == guest.event_id).first()
            if event and event.wrapped_kek:
                kek_blob = typing.cast(bytes, event.wrapped_kek)
                kek_nonce, kek_wrapped = kek_blob[:12], kek_blob[12:]
                kek = get_or_unwrap_kek(str(event.id), kek_wrapped, kek_nonce)

                dek_blob = typing.cast(bytes, guest.wrapped_dek)
                dek_nonce, dek_wrapped = dek_blob[:12], dek_blob[12:]
                dek = get_or_unwrap_dek(str(guest_id), dek_wrapped, dek_nonce, kek)

                embedding_bytes = json.dumps(embedding).encode("utf-8")
                ciphertext, nonce = encrypt_embedding(
                    embedding_bytes, dek, str(guest_id), str(event.id), str(fe_id), model_version
                )
            else:
                _log.error(
                    "Guest %s has wrapped_dek but event %s has no wrapped_kek — "
                    "refusing to store plaintext embedding.",
                    guest_id, guest.event_id,
                )
                raise RuntimeError(
                    f"Encryption key unavailable for event {guest.event_id}. "
                    "Embedding not stored."
                )
        else:
            _log.error(
                "Guest %s has no wrapped_dek — refusing to store plaintext embedding.",
                guest_id,
            )
            raise RuntimeError(
                f"Guest {guest_id} has no data-encryption key. "
                "Ensure key provisioning ran before embedding extraction."
            )

        # Never write the plaintext `embedding` column — encryption is mandatory.
        record = FaceEmbedding(
            id=fe_id,
            guest_id=guest_id,
            model_version=model_version,
            embedding_dim=embedding_dim,
            quality_score=quality_score,
            content_hash=content_hash,
            embedding=None,        # plaintext column intentionally left NULL
            embedding_enc=ciphertext,
            enc_nonce=nonce,
            enc_key_id="local",
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

    def delete_by_guest(self, guest_id: UUID) -> int:
        """Hard-delete all face_embeddings rows for the given guest.

        Returns the number of rows deleted.
        Used by the biometrics purge endpoint and the sweep_expired_guests task.
        """
        deleted = (
            self.db.query(FaceEmbedding)
            .filter(FaceEmbedding.guest_id == guest_id)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return deleted

