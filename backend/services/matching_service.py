import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, insert, update

from models.event import Event
from models.photo_face import PhotoFace
from models.match import Match
from models.match_run import MatchRun

logger = logging.getLogger(__name__)

DEFAULT_AUTO_CONFIRM = 0.42
DEFAULT_REVIEW_FLOOR = 0.32
DEFAULT_MARGIN = 0.05


class MatchingService:
    def __init__(self, db: Session):
        self.db = db

    def _get_thresholds(self, event_id: str) -> Tuple[float, float, float]:
        event = self.db.query(Event).filter(Event.id == uuid.UUID(event_id)).first()
        auto_confirm = getattr(event, "match_threshold", None) or float(os.getenv("MATCH_THRESHOLD", DEFAULT_AUTO_CONFIRM))
        review_floor = getattr(event, "review_floor", None) or float(os.getenv("MATCH_REVIEW_FLOOR", DEFAULT_REVIEW_FLOOR))
        margin = getattr(event, "match_margin", None) or float(os.getenv("MATCH_MARGIN", DEFAULT_MARGIN))
        return auto_confirm, review_floor, margin

    def match_pending_faces(self, event_id_str: str, force: bool = False, trigger: str = "photo_ingest") -> Dict[str, Any]:
        """
        Runs Postgres pgvector-based matching for photo faces against guest embeddings.
        """
        event_id = uuid.UUID(event_id_str)
        auto_confirm_thresh, review_floor_thresh, margin_thresh = self._get_thresholds(event_id_str)

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
            # Query the database to find the top 2 matching guests for each matchable face
            # using pgvector's cosine distance operator `<=>`.
            # Note: 1 - cosine_distance = cosine_similarity
            
            faces_cond = "" if force else "AND pf.matched_at IS NULL"
            
            query = text(f"""
                WITH guest_embeddings AS (
                    SELECT fe.guest_id, fe.embedding
                    FROM face_embeddings fe
                    JOIN guests g ON g.id = fe.guest_id
                    WHERE g.event_id = :event_id
                ),
                top_k_matches AS (
                    SELECT 
                        pf.id AS pf_id,
                        pf.photo_id,
                        ge.guest_id,
                        (1 - (pf.embedding <=> ge.embedding)) AS similarity
                    FROM photo_faces pf
                    CROSS JOIN LATERAL (
                        SELECT guest_id, embedding
                        FROM guest_embeddings
                        ORDER BY pf.embedding <=> guest_embeddings.embedding ASC
                        LIMIT 10
                    ) ge
                    WHERE pf.event_id = :event_id AND pf.is_matchable = true {faces_cond}
                ),
                ranked_guests AS (
                    SELECT 
                        pf_id,
                        photo_id,
                        guest_id,
                        MAX(similarity) as similarity
                    FROM top_k_matches
                    GROUP BY pf_id, photo_id, guest_id
                ),
                face_matches AS (
                    SELECT
                        pf_id,
                        photo_id,
                        guest_id,
                        similarity,
                        ROW_NUMBER() OVER(PARTITION BY pf_id ORDER BY similarity DESC) as rank
                    FROM ranked_guests
                )
                SELECT 
                    m1.pf_id, 
                    m1.photo_id, 
                    m1.guest_id AS top1_guest_id, 
                    m1.similarity AS top1_score,
                    m2.guest_id AS top2_guest_id, 
                    m2.similarity AS top2_score
                FROM face_matches m1
                LEFT JOIN face_matches m2 ON m1.pf_id = m2.pf_id AND m2.rank = 2
                WHERE m1.rank = 1 AND m1.similarity >= :review_floor;
            """)
            
            rows = self.db.execute(query, {
                "event_id": event_id_str,
                "review_floor": review_floor_thresh
            }).fetchall()

            if not rows:
                match_run.status = "completed"
                match_run.finished_at = datetime.now(timezone.utc)
                self.db.commit()
                return {"status": "completed", "faces_scanned": 0, "auto_confirmed": 0, "review": 0, "rejected": 0}

            # Pre-fetch existing matches to handle overrides & manual protections
            existing_rows = self.db.execute(
                text("SELECT id::text as id, photo_face_id::text as pf_id, status, reviewed_at FROM matches WHERE event_id = :event_id"),
                {"event_id": event_id_str}
            ).fetchall()
            existing_matches_map = {
                uuid.UUID(r.pf_id): {"id": uuid.UUID(r.id), "status": r.status, "reviewed_at": r.reviewed_at}
                for r in existing_rows
            }

            now_ts = datetime.now(timezone.utc)
            auto_confirmed_cnt = 0
            review_cnt = 0
            rejected_cnt = 0
            protected_cnt = 0
            scanned_faces = len(rows)

            new_match_mappings = []
            update_match_mappings = []
            chunk_processed_uuids = []

            for r in rows:
                pf_uuid = r.pf_id if isinstance(r.pf_id, uuid.UUID) else uuid.UUID(str(r.pf_id))
                p_uuid = r.photo_id if isinstance(r.photo_id, uuid.UUID) else uuid.UUID(str(r.photo_id))
                top1_guest_id = r.top1_guest_id if isinstance(r.top1_guest_id, uuid.UUID) else uuid.UUID(str(r.top1_guest_id))
                top1_score = float(r.top1_score)
                if r.top2_guest_id:
                    top2_guest_id = r.top2_guest_id if isinstance(r.top2_guest_id, uuid.UUID) else uuid.UUID(str(r.top2_guest_id))
                else:
                    top2_guest_id = None
                top2_score = float(r.top2_score) if r.top2_score else 0.0

                margin = top1_score - top2_score

                review_reason = None
                if top1_score >= auto_confirm_thresh and margin >= margin_thresh:
                    decision = "auto_confirmed"
                else:
                    decision = "review"
                    if margin < margin_thresh:
                        review_reason = "below_margin"
                    else:
                        review_reason = "in_review_band"

                existing = existing_matches_map.get(pf_uuid)
                if existing and not force:
                    if existing["reviewed_at"] is not None or existing["status"] in ("manually_added", "rejected_by_organizer"):
                        protected_cnt += 1
                        continue

                top_candidates = [{"guest_id": str(top1_guest_id), "score": round(top1_score, 4), "rank": 1}]
                if top2_guest_id:
                    top_candidates.append({"guest_id": str(top2_guest_id), "score": round(top2_score, 4), "rank": 2})

                if existing:
                    update_match_mappings.append({
                        "id": existing["id"],
                        "event_id": event_id,
                        "guest_id": top1_guest_id,
                        "photo_id": p_uuid,
                        "photo_face_id": pf_uuid,
                        "match_run_id": match_run.id,
                        "similarity": round(top1_score, 4),
                        "threshold_used": auto_confirm_thresh,
                        "decision": decision,
                        "status": "active" if existing["status"] != "rejected_by_organizer" else existing["status"],
                        "second_guest_id": top2_guest_id,
                        "second_similarity": round(top2_score, 4) if top2_guest_id else None,
                        "margin": round(margin, 4),
                        "review_reason": review_reason,
                        "top_candidates": top_candidates,
                        "model_version": "buffalo_l",
                        "matched_at": now_ts,
                        "updated_at": now_ts,
                    })
                else:
                    new_match_id = uuid.uuid4()
                    insert_status = "pending_review" if decision == "review" else "active"
                    new_match_mappings.append({
                        "id": new_match_id,
                        "event_id": event_id,
                        "guest_id": top1_guest_id,
                        "photo_id": p_uuid,
                        "photo_face_id": pf_uuid,
                        "match_run_id": match_run.id,
                        "similarity": round(top1_score, 4),
                        "threshold_used": auto_confirm_thresh,
                        "decision": decision,
                        "status": insert_status,
                        "second_guest_id": top2_guest_id,
                        "second_similarity": round(top2_score, 4) if top2_guest_id else None,
                        "margin": round(margin, 4),
                        "review_reason": review_reason,
                        "top_candidates": top_candidates,
                        "model_version": "buffalo_l",
                        "matched_at": now_ts,
                        "created_at": now_ts,
                        "updated_at": now_ts,
                    })
                    existing_matches_map[pf_uuid] = {"id": new_match_id, "status": insert_status, "reviewed_at": None}

                chunk_processed_uuids.append(pf_uuid)
                
                if decision == "auto_confirmed":
                    auto_confirmed_cnt += 1
                else:
                    review_cnt += 1

            if new_match_mappings:
                self.db.execute(insert(Match), new_match_mappings)
            if update_match_mappings:
                self.db.execute(update(Match), update_match_mappings)

            if chunk_processed_uuids:
                self.db.query(PhotoFace).filter(PhotoFace.id.in_(chunk_processed_uuids)).update(
                    {PhotoFace.matched_at: now_ts},
                    synchronize_session=False
                )

            match_run.faces_scanned = scanned_faces
            match_run.auto_confirmed = auto_confirmed_cnt
            match_run.sent_to_review = review_cnt
            match_run.rejected = rejected_cnt
            match_run.protected_rows = protected_cnt
            match_run.status = "completed"
            match_run.finished_at = now_ts
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
        Fast pgvector-based single-guest matching against existing photo faces.
        """
        event_id = uuid.UUID(event_id_str)
        guest_id = uuid.UUID(guest_id_str)
        auto_confirm_thresh, review_floor_thresh, margin_thresh = self._get_thresholds(event_id_str)

        query = text("""
            WITH guest_refs AS (
                SELECT embedding FROM face_embeddings WHERE guest_id = :guest_id
            ),
            face_matches AS (
                SELECT 
                    pf.id AS pf_id,
                    pf.photo_id,
                    (1 - (pf.embedding <=> gr.embedding)) AS similarity,
                    ROW_NUMBER() OVER(PARTITION BY pf.id ORDER BY (pf.embedding <=> gr.embedding) ASC) as rank
                FROM photo_faces pf
                CROSS JOIN LATERAL (
                    SELECT embedding FROM guest_refs
                    ORDER BY pf.embedding <=> guest_refs.embedding ASC
                    LIMIT 1
                ) gr
                WHERE pf.event_id = :event_id AND pf.is_matchable = true
            )
            SELECT pf_id, photo_id, similarity
            FROM face_matches
            WHERE rank = 1 AND similarity >= :review_floor;
        """)

        rows = self.db.execute(query, {
            "event_id": event_id_str,
            "guest_id": guest_id_str,
            "review_floor": review_floor_thresh
        }).fetchall()

        if not rows:
            return {"status": "completed", "matches_evaluated": 0, "updated_matches": 0}

        updated_matches = 0
        for r in rows:
            score = float(r.similarity)
            pf_uuid = r.pf_id if isinstance(r.pf_id, uuid.UUID) else uuid.UUID(str(r.pf_id))
            p_uuid = r.photo_id if isinstance(r.photo_id, uuid.UUID) else uuid.UUID(str(r.photo_id))
            
            existing_match = self.db.query(Match).filter(Match.photo_face_id == pf_uuid).first()

            if existing_match:
                if existing_match.reviewed_at is not None or existing_match.status in ("manually_added", "rejected_by_organizer"):
                    continue
                if existing_match.similarity >= score:
                    continue

            decision = "auto_confirmed" if score >= auto_confirm_thresh else "review"
            insert_status = "pending_review" if decision == "review" else "active"

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
                    status=insert_status,
                    model_version="buffalo_l",
                )
                self.db.add(match_record)
            else:
                existing_match.guest_id = guest_id
                existing_match.similarity = round(score, 4)
                existing_match.decision = decision

            updated_matches += 1

        self.db.commit()
        return {"status": "completed", "matches_evaluated": len(rows), "updated_matches": updated_matches}
