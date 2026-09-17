"""Lightweight face-presence validation before persisting guest selfies."""

import cv2
import numpy as np


def contains_face(image_bytes: bytes) -> bool:
    """Return whether an image contains at least one frontal face.

    This intentionally performs only a cheap presence check. The face worker
    remains responsible for the full quality gate and embedding extraction.
    """
    encoded = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_GRAYSCALE)
    if image is None:
        return False

    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    if cascade.empty():
        return False

    height, width = image.shape[:2]
    min_side = max(40, min(height, width) // 10)
    faces = cascade.detectMultiScale(
        image,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(min_side, min_side),
    )
    return len(faces) > 0
