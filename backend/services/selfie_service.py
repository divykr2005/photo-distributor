import hashlib
import json
import logging
import os
import secrets
import tempfile
import time
import uuid
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.config import settings
from models.event import Event
from models.photo import Photo
from models.photo_face import PhotoFace
from models.selfie_search_log import SelfieSearchLog
from worker.face_processor import FaceProcessor, FaceQualityError

logger = logging.getLogger(__name__)

DEFAULT_SELFIE_THRESHOLD = 0.45


class SelfieSearchService:
    def __init__(self, db: Session):
        self.db = db
        try:
            self.redis = redis.Redis.from_url(getattr(settings, "REDIS_URL", "redis://localhost:6379/0"))
        except Exception as e:
            logger.warning(f"Redis not available for selfie search service: {e}")
            self.redis = None

    def get_event_photo_matrix(self, event_id_str: str) -> Tuple[np.ndarray, List[str], List[str]]:
        """
        Loads photo faces matrix for an event.
        Returns (P_matrix: [N_faces, 512] float32, photo_ids: list of str, face_ids: list of str).
        Cached in Redis with 10 min TTL.
        """
        cache_key = f"event:{event_id_str}:photomatrix"
        if self.redis:
            try:
                cached_data = self.redis.get(cache_key)
                if cached_data:
                    data = json.loads(cached_data)
                    matrix = np.array(data["matrix"], dtype=np.float32)
                    photo_ids = data["photo_ids"]
                    face_ids = data["face_ids"]
                    if matrix.shape[1] == 512 and len(photo_ids) == matrix.shape[0]:
                        return matrix, photo_ids, face_ids
            except Exception as e:
                logger.warning(f"Redis cache read error for photo matrix: {e}")

        # Fetch from PostgreSQL
        query = text("""
            SELECT pf.id::text as face_id, pf.photo_id::text as photo_id, pf.embedding
            FROM photo_faces pf
            JOIN photos p ON pf.photo_id = p.id
            WHERE pf.event_id = :event_id AND pf.is_matchable = true AND p.status != 'failed'
        """)
        rows = self.db.execute(query, {"event_id": event_id_str}).fetchall()

        embeddings = []
        photo_ids = []
        face_ids = []

        for row in rows:
            raw_emb = row.embedding
            if isinstance(raw_emb, str):
                vec = np.array(json.loads(raw_emb), dtype=np.float32)
            elif isinstance(raw_emb, (list, tuple)):
                vec = np.array(raw_emb, dtype=np.float32)
            else:
                vec = np.array(raw_emb, dtype=np.float32)

            if vec.shape[0] != 512:
                continue

            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm

            embeddings.append(vec)
            photo_ids.append(row.photo_id)
            face_ids.append(row.face_id)

        if not embeddings:
            return np.empty((0, 512), dtype=np.float32), [], []

        P_matrix = np.vstack(embeddings).astype(np.float32)

        if self.redis:
            try:
                payload = json.dumps({
                    "matrix": P_matrix.tolist(),
                    "photo_ids": photo_ids,
                    "face_ids": face_ids,
                })
                self.redis.setex(cache_key, 600, payload)  # 10 min TTL
            except Exception as e:
                logger.warning(f"Redis cache write error for photo matrix: {e}")

        return P_matrix, photo_ids, face_ids

    def search_by_selfie(
        self,
        event: Event,
        file_bytes: bytes,
        ip_hash: str,
        user_agent_hash: Optional[str] = None,
    ) -> Tuple[str, List[Photo]]:
        """
        Processes selfie in memory, matches against event photo face embeddings,
        mints a search session, and returns (session_id, matched_photo_rows).
        """
        start_time = time.time()
        event_id_str = str(event.id)

        # Threshold D23: selfie_auto_confirm = auto_confirm + 0.03
        base_threshold = event.match_threshold or 0.42
        threshold_used = event.selfie_threshold if event.selfie_threshold is not None else round(base_threshold + 0.03, 4)

        # Write selfie to temp file for DeepFace/OpenCV processing, deleted immediately after
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        try:
            try:
                processor = FaceProcessor.get_instance()
                embedding_list, quality_score = processor.process_image(temp_path)
            except FaceQualityError as fqe:
                latency_ms = int((time.time() - start_time) * 1000)
                # Log rejection
                log_entry = SelfieSearchLog(
                    event_id=event.id,
                    ip_hash=ip_hash,
                    user_agent_hash=user_agent_hash,
                    faces_detected=0,
                    threshold_used=threshold_used,
                    results_count=0,
                    latency_ms=latency_ms,
                    rejected_reason=str(fqe),
                )
                self.db.add(log_entry)
                self.db.commit()
                raise fqe
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

        # Selfie vector S [1, 512]
        selfie_vec = np.array(embedding_list, dtype=np.float32)
        norm = np.linalg.norm(selfie_vec)
        if norm > 0:
            selfie_vec = selfie_vec / norm

        # Fetch photo faces matrix
        P_matrix, photo_ids, face_ids = self.get_event_photo_matrix(event_id_str)

        if P_matrix.shape[0] == 0:
            session_id = secrets.token_urlsafe(24)
            self._save_session(session_id, [])
            latency_ms = int((time.time() - start_time) * 1000)
            log_entry = SelfieSearchLog(
                event_id=event.id,
                ip_hash=ip_hash,
                user_agent_hash=user_agent_hash,
                faces_detected=1,
                threshold_used=threshold_used,
                results_count=0,
                top_similarity=None,
                session_id=session_id,
                latency_ms=latency_ms,
            )
            self.db.add(log_entry)
            self.db.commit()
            return session_id, []

        # Dot product similarities
        similarities = (P_matrix @ selfie_vec.T).flatten()

        # Group by photo_id -> max similarity
        photo_sim_map: Dict[str, float] = {}
        for idx, p_id in enumerate(photo_ids):
            sim = float(similarities[idx])
            if sim > photo_sim_map.get(p_id, -1.0):
                photo_sim_map[p_id] = sim

        # Filter >= threshold_used
        matched_pairs = [
            (p_id, sim) for p_id, sim in photo_sim_map.items() if sim >= threshold_used
        ]

        # Sort desc by similarity
        matched_pairs.sort(key=lambda x: x[1], reverse=True)

        # Cap top 200 photos (D23)
        matched_pairs = matched_pairs[:200]

        matched_photo_ids = [p_id for p_id, _ in matched_pairs]
        top_similarity = matched_pairs[0][1] if matched_pairs else None

        # Mint session ID (D24)
        session_id = secrets.token_urlsafe(24)
        self._save_session(session_id, matched_photo_ids)

        latency_ms = int((time.time() - start_time) * 1000)

        log_entry = SelfieSearchLog(
            event_id=event.id,
            ip_hash=ip_hash,
            user_agent_hash=user_agent_hash,
            faces_detected=1,
            threshold_used=threshold_used,
            results_count=len(matched_photo_ids),
            top_similarity=top_similarity,
            session_id=session_id,
            latency_ms=latency_ms,
        )
        self.db.add(log_entry)
        self.db.commit()

        if not matched_photo_ids:
            return session_id, []

        # Retrieve photo objects preserving order
        photos_by_id = {
            str(p.id): p
            for p in self.db.query(Photo).filter(Photo.id.in_([uuid.UUID(pid) for pid in matched_photo_ids])).all()
        }
        ordered_photos = [photos_by_id[pid] for pid in matched_photo_ids if pid in photos_by_id]

        return session_id, ordered_photos

    def _save_session(self, session_id: str, photo_ids: List[str]) -> None:
        """Stores allowed photo IDs in Redis session key with 15 min TTL (D24)."""
        key = f"selfie_session:{session_id}"
        if self.redis:
            try:
                self.redis.setex(key, 900, json.dumps(photo_ids))  # 15 min TTL
            except Exception as e:
                logger.warning(f"Failed to save selfie session in Redis: {e}")

    def validate_session_photo(self, session_id: str, photo_id_str: str) -> bool:
        """Validates if a photo_id is authorized by the selfie search session."""
        key = f"selfie_session:{session_id}"
        if not self.redis:
            return False
        try:
            raw = self.redis.get(key)
            if not raw:
                return False
            allowed_photo_ids = json.loads(raw)
            return photo_id_str in allowed_photo_ids
        except Exception as e:
            logger.warning(f"Error validating selfie search session: {e}")
            return False
