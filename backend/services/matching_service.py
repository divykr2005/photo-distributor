import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text, insert, update

from models.event import Event
from models.photo_face import PhotoFace
from models.match import Match
from models.match_run import MatchRun
from models.guest import Guest
from services.matrix_cache import MatrixCache

logger = logging.getLogger(__name__)

DEFAULT_AUTO_CONFIRM = 0.42
DEFAULT_REVIEW_FLOOR = 0.32
DEFAULT_MARGIN = 0.05


class MatchingService:
    def __init__(self, db: Session):
        self.db = db
        self.matrix_cache = MatrixCache(db)

    def _get_thresholds(self, event_id: str) -> Tuple[float, float, float]:
        event = self.db.query(Event).filter(Event.id == uuid.UUID(event_id)).first()
        auto_confirm = getattr(event, "match_threshold", None) or float(os.getenv("MATCH_THRESHOLD", DEFAULT_AUTO_CONFIRM))
        review_floor = getattr(event, "review_floor", None) or float(os.getenv("MATCH_REVIEW_FLOOR", DEFAULT_REVIEW_FLOOR))
        margin = getattr(event, "match_margin", None) or float(os.getenv("MATCH_MARGIN", DEFAULT_MARGIN))
        return auto_confirm, review_floor, margin

    def match_pending_faces(self, event_id_str: str, force: bool = False, trigger: str = "photo_ingest") -> Dict[str, Any]:
        """
        Runs batched NumPy matrix multiplication for matchable photo faces.
        """
        event_id = uuid.UUID(event_id_str)
        auto_confirm_thresh, review_floor_thresh, margin_thresh = self._get_thresholds(event_id_str)

        # Create MatchRun audit record
        match_run = MatchRun(
            id=uuid.uuid4(),
            event_id=event_id,
            trigger=trigger,
            scope="full_event" if force else "new_photos",
            params={
                "auto_confirm": auto_confirm_thresh,
                "review_floor": review_floor_thresh,
                "margin": margin_thresh,
                "force": force,
            },
            status="running",
        )
        self.db.add(match_run)
        self.db.commit()

        try:
            # Load reference matrix R: [N_refs, 512] and guest_ids
            R_matrix, ref_guest_ids = self.matrix_cache.get_reference_matrix(event_id_str)

            if R_matrix.shape[0] == 0:
                match_run.status = "completed"
                match_run.finished_at = datetime.now(timezone.utc)
                self.db.commit()
                return {"status": "completed", "faces_scanned": 0, "guests_scanned": 0}

            # Unique distinct guests count
            unique_guests = list(set(ref_guest_ids))
            match_run.guests_scanned = len(unique_guests)

            # Query matchable faces
            if force:
                face_query = text("""
                    SELECT id::text as face_id, photo_id::text as photo_id, embedding
                    FROM photo_faces
                    WHERE event_id = :event_id AND is_matchable = true
                """)
            else:
                face_query = text("""
                    SELECT id::text as face_id, photo_id::text as photo_id, embedding
                    FROM photo_faces
                    WHERE event_id = :event_id AND is_matchable = true AND matched_at IS NULL
                """)

            rows = self.db.execute(face_query, {"event_id": event_id_str}).fetchall()

            if not rows:
                match_run.status = "completed"
                match_run.finished_at = datetime.now(timezone.utc)
                self.db.commit()
                return {"status": "completed", "faces_scanned": 0}

            # Map reference indices per distinct guest ID
            guest_ref_indices: Dict[str, List[int]] = {}
            for idx, g_id in enumerate(ref_guest_ids):
                guest_ref_indices.setdefault(g_id, []).append(idx)

            distinct_guest_list = list(guest_ref_indices.keys())

            chunk_size = 4096
            scanned_faces = 0
            auto_confirmed_cnt = 0
            review_cnt = 0
            rejected_cnt = 0
            protected_cnt = 0

            # Pre-fetch existing match metadata as lightweight dicts to avoid loading ORM objects
            existing_rows = self.db.execute(
                text("SELECT id::text as id, photo_face_id::text as pf_id, status, reviewed_at FROM matches WHERE event_id = :event_id"),
                {"event_id": event_id_str}
            ).fetchall()

            existing_matches_map = {
                uuid.UUID(r.pf_id): {"id": uuid.UUID(r.id), "status": r.status, "reviewed_at": r.reviewed_at}
                for r in existing_rows
            }

            # Prepare distinct guest indexing for vectorized aggregation
            distinct_guests = list(dict.fromkeys(ref_guest_ids))
            guest_ref_indices = [
                np.array([idx for idx, g_id in enumerate(ref_guest_ids) if g_id == target_g_id], dtype=int)
                for target_g_id in distinct_guests
            ]
            num_guests = len(distinct_guests)

            # Process photo faces in chunks of 4096
            for chunk_start in range(0, len(rows), chunk_size):
                chunk_rows = rows[chunk_start:chunk_start + chunk_size]
                face_ids = []
                photo_ids = []
                face_vectors = []

                for r in chunk_rows:
                    raw_emb = r.embedding
                    if isinstance(raw_emb, str):
                        vec = np.fromstring(raw_emb[1:-1], dtype=np.float32, sep=",")
                    elif isinstance(raw_emb, (list, tuple)):
                        vec = np.array(raw_emb, dtype=np.float32)
                    else:
                        vec = np.array(raw_emb, dtype=np.float32)

                    norm = np.linalg.norm(vec)
                    if norm > 0 and abs(norm - 1.0) > 1e-2:
                        vec = vec / norm

                    face_ids.append(r.face_id)
                    photo_ids.append(r.photo_id)
                    face_vectors.append(vec)

                N_chunk = len(face_ids)
                F_matrix = np.vstack(face_vectors).astype(np.float32)  # [N_chunk, 512]

                # Matrix multiplication F @ R.T  ->  [N_chunk, N_refs]
                sim_matrix = np.matmul(F_matrix, R_matrix.T)

                # Vectorized aggregation: MAX similarity per distinct guest -> [N_chunk, N_guests]
                guest_sims = np.zeros((N_chunk, num_guests), dtype=np.float32)
                for g_idx, indices in enumerate(guest_ref_indices):
                    guest_sims[:, g_idx] = np.max(sim_matrix[:, indices], axis=1)

                # Top 1, Top 2 scores and top-3 ranking per face in chunk
                top1_indices = np.argmax(guest_sims, axis=1)
                top1_scores = guest_sims[np.arange(N_chunk), top1_indices]

                if num_guests > 1:
                    partitioned = np.partition(guest_sims, -2, axis=1)
                    top2_scores = partitioned[:, -2]
                    top3_indices = np.argsort(-guest_sims, axis=1)[:, :3]
                else:
                    top2_scores = np.zeros(N_chunk, dtype=np.float32)
                    top3_indices = np.zeros((N_chunk, 1), dtype=int)

                margins = top1_scores - top2_scores
                chunk_processed_uuids = []
                new_match_mappings = []
                update_match_mappings = []

                now_ts = datetime.now(timezone.utc)

                # Build match mapping dicts for chunk
                for i in range(N_chunk):
                    pf_id_str = face_ids[i]
                    p_id_str = photo_ids[i]
                    pf_uuid = uuid.UUID(pf_id_str)

                    top_1_score = float(top1_scores[i])
                    top_2_score = float(top2_scores[i])
                    margin = float(margins[i])
                    top_1_guest = distinct_guests[top1_indices[i]]

                    top_2_guest = None
                    if num_guests > 1:
                        t3 = top3_indices[i]
                        top_2_guest = distinct_guests[t3[1]] if len(t3) > 1 else None

                    top_candidates = []
                    for rank_idx, g_idx_val in enumerate(top3_indices[i]):
                        top_candidates.append({
                            "guest_id": distinct_guests[g_idx_val],
                            "score": round(float(guest_sims[i, g_idx_val]), 4),
                            "rank": rank_idx + 1
                        })

                    # Decision logic
                    review_reason = None
                    if top_1_score >= auto_confirm_thresh and margin >= margin_thresh:
                        decision = "auto_confirmed"
                    elif top_1_score >= review_floor_thresh:
                        decision = "review"
                        if margin < margin_thresh:
                            review_reason = "below_margin"
                        else:
                            review_reason = "in_review_band"
                    else:
                        decision = "rejected"
                        if margin < margin_thresh:
                            review_reason = "below_margin"

                    # Check for existing match row & manual protection via map lookup
                    existing = existing_matches_map.get(pf_uuid)

                    if existing and not force:
                        if existing["reviewed_at"] is not None or existing["status"] in ("manually_added", "rejected_by_organizer"):
                            protected_cnt += 1
                            continue

                    if existing:
                        update_match_mappings.append({
                            "id": existing["id"],
                            "event_id": event_id,
                            "guest_id": uuid.UUID(top_1_guest),
                            "photo_id": uuid.UUID(p_id_str),
                            "photo_face_id": pf_uuid,
                            "match_run_id": match_run.id,
                            "similarity": round(top_1_score, 4),
                            "threshold_used": auto_confirm_thresh,
                            "decision": decision,
                            "status": "active" if existing["status"] != "rejected_by_organizer" else existing["status"],
                            "second_guest_id": uuid.UUID(top_2_guest) if top_2_guest else None,
                            "second_similarity": round(top_2_score, 4) if top_2_guest else None,
                            "margin": round(margin, 4),
                            "review_reason": review_reason,
                            "top_candidates": top_candidates,
                            "model_version": "buffalo_l",
                            "matched_at": now_ts,
                            "updated_at": now_ts,
                        })
                    else:
                        new_match_id = uuid.uuid4()
                        new_match_mappings.append({
                            "id": new_match_id,
                            "event_id": event_id,
                            "guest_id": uuid.UUID(top_1_guest),
                            "photo_id": uuid.UUID(p_id_str),
                            "photo_face_id": pf_uuid,
                            "match_run_id": match_run.id,
                            "similarity": round(top_1_score, 4),
                            "threshold_used": auto_confirm_thresh,
                            "decision": decision,
                            "status": "active",
                            "second_guest_id": uuid.UUID(top_2_guest) if top_2_guest else None,
                            "second_similarity": round(top_2_score, 4) if top_2_guest else None,
                            "margin": round(margin, 4),
                            "review_reason": review_reason,
                            "top_candidates": top_candidates,
                            "model_version": "buffalo_l",
                            "matched_at": now_ts,
                            "created_at": now_ts,
                            "updated_at": now_ts,
                        })
                        existing_matches_map[pf_uuid] = {"id": new_match_id, "status": "active", "reviewed_at": None}

                    chunk_processed_uuids.append(pf_uuid)
                    scanned_faces += 1

                    if decision == "auto_confirmed":
                        auto_confirmed_cnt += 1
                    elif decision == "review":
                        review_cnt += 1
                    else:
                        rejected_cnt += 1

                # Bulk insert and update via SQLAlchemy Core for maximum throughput
                if new_match_mappings:
                    self.db.execute(insert(Match), new_match_mappings)
                if update_match_mappings:
                    self.db.execute(update(Match), update_match_mappings)

                # Bulk update matched_at on PhotoFaces for this chunk
                if chunk_processed_uuids:
                    self.db.query(PhotoFace).filter(PhotoFace.id.in_(chunk_processed_uuids)).update(
                        {PhotoFace.matched_at: now_ts},
                        synchronize_session=False
                    )

                self.db.commit()

            # Finalize MatchRun
            match_run.faces_scanned = scanned_faces
            match_run.auto_confirmed = auto_confirmed_cnt
            match_run.sent_to_review = review_cnt
            match_run.rejected = rejected_cnt
            match_run.protected_rows = protected_cnt
            match_run.status = "completed"
            match_run.finished_at = datetime.now(timezone.utc)
            self.db.commit()

            return {
                "status": "completed",
                "match_run_id": str(match_run.id),
                "faces_scanned": scanned_faces,
                "auto_confirmed": auto_confirmed_cnt,
                "review": review_cnt,
                "rejected": rejected_cnt,
                "protected_rows": protected_cnt,
            }

        except Exception as e:
            logger.error(f"Matching failed for event {event_id_str}: {e}")
            match_run.status = "failed"
            match_run.error = str(e)
            match_run.finished_at = datetime.now(timezone.utc)
            self.db.commit()
            raise

    def match_guest(self, event_id_str: str, guest_id_str: str) -> Dict[str, Any]:
        """
        Fast single-guest matching: matches a newly registered guest against existing photo faces in <= 1s.
        """
        event_id = uuid.UUID(event_id_str)
        guest_id = uuid.UUID(guest_id_str)
        auto_confirm_thresh, review_floor_thresh, margin_thresh = self._get_thresholds(event_id_str)

        # Load target guest reference embeddings
        ref_query = text("SELECT embedding FROM face_embeddings WHERE guest_id = :guest_id")
        ref_rows = self.db.execute(ref_query, {"guest_id": guest_id_str}).fetchall()
        if not ref_rows:
            return {"status": "completed", "matches_evaluated": 0}

        guest_ref_vecs = []
        for r in ref_rows:
            raw_emb = r.embedding
            if isinstance(raw_emb, str):
                vec = np.array(json.loads(raw_emb), dtype=np.float32)
            else:
                vec = np.array(raw_emb, dtype=np.float32)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            guest_ref_vecs.append(vec)

        R_guest = np.vstack(guest_ref_vecs).astype(np.float32)  # [N_guest_refs, 512]

        # Load all matchable photo faces for this event
        faces_query = text("""
            SELECT id::text as face_id, photo_id::text as photo_id, embedding
            FROM photo_faces
            WHERE event_id = :event_id AND is_matchable = true
        """)
        rows = self.db.execute(faces_query, {"event_id": event_id_str}).fetchall()
        if not rows:
            return {"status": "completed", "matches_evaluated": 0}

        face_ids = []
        photo_ids = []
        face_vecs = []
        for r in rows:
            raw_emb = r.embedding
            if isinstance(raw_emb, str):
                vec = np.array(json.loads(raw_emb), dtype=np.float32)
            else:
                vec = np.array(raw_emb, dtype=np.float32)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            face_ids.append(r.face_id)
            photo_ids.append(r.photo_id)
            face_vecs.append(vec)

        F_matrix = np.vstack(face_vecs).astype(np.float32)  # [N_faces, 512]
        sim_matrix = np.matmul(F_matrix, R_guest.T)  # [N_faces, N_guest_refs]
        max_sims = np.max(sim_matrix, axis=1)        # [N_faces]

        updated_matches = 0
        for i in range(len(face_ids)):
            score = float(max_sims[i])
            if score < review_floor_thresh:
                continue

            pf_uuid = uuid.UUID(face_ids[i])
            p_uuid = uuid.UUID(photo_ids[i])
            existing_match = self.db.query(Match).filter(Match.photo_face_id == pf_uuid).first()

            # If existing match exists and has higher score or is manually protected, do not overwrite
            if existing_match:
                if existing_match.reviewed_at is not None or existing_match.status in ("manually_added", "rejected_by_organizer"):
                    continue
                if existing_match.similarity >= score:
                    continue

            decision = "auto_confirmed" if score >= auto_confirm_thresh else "review"
            
            if not existing_match:
                match_record = Match(
                    id=uuid.uuid4(),
                    event_id=event_id,
                    guest_id=guest_id,
                    photo_id=p_uuid,
                    photo_face_id=pf_uuid,
                    similarity=round(score, 4),
                    threshold_used=auto_confirm_thresh,
                    decision=decision,
                    status="active",
                    model_version="buffalo_l",
                )
                self.db.add(match_record)
            else:
                existing_match.guest_id = guest_id
                existing_match.similarity = round(score, 4)
                existing_match.decision = decision

            updated_matches += 1

        self.db.commit()
        return {"status": "completed", "matches_evaluated": len(face_ids), "updated_matches": updated_matches}
