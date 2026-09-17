import cv2
import numpy as np

from services.face_presence import contains_face


def _encode(image: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    return encoded.tobytes()


def test_blank_image_has_no_face() -> None:
    blank = np.full((480, 640, 3), 255, dtype=np.uint8)
    assert contains_face(_encode(blank)) is False


def test_invalid_image_has_no_face() -> None:
    assert contains_face(b"not an image") is False
