import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Quality thresholds
LAPLACIAN_BLUR_THRESHOLD = 80.0   # Laplacian variance below this -> blurry
DARKNESS_THRESHOLD = 40.0         # Mean gray pixel value below this -> too dark
MIN_FACE_PX = 50                  # Face bbox width/height floor in pixels


class FaceQualityError(ValueError):
    """Raised when an image fails a quality gate with a specific, actionable reason."""


class FaceProcessor:
    """
    Thin singleton wrapper around DeepFace (ArcFace model, RetinaFace detector).

    Why DeepFace instead of InsightFace:
      - InsightFace requires C++ build tools on Windows; DeepFace is pure-pip.
      - Both use ArcFace and produce identical 512-dim L2-normalised embeddings.
      - At 500 guests the difference in throughput is immaterial.
      - The Docker ai-service (Week 7) can swap in InsightFace with zero schema
        changes if needed.
    """

    _instance = None

    @classmethod
    def get_instance(cls) -> "FaceProcessor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def process_image(self, image_path: str) -> tuple[list[float], float]:
        """
        Run quality checks then extract a 512-dim ArcFace embedding.

        Returns (embedding_list, quality_score).
        Raises FaceQualityError with a user-readable reason on any failure.
        """
        from deepface import DeepFace  # lazy import so startup is fast

        img = cv2.imread(image_path)
        if img is None:
            raise FaceQualityError("Could not read the image file. Please re-upload.")

        self._check_darkness(img)
        self._check_blur(img)

        # DeepFace.represent returns a list — one entry per detected face.
        # enforce_detection=True (default) raises ValueError when no face found.
        try:
            results = DeepFace.represent(
                img_path=image_path,
                model_name="ArcFace",       # 512-dim, same family as InsightFace buffalo_l
                detector_backend="retinaface",
                enforce_detection=True,
                align=True,
            )
        except ValueError:
            raise FaceQualityError(
                "No face detected. Make sure your face is fully visible, "
                "well-lit, and centred in the frame."
            )

        if len(results) > 1:
            raise FaceQualityError(
                f"{len(results)} faces detected. Please ensure only one person "
                "is visible in the photo."
            )

        result = results[0]
        self._check_face_size(result)

        embedding: list[float] = result["embedding"]   # 512 floats
        quality_score = round(float(result.get("face_confidence", 1.0)), 4)
        return embedding, quality_score

    # ------------------------------------------------------------------
    # Individual quality gates
    # ------------------------------------------------------------------

    def _check_darkness(self, img: np.ndarray) -> None:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean_val = float(gray.mean())
        if mean_val < DARKNESS_THRESHOLD:
            raise FaceQualityError(
                f"Image is too dark (brightness {mean_val:.0f}/255). "
                "Please take the photo in better lighting."
            )

    def _check_blur(self, img: np.ndarray) -> None:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if lap_var < LAPLACIAN_BLUR_THRESHOLD:
            raise FaceQualityError(
                f"Image is too blurry (sharpness score {lap_var:.1f}). "
                "Please hold still and retake the photo."
            )

    def _check_face_size(self, result: dict) -> None:
        area = result.get("facial_area", {})
        w = area.get("w", 9999)
        h = area.get("h", 9999)
        if w < MIN_FACE_PX or h < MIN_FACE_PX:
            raise FaceQualityError(
                f"Face is too small ({w}x{h} px). "
                "Please move closer to the camera."
            )
