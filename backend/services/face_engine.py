import os
import io
import math
import logging
import cv2
import numpy as np
from datetime import datetime
from PIL import Image, ImageOps
from typing import List, Tuple, Dict, Any, Optional
from services.face_quality import (
    sharpness_score,
    eye_open_score,
    smile_score,
    frontality_score,
    exposure_score,
    compute_composite,
)

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

logger = logging.getLogger(__name__)

MAX_IMAGE_PIXELS = 50_000_000
WEB_MAX_EDGE = 1600
THUMB_MAX_EDGE = 400

LAPLACIAN_BLUR_FLOOR = 40.0
MIN_DET_SCORE = 0.5
MIN_FACE_AREA_RATIO = 0.005  # 0.5%
MAX_YAW_DEG = 45.0


class FaceEngine:
    _instance: Optional["FaceEngine"] = None

    def __init__(self):
        import insightface
        from insightface.app import FaceAnalysis

        model_name = os.getenv("INSIGHTFACE_MODEL", "buffalo_l")
        det_size_val = int(os.getenv("INSIGHTFACE_DET_SIZE", "640"))
        
        logger.info(f"Initializing InsightFace FaceEngine with model={model_name}, det_size={det_size_val}")
        self.app = FaceAnalysis(name=model_name, providers=['CPUExecutionProvider'])
        self.app.prepare(ctx_id=0, det_size=(det_size_val, det_size_val))
        logger.info("InsightFace FaceEngine initialized successfully.")

    @classmethod
    def get_instance(cls) -> "FaceEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def process_photo_bytes(
        self, raw_bytes: bytes, event_id: str, photo_id: str
    ) -> Tuple[bytes, bytes, int, int, Optional[str], List[Dict[str, Any]]]:
        """
        Processes original photo bytes:
        1. Decodes and applies EXIF orientation.
        2. Generates 1600px web JPEG and 400px thumbnail JPEG.
        3. Detects faces on web image, extracts normalized bboxes [0,1], 512-dim normalized embeddings, quality scores/flags, and padded face crops.

        Returns (web_bytes, thumb_bytes, web_width, web_height, exif_taken_at_iso, list_of_detected_faces)
        """
        # Decompression bomb check
        PIL_Image = Image.open(io.BytesIO(raw_bytes))
        width, height = PIL_Image.size
        if width * height > MAX_IMAGE_PIXELS:
            raise ValueError(f"Image dimensions ({width}x{height}) exceed maximum allowed pixels ({MAX_IMAGE_PIXELS}).")

        # EXIF datetime extraction
        exif_taken_at = None
        try:
            exif_data = PIL_Image.getexif()
            if exif_data:
                # 36867 is DateTimeOriginal, 306 is DateTime
                date_str = exif_data.get(36867) or exif_data.get(306)
                if date_str and isinstance(date_str, str):
                    try:
                        dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                        exif_taken_at = dt.isoformat()
                    except Exception:
                        pass
        except Exception:
            pass

        # Apply EXIF orientation
        PIL_Image = ImageOps.exif_transpose(PIL_Image)
        if PIL_Image.mode != "RGB":
            PIL_Image = PIL_Image.convert("RGB")

        orig_w, orig_h = PIL_Image.size

        # Web derivative (max 1600px)
        web_pil = PIL_Image.copy()
        web_pil.thumbnail((WEB_MAX_EDGE, WEB_MAX_EDGE), Image.Resampling.LANCZOS)
        web_w, web_h = web_pil.size

        web_io = io.BytesIO()
        web_pil.save(web_io, format="JPEG", quality=82)
        web_bytes = web_io.getvalue()

        # Thumb derivative (max 400px)
        thumb_pil = PIL_Image.copy()
        thumb_pil.thumbnail((THUMB_MAX_EDGE, THUMB_MAX_EDGE), Image.Resampling.LANCZOS)
        thumb_io = io.BytesIO()
        thumb_pil.save(thumb_io, format="JPEG", quality=82)
        thumb_bytes = thumb_io.getvalue()

        # Convert web image to OpenCV BGR for InsightFace detection
        web_np = np.array(web_pil)
        web_bgr = cv2.cvtColor(web_np, cv2.COLOR_RGB2BGR)

        # Run InsightFace face detection & embedding extraction
        insight_faces = self.app.get(web_bgr)

        detected_faces = []
        for face in insight_faces:
            bbox = face.bbox.astype(float)  # [x1, y1, x2, y2] in web image pixel coords
            x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]

            w_px = max(1.0, x2 - x1)
            h_px = max(1.0, y2 - y1)

            # Normalized bounding box [0.0, 1.0] relative to web image
            bbox_x = max(0.0, min(1.0, x1 / float(web_w)))
            bbox_y = max(0.0, min(1.0, y1 / float(web_h)))
            bbox_w = max(0.0, min(1.0 - bbox_x, w_px / float(web_w)))
            bbox_h = max(0.0, min(1.0 - bbox_y, h_px / float(web_h)))

            det_score = float(face.det_score) if hasattr(face, "det_score") else 1.0

            # 512-dim embedding L2 normalization
            emb = face.embedding.astype(np.float32)
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm
            emb_list = emb.tolist()

            # Quality metrics
            face_area_ratio = (w_px * h_px) / (web_w * web_h)

            # Crop face area for blur calculation
            ix1 = max(0, int(x1))
            iy1 = max(0, int(y1))
            ix2 = min(web_w, int(x2))
            iy2 = min(web_h, int(y2))
            face_crop_bgr = web_bgr[iy1:iy2, ix1:ix2]

            if face_crop_bgr.size > 0:
                gray = cv2.cvtColor(face_crop_bgr, cv2.COLOR_BGR2GRAY)
                blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            else:
                blur_score = 0.0

            # Pose angles (yaw, pitch, roll) if available
            yaw = pitch = roll = 0.0
            if hasattr(face, "pose") and face.pose is not None and len(face.pose) >= 3:
                pitch, yaw, roll = float(face.pose[0]), float(face.pose[1]), float(face.pose[2])

            landmarks_2d106 = face.landmark_2d_106 if hasattr(face, "landmark_2d_106") else None
            
            # W4.D23: new quality sub-scores
            sh_score = sharpness_score(web_bgr, (x1, y1, x2, y2))
            eo_score = eye_open_score(landmarks_2d106)
            sm_score = smile_score(landmarks_2d106)
            fr_score = frontality_score(yaw, pitch, roll)
            ex_score = exposure_score(web_bgr, (x1, y1, x2, y2))
            
            composite = compute_composite(sh_score, eo_score, fr_score, ex_score, sm_score)

            # Quality evaluation & flags
            quality_flags = []
            if det_score < MIN_DET_SCORE:
                quality_flags.append("low_detection_score")
            if face_area_ratio < MIN_FACE_AREA_RATIO:
                quality_flags.append("too_small")
            if blur_score < LAPLACIAN_BLUR_FLOOR:
                quality_flags.append("blurry")
            if abs(yaw) > MAX_YAW_DEG:
                quality_flags.append("extreme_pose")

            is_matchable = len(quality_flags) == 0

            # Generate 15% padded 256px square face crop
            pad_x = w_px * 0.15
            pad_y = h_px * 0.15
            cx1 = max(0, int(x1 - pad_x))
            cy1 = max(0, int(y1 - pad_y))
            cx2 = min(web_w, int(x2 + pad_x))
            cy2 = min(web_h, int(y2 + pad_y))

            crop_pil = web_pil.crop((cx1, cy1, cx2, cy2))
            crop_pil.thumbnail((256, 256), Image.Resampling.LANCZOS)
            crop_io = io.BytesIO()
            crop_pil.save(crop_io, format="JPEG", quality=82)
            crop_bytes = crop_io.getvalue()

            overall_quality = round(composite, 4)

            detected_faces.append({
                "bbox_x": bbox_x,
                "bbox_y": bbox_y,
                "bbox_w": bbox_w,
                "bbox_h": bbox_h,
                "det_score": det_score,
                "embedding": emb_list,
                "quality_score": overall_quality,
                "blur_score": round(blur_score, 2),
                "face_area_ratio": round(face_area_ratio, 6),
                "yaw": round(yaw, 2),
                "pitch": round(pitch, 2),
                "roll": round(roll, 2),
                "sharpness_score": round(sh_score, 4),
                "eye_open_score": round(eo_score, 4),
                "smile_score": round(sm_score, 4),
                "frontality_score": round(fr_score, 4),
                "exposure_score": round(ex_score, 4),
                "composite_quality": round(composite, 4),
                "is_matchable": is_matchable,
                "quality_flags": quality_flags,
                "crop_bytes": crop_bytes,
            })

        return web_bytes, thumb_bytes, web_w, web_h, exif_taken_at, detected_faces

    def process_guest_image(self, image_path: str) -> Tuple[List[float], float]:
        """
        Process a guest registration photo using InsightFace.
        Returns (embedding_list, quality_score).
        Raises ValueError if quality checks fail.
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError("Could not read the image file.")
            
        faces = self.app.get(img)
        if not faces:
            raise ValueError("No face detected in the image.")
        if len(faces) > 1:
            raise ValueError(f"{len(faces)} faces detected. Please ensure only one person is visible.")
            
        face = faces[0]
        det_score = float(face.det_score) if hasattr(face, "det_score") else 1.0
        
        # Check blur
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if blur_score < LAPLACIAN_BLUR_FLOOR:
            raise ValueError("Image is too blurry. Please retake the photo.")
            
        # Normalize embedding
        emb = face.embedding.astype(np.float32)
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
            
        overall_quality = round(det_score * min(1.0, blur_score / 100.0), 4)
        return emb.tolist(), overall_quality
