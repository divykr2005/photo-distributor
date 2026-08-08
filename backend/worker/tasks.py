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
