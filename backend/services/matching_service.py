"""
Matching service: orchestrates face detection in event photos and cosine
similarity search against registered guest embeddings.
"""
import logging

from sqlalchemy.orm import Session

from core.config import settings
from models.event_photo import EventPhoto
from repositories.event_photo_repository import EventPhotoRepository
from repositories.face_embedding_repository import FaceEmbeddingRepository
from repositories.photo_match_repository import PhotoMatchRepository
from worker.face_processor import FaceProcessor

logger = logging.getLogger(__name__)


class MatchingService:
    def __init__(self, db: Session):
        self.db = db
        self.photo_repo = EventPhotoRepository(db)
        self.emb_repo = FaceEmbeddingRepository(db)
        self.match_repo = PhotoMatchRepository(db)
        self.processor = FaceProcessor.get_instance()

    def process_photo(self, photo_id: str) -> dict:
        """
        Full pipeline for one event photo:
        1. Detect all faces in the photo
        2. Extract 512-dim embedding for each face
        3. Cosine-search against registered guest embeddings
        4. Store matches in photo_matches table

        Returns a summary dict with face count and match count.
        """
        photo = self.photo_repo.get_by_id(photo_id)
        if not photo:
            logger.error(f"EventPhoto {photo_id} not found")
            return {"error": "photo_not_found"}

        # Mark as processing
        self.photo_repo.update_status(photo, "processing")

        try:
            face_embeddings = self._detect_faces(photo.file_path)
        except Exception as e:
            logger.error(f"Face detection failed for photo {photo_id}: {e}")
            self.photo_repo.update_status(photo, "failed")
            return {"error": str(e), "faces_detected": 0, "matches": 0}

        num_faces = len(face_embeddings)
        if num_faces == 0:
            self.photo_repo.update_status(photo, "no_faces", faces_detected=0)
            logger.info(f"Photo {photo_id}: no faces detected")
            return {"faces_detected": 0, "matches": 0}

        # Update face count
        self.photo_repo.update_status(photo, "processing", faces_detected=num_faces)

        # Match each face against registered guest embeddings for this event
        all_matches = []
        threshold = settings.MATCH_CONFIDENCE_THRESHOLD
        is_solo = num_faces == 1

        for face_idx, embedding in enumerate(face_embeddings):
            matches = self.emb_repo.find_matches(
                query_embedding=embedding,
                event_id=photo.event_id,
                threshold=threshold,
            )
            for m in matches:
                all_matches.append({
                    "event_photo_id": photo.id,
                    "guest_id": m["guest_id"],
                    "confidence": m["confidence"],
                    "face_index": face_idx,
                    "is_solo": is_solo,
                })

        # Bulk insert matches
        if all_matches:
            try:
                self.match_repo.create_bulk(all_matches)
            except Exception as e:
                # Unique constraint violation = duplicate match, skip
                self.db.rollback()
                logger.warning(f"Some matches already exist for photo {photo_id}: {e}")

        # Mark as done
        self.photo_repo.update_status(photo, "success", faces_detected=num_faces)
        logger.info(
            f"Photo {photo_id}: {num_faces} faces detected, "
            f"{len(all_matches)} matches found"
        )

        return {"faces_detected": num_faces, "matches": len(all_matches)}

    def _detect_faces(self, image_path: str) -> list[list[float]]:
        """
        Detect all faces in an image and return their 512-dim embeddings.
        Unlike guest registration (which rejects multi-face), here we accept all.
        """
        from deepface import DeepFace

        try:
            results = DeepFace.represent(
                img_path=image_path,
                model_name="ArcFace",
                detector_backend="retinaface",
                enforce_detection=False,  # Don't error on no faces — return empty
                align=True,
            )
        except Exception as e:
            logger.error(f"DeepFace.represent failed: {e}")
            return []

        if not results:
            return []

        embeddings = []
        for result in results:
            # Filter out low-confidence detections
            face_confidence = float(result.get("face_confidence", 0))
            if face_confidence < 0.5:
                continue
            embeddings.append(result["embedding"])

        return embeddings
