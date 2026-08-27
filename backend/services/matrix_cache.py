import json
import logging
import redis
import numpy as np
from typing import Tuple, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import functools
from cachetools import LRUCache

from core.config import settings
from services.crypto.envelope import get_or_unwrap_kek, get_or_unwrap_dek, decrypt_embedding

logger = logging.getLogger(__name__)

# LRU Cache for process memory: (event_id, fingerprint) -> (R_matrix, guest_ids)
# Size 8 events to bound memory usage
_reference_matrix_cache = LRUCache(maxsize=8)

class MatrixCache:
    """Caches reference embedding matrix in process memory, tracks invalidation via Redis fingerprint."""

    def __init__(self, db: Session):
        self.db = db
        try:
            self.redis = redis.Redis.from_url(getattr(settings, "REDIS_URL", "redis://localhost:6379/0"))
        except Exception:
            self.redis = None

    def get_reference_matrix(self, event_id: str) -> Tuple[np.ndarray, List[str]]:
        """
        Loads and decrypts reference embeddings for event guests.
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
        cache_key = f"event:{event_id}:refmatrix_fp"
        
        # Check if the fingerprint matches what is in Redis
        # If it doesn't match, or not in Redis, we re-build the matrix and update Redis fingerprint
        if self.redis:
            try:
                cached_fp = self.redis.get(cache_key)
                if cached_fp and cached_fp.decode('utf-8') == fingerprint:
                    # Fingerprint matches, check local memory cache
                    if (event_id, fingerprint) in _reference_matrix_cache:
                        return _reference_matrix_cache[(event_id, fingerprint)]
            except Exception as e:
                logger.warning(f"Redis cache read error: {e}")

        # Load from Postgres
        # We need wrapped KEK from event, wrapped DEK from guest, and embedding_enc from face_embedding
        load_query = text("""
            SELECT fe.id as fe_id, fe.guest_id::text as guest_id, 
                   fe.embedding_enc, fe.enc_nonce, fe.model_version,
                   g.wrapped_dek, e.wrapped_kek
            FROM face_embeddings fe
            JOIN guests g ON fe.guest_id = g.id
            JOIN events e ON g.event_id = e.id
            WHERE g.event_id = :event_id
        """)
        rows = self.db.execute(load_query, {"event_id": event_id}).fetchall()

        ref_vectors = []
        guest_ids = []

        for row in rows:
            guest_id = row.guest_id
            
            # Phase 2 logic: if encrypted data exists, use it. Else fallback to plaintext.
            if row.embedding_enc and row.enc_nonce and row.wrapped_dek and row.wrapped_kek:
                # Decrypt
                kek_blob = row.wrapped_kek
                kek_nonce, kek_wrapped = kek_blob[:12], kek_blob[12:]
                kek = get_or_unwrap_kek(event_id, kek_wrapped, kek_nonce)
                
                dek_blob = row.wrapped_dek
                dek_nonce, dek_wrapped = dek_blob[:12], dek_blob[12:]
                dek = get_or_unwrap_dek(guest_id, dek_wrapped, dek_nonce, kek)
                
                pt_bytes = decrypt_embedding(
                    ciphertext=row.embedding_enc,
                    nonce=row.enc_nonce,
                    dek=dek,
                    guest_id=guest_id,
                    event_id=event_id,
                    face_embedding_id=str(row.fe_id),
                    model_version=row.model_version
                )
                raw_emb_str = pt_bytes.decode('utf-8')
            else:
                # Fallback to plaintext if not encrypted yet
                raw_emb_str = None

            if not raw_emb_str:
                continue

            try:
                vec = np.array(json.loads(raw_emb_str), dtype=np.float32)
            except Exception:
                # In case it's a tuple or list already evaluated by SQLAlchemy
                vec = np.array(raw_emb_str, dtype=np.float32)

            if vec.shape[0] != 512:
                continue

            # Load safety assertions run AFTER decryption
            assert np.all(np.isfinite(vec)), f"Non-finite element found in reference embedding for guest {guest_id}"
            norm = np.linalg.norm(vec)
            assert abs(norm - 1.0) <= 1e-2, f"Unnormalized reference embedding vector for guest {guest_id} (norm={norm})"

            ref_vectors.append(vec)
            guest_ids.append(guest_id)

        if not ref_vectors:
            return np.empty((0, 512), dtype=np.float32), []

        R_matrix = np.vstack(ref_vectors).astype(np.float32)

        # Store in local memory LRU
        _reference_matrix_cache[(event_id, fingerprint)] = (R_matrix, guest_ids)

        # Update Redis fingerprint with 1 hour TTL
        if self.redis:
            try:
                self.redis.setex(cache_key, 3600, fingerprint)
            except Exception as e:
                logger.warning(f"Redis cache write error: {e}")

        return R_matrix, guest_ids
