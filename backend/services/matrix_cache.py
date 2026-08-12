import json
import logging
import redis
import numpy as np
from typing import Tuple, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.config import settings

logger = logging.getLogger(__name__)


class MatrixCache:
    """Caches reference embedding matrix in Redis with a derived fingerprint."""

    def __init__(self, db: Session):
        self.db = db
        try:
            self.redis = redis.Redis.from_url(getattr(settings, "REDIS_URL", "redis://localhost:6379/0"))
        except Exception:
            self.redis = None

    def get_reference_matrix(self, event_id: str) -> Tuple[np.ndarray, List[str]]:
        """
        Loads reference embeddings for event guests.
        Returns (R_matrix: [N_refs, 512] float32, guest_ids: list of str of length N_refs).
        """
        # Calculate fingerprint based on count, max(id), max(updated_at)
        fp_query = text("""
            SELECT COUNT(fe.id) as cnt,
                   COALESCE(MAX(fe.id::text), '') as max_id,
                   COALESCE(MAX(fe.updated_at::text), '') as max_updated
            FROM face_embeddings fe
            JOIN guests g ON fe.guest_id = g.id
            WHERE g.event_id = :event_id
        """)
        fp_row = self.db.execute(fp_query, {"event_id": event_id}).fetchone()
        if not fp_row or fp_row.cnt == 0:
            return np.empty((0, 512), dtype=np.float32), []

        fingerprint = f"{fp_row.cnt}_{fp_row.max_id}_{fp_row.max_updated}"
        cache_key = f"event:{event_id}:refmatrix:{fingerprint}"

        # Attempt to retrieve from Redis cache
        if self.redis:
            try:
                cached_data = self.redis.get(cache_key)
                if cached_data:
                    data = json.loads(cached_data)
                    refs = np.array(data["references"], dtype=np.float32)
                    guest_ids = data["guest_ids"]
                    if refs.shape[1] == 512 and len(guest_ids) == refs.shape[0]:
                        return refs, guest_ids
            except Exception as e:
                logger.warning(f"Redis cache read error: {e}")

        # Load from Postgres
        load_query = text("""
            SELECT fe.guest_id::text as guest_id, fe.embedding
            FROM face_embeddings fe
            JOIN guests g ON fe.guest_id = g.id
            WHERE g.event_id = :event_id
        """)
        rows = self.db.execute(load_query, {"event_id": event_id}).fetchall()

        ref_vectors = []
        guest_ids = []

        for row in rows:
            raw_emb = row.embedding
            if isinstance(raw_emb, str):
                # Parse string vector '[0.1, 0.2, ...]'
                vec = np.array(json.loads(raw_emb), dtype=np.float32)
            elif isinstance(raw_emb, (list, tuple)):
                vec = np.array(raw_emb, dtype=np.float32)
            else:
                vec = np.array(raw_emb, dtype=np.float32)

            if vec.shape[0] != 512:
                continue

            # Load safety assertions
            assert np.all(np.isfinite(vec)), f"Non-finite element found in reference embedding for guest {row.guest_id}"
            norm = np.linalg.norm(vec)
            assert abs(norm - 1.0) <= 1e-2, f"Unnormalized reference embedding vector for guest {row.guest_id} (norm={norm})"

            ref_vectors.append(vec)
            guest_ids.append(row.guest_id)

        if not ref_vectors:
            return np.empty((0, 512), dtype=np.float32), []

        R_matrix = np.vstack(ref_vectors).astype(np.float32)

        # Store in Redis with 1 hour TTL
        if self.redis:
            try:
                payload = json.dumps({
                    "references": R_matrix.tolist(),
                    "guest_ids": guest_ids
                })
                self.redis.setex(cache_key, 3600, payload)
            except Exception as e:
                logger.warning(f"Redis cache write error: {e}")

        return R_matrix, guest_ids
