import logging
from sqlalchemy.orm import Session
from worker.face_processor import FaceProcessor
from repositories.guest_repository import GuestRepository

logger = logging.getLogger(__name__)

def process_guest_registration_photo(guest_id: str, photo_path: str, db: Session):
    """
    Background task to extract embedding from a guest's registration photo.
    Updates the guest record with the embedding or failure status.
    """
    guest_repo = GuestRepository(db)
    guest = guest_repo.get(guest_id)
    if not guest:
        logger.error(f"Guest {guest_id} not found when processing photo.")
        return

    try:
        processor = FaceProcessor.get_instance()
        embedding = processor.process_image(photo_path)
        
        # pgvector expects a list of floats
        embedding_list = embedding.tolist()
        
        guest_repo.update_embedding(
            guest_id=guest_id,
            embedding=embedding_list,
            status="success",
            notes=None  # Clear any previous errors
        )
        logger.info(f"Successfully processed embedding for guest {guest_id}")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to process embedding for guest {guest_id}: {error_msg}")
        guest_repo.update_embedding(
            guest_id=guest_id,
            embedding=None,
            status="failed",
            notes=error_msg
        )

def process_event_photo(photo_id: str, photo_path: str, db: Session):
    """
    Background task to detect all faces in an event photo and match them against registered guests.
    """
    from models.event_photo import EventPhoto
    from models.photo_match import PhotoMatch
    from models.guest import Guest
    
    photo = db.query(EventPhoto).filter(EventPhoto.id == photo_id).first()
    if not photo:
        return

    photo.status = "processing"
    db.commit()

    try:
        processor = FaceProcessor.get_instance()
        import cv2
        img = cv2.imread(photo_path)
        if img is None:
            raise ValueError("Failed to read image")
            
        faces = processor.app.get(img)
        photo.faces_detected = len(faces)
        
        if len(faces) == 0:
            photo.status = "success"
            db.commit()
            return
            
        is_solo = len(faces) == 1
        
        # Get all guests for this event with embeddings
        guests = db.query(Guest).filter(
            Guest.event_id == photo.event_id,
            Guest.embedding_status == "success",
            Guest.face_embedding.is_not(None)
        ).all()
        
        import numpy as np
        
        matched_count = 0
        for face in faces:
            # InsightFace output is normed_embedding
            emb = face.normed_embedding
            
            best_guest_id = None
            best_score = -1.0
            
            for guest in guests:
                # Calculate cosine similarity using numpy
                g_emb = np.array(guest.face_embedding, dtype=np.float32)
                score = np.dot(emb, g_emb) / (np.linalg.norm(emb) * np.linalg.norm(g_emb))
                
                # Threshold for buffalo_l is usually around 0.5 - 0.6
                if score > 0.55 and score > best_score:
                    best_score = score
                    best_guest_id = guest.id
                    
            if best_guest_id:
                match = PhotoMatch(
                    event_photo_id=photo.id,
                    guest_id=best_guest_id,
                    confidence=float(best_score),
                    is_solo=is_solo
                )
                db.add(match)
                matched_count += 1
                
        photo.status = "success"
        db.commit()
        logger.info(f"Photo {photo_id}: {len(faces)} faces found, {matched_count} matches.")
        
    except Exception as e:
        logger.error(f"Failed to process event photo {photo_id}: {e}")
        photo.status = "failed"
        db.commit()
