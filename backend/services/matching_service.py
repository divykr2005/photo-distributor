import os
import uuid
import json
import logging
import typing
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, insert, update

import numpy as np
import faiss

from models.event import Event
from models.photo_face import PhotoFace
from models.match import Match
from models.match_run import MatchRun
from models.face_embedding import FaceEmbedding
from models.guest import Guest
from services.crypto.envelope import get_or_unwrap_kek, get_or_unwrap_dek, decrypt_embedding

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

    def _get_event_kek(self, event_id_str: str) -> bytes:
        event = self.db.query(Event).filter(Event.id == uuid.UUID(event_id_str)).first()
        if not event or not event.wrapped_kek:
            raise RuntimeError(f"Event {event_id_str} missing or missing wrapped_kek")
        kek_blob = typing.cast(bytes, event.wrapped_kek)
        return get_or_unwrap_kek(event_id_str, kek_blob[12:], kek_blob[:12])

    def _decrypt_face(self, enc_blob: bytes, nonce: bytes, guest_id: str, event_id: str, face_id: str, key: bytes, model_version: str = "buffalo_l") -> list[float]:
        raw = decrypt_embedding(enc_blob, nonce, key, guest_id, event_id, face_id, model_version)
        return json.loads(raw.decode("utf-8"))

    def match_pending_faces(self, event_id_str: str, force: bool = False, trigger: str = "photo_ingest") -> Dict[str, Any]:
        """
        Runs FAISS in-memory matching for photo faces against guest embeddings.
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
            # 1. Fetch Event KEK
            kek = self._get_event_kek(event_id_str)

            # 2. Fetch Guests and Decrypt Embeddings
            guest_records = self.db.query(FaceEmbedding, Guest.wrapped_dek).join(
                Guest, Guest.id == FaceEmbedding.guest_id
            ).filter(
                Guest.event_id == event_id,
                Guest.wrapped_dek.is_not(None)
            ).all()

            guest_ids = []
            guest_vectors = []

            for fe, wrapped_dek in guest_records:
                if not fe.embedding_enc or not fe.enc_nonce:
                    continue
                dek_blob = typing.cast(bytes, wrapped_dek)
                dek = get_or_unwrap_dek(str(fe.guest_id), dek_blob[12:], dek_blob[:12], kek)
                vec = self._decrypt_face(
                    fe.embedding_enc, fe.enc_nonce,
                    str(fe.guest_id), event_id_str, str(fe.id), dek, fe.model_version
                )
                guest_vectors.append(vec)
                guest_ids.append(fe.guest_id)

            if not guest_vectors:
                match_run.status = "completed"
                match_run.finished_at = datetime.now(timezone.utc)
                self.db.commit()
                return {"status": "completed", "faces_scanned": 0, "auto_confirmed": 0, "review": 0, "rejected": 0}

            # 3. Build FAISS Index
            dim = len(guest_vectors[0])
            np_guest_vectors = np.array(guest_vectors, dtype=np.float32)
            faiss.normalize_L2(np_guest_vectors)
            index = faiss.IndexFlatIP(dim)
            index.add(np_guest_vectors)

            # 4. Fetch Photo Faces
            pf_query = self.db.query(PhotoFace).filter(
                PhotoFace.event_id == event_id,
                PhotoFace.is_matchable == True
            )
            if not force:
                pf_query = pf_query.filter(PhotoFace.matched_at.is_(None))

            photo_faces = pf_query.all()

            if not photo_faces:
                match_run.status = "completed"
                match_run.finished_at = datetime.now(timezone.utc)
                self.db.commit()
                return {"status": "completed", "faces_scanned": 0, "auto_confirmed": 0, "review": 0, "rejected": 0}

            pf_vectors = []
            pf_objects = []
            for pf in photo_faces:
                if not pf.embedding_enc or not pf.enc_nonce:
                    continue
                vec = self._decrypt_face(
                    pf.embedding_enc, pf.enc_nonce,
                    str(pf.id), event_id_str, str(pf.id), kek, pf.model_version
                )
                pf_vectors.append(vec)
                pf_objects.append(pf)

            if not pf_vectors:
                match_run.status = "completed"
                match_run.finished_at = datetime.now(timezone.utc)
                self.db.commit()
                return {"status": "completed", "faces_scanned": len(photo_faces), "auto_confirmed": 0, "review": 0, "rejected": 0}

            # 5. Run FAISS Search
            np_pf_vectors = np.array(pf_vectors, dtype=np.float32)
            faiss.normalize_L2(np_pf_vectors)

            # Find top 2 matches for each face
            k = min(2, len(guest_ids))
            similarities, indices = index.search(np_pf_vectors, k)

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
            scanned_faces = len(pf_objects)

            new_match_mappings = []
            update_match_mappings = []
            chunk_processed_uuids = []

            for i, pf in enumerate(pf_objects):
                pf_uuid = pf.id
                p_uuid = pf.photo_id

                top1_score = float(similarities[i][0])
                top1_guest_id = guest_ids[indices[i][0]]

                if top1_score < review_floor_thresh:
                    chunk_processed_uuids.append(pf_uuid)
                    continue

                if k > 1:
                    top2_score = float(similarities[i][1])
                    top2_guest_id = guest_ids[indices[i][1]]
                else:
                    top2_score = 0.0
                    top2_guest_id = None

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
                        "model_version": pf.model_version,
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
                        "model_version": pf.model_version,
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

            # Explicitly delete index and arrays from memory
            del index
            del np_guest_vectors
            del np_pf_vectors

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
        Fast FAISS in-memory single-guest matching against existing photo faces.
        """
        event_id = uuid.UUID(event_id_str)
        guest_id = uuid.UUID(guest_id_str)
        auto_confirm_thresh, review_floor_thresh, margin_thresh = self._get_thresholds(event_id_str)

        # 1. Fetch Event KEK
        kek = self._get_event_kek(event_id_str)

        # 2. Fetch Guest and Decrypt
        guest_record = self.db.query(FaceEmbedding, Guest.wrapped_dek).join(
            Guest, Guest.id == FaceEmbedding.guest_id
        ).filter(
            FaceEmbedding.guest_id == guest_id,
            Guest.wrapped_dek.is_not(None)
        ).first()

        if not guest_record:
            return {"status": "completed", "matches_evaluated": 0, "updated_matches": 0}

        fe, wrapped_dek = guest_record
        if not fe.embedding_enc or not fe.enc_nonce:
            return {"status": "completed", "matches_evaluated": 0, "updated_matches": 0}

        dek_blob = typing.cast(bytes, wrapped_dek)
        dek = get_or_unwrap_dek(str(fe.guest_id), dek_blob[12:], dek_blob[:12], kek)
        guest_vec = self._decrypt_face(
            fe.embedding_enc, fe.enc_nonce,
            str(fe.guest_id), event_id_str, str(fe.id), dek, fe.model_version
        )

        # Build index for the single guest
        np_guest_vectors = np.array([guest_vec], dtype=np.float32)
        faiss.normalize_L2(np_guest_vectors)
        index = faiss.IndexFlatIP(len(guest_vec))
        index.add(np_guest_vectors)

        # 3. Fetch all photo faces
        pf_query = self.db.query(PhotoFace).filter(
            PhotoFace.event_id == event_id,
            PhotoFace.is_matchable == True
        )
        photo_faces = pf_query.all()
        if not photo_faces:
            return {"status": "completed", "matches_evaluated": 0, "updated_matches": 0}

        pf_vectors = []
        pf_objects = []
        for pf in photo_faces:
            if not pf.embedding_enc or not pf.enc_nonce:
                continue
            vec = self._decrypt_face(
                pf.embedding_enc, pf.enc_nonce,
                str(pf.id), event_id_str, str(pf.id), kek, pf.model_version
            )
            pf_vectors.append(vec)
            pf_objects.append(pf)

        if not pf_vectors:
            return {"status": "completed", "matches_evaluated": 0, "updated_matches": 0}

        np_pf_vectors = np.array(pf_vectors, dtype=np.float32)
        faiss.normalize_L2(np_pf_vectors)

        # Search the guest index with photo vectors. Wait, doing index.search(np_pf_vectors, 1)
        # gives us the similarity of each photo to the single guest.
        similarities, indices = index.search(np_pf_vectors, 1)

        updated_matches = 0
        for i, pf in enumerate(pf_objects):
            score = float(similarities[i][0])
            if score < review_floor_thresh:
                continue

            pf_uuid = pf.id
            p_uuid = pf.photo_id

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
                    model_version=pf.model_version,
                )
                self.db.add(match_record)
            else:
                existing_match.guest_id = guest_id
                existing_match.similarity = round(score, 4)
                existing_match.decision = decision

            updated_matches += 1

        self.db.commit()

        del index
        del np_guest_vectors
        del np_pf_vectors

        return {"status": "completed", "matches_evaluated": len(pf_objects), "updated_matches": updated_matches}
