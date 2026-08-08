import logging
import cv2
import numpy as np
from insightface.app import FaceAnalysis

logger = logging.getLogger(__name__)

class FaceProcessor:
    _instance = None

    def __init__(self):
        # ponytail: Singleton to avoid loading 300MB model on every request
        # ctx_id=-1 forces CPU which is safer for dev
        logger.info("Initializing InsightFace model (this takes a moment on first run)...")
        self.app = FaceAnalysis(name='buffalo_l', root='.insightface', allowed_modules=['detection', 'recognition'])
        self.app.prepare(ctx_id=-1, det_size=(640, 640))
        logger.info("InsightFace model loaded.")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def process_image(self, image_path: str):
        """
        Reads image from path and returns face embedding if exactly one face is found.
        Raises ValueError with specific reasons if quality checks fail.
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError("Failed to read image file.")
        
        # ponytail: lazy dark/blur check. 
        # If the image is pitch black or completely white, std will be near 0
        if img.std() < 10:
            raise ValueError("Image quality too poor (too dark or blurry).")

        faces = self.app.get(img)

        if len(faces) == 0:
            raise ValueError("No face detected in the image.")
        if len(faces) > 1:
            raise ValueError(f"Multiple faces ({len(faces)}) detected. Please ensure only one face is visible.")

        face = faces[0]
        
        # ponytail: check if face is too small
        bbox = face.bbox
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        if width < 50 or height < 50:
            raise ValueError("Face is too small or too far away.")

        # the embedding is a 512-d float32 numpy array
        return face.normed_embedding
