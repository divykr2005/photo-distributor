import hashlib
import json
import logging
import os
import secrets
import tempfile
import time
import uuid
from typing import List, Tuple, Dict, Any, Optional
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
            from core.config import get_redis_url
            self.redis = redis.Redis.from_url(get_redis_url())
        except Exception as e:
            logger.warning(f"Redis not available for selfie search service: {e}")
            self.redis = None



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

        # Use pgvector <=> (cosine distance) natively in DB
        # The cosine similarity is (1 - cosine_distance)
        # We group by photo_id and find the maximum similarity for the faces in that photo
        selfie_vec_str = json.dumps(embedding_list)

        query = text("""
            SELECT pf.photo_id::text AS photo_id, MAX(1 - (pf.embedding <=> :selfie_emb)) AS sim
            FROM photo_faces pf
            JOIN photos p ON pf.photo_id = p.id
            WHERE pf.event_id = :event_id AND pf.is_matchable = true AND p.status != 'failed'
            GROUP BY pf.photo_id
            HAVING MAX(1 - (pf.embedding <=> :selfie_emb)) >= :threshold
            ORDER BY sim DESC
            LIMIT 200
        """)

        rows = self.db.execute(query, {
            "selfie_emb": selfie_vec_str,
            "event_id": event_id_str,
            "threshold": threshold_used
        }).fetchall()

        matched_photo_ids = [row.photo_id for row in rows]
        top_similarity = float(rows[0].sim) if rows else None

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
