import math
import numpy as np
import cv2
from typing import Optional

def sharpness_score(web_image_bgr: np.ndarray, bbox_px: tuple) -> float:
    """
    Laplacian variance over the face bbox region of the web derivative, 
    squashed with a logistic function to [0,1].
    """
    x1, y1, x2, y2 = [int(v) for v in bbox_px]
    h, w = web_image_bgr.shape[:2]
    
    # Pad slightly but stay within bounds
    ix1 = max(0, x1)
    iy1 = max(0, y1)
    ix2 = min(w, x2)
    iy2 = min(h, y2)
    
    face_crop = web_image_bgr[iy1:iy2, ix1:ix2]
    if face_crop.size == 0:
        return 0.0
        
    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    # Squashing function (logistic): midpoint 100, scale 30
    # lap_var ranges from ~10 (very blurry) to ~500+ (very sharp)
    score = 1.0 / (1.0 + math.exp(-(lap_var - 100.0) / 30.0))
    return float(np.clip(score, 0.0, 1.0))


def _aspect_ratio(pts: np.ndarray) -> float:
    if len(pts) == 0:
        return 0.0
    min_x, min_y = np.min(pts, axis=0)
    max_x, max_y = np.max(pts, axis=0)
    w = max_x - min_x
    h = max_y - min_y
    if w <= 0:
        return 0.0
    return float(h / w)


def eye_open_score(landmarks_2d106: Optional[np.ndarray]) -> float:
    """
    Eye Aspect Ratio from 2d106 landmarks, min of both eyes.
    Using approximate ranges for left (33-42) and right (87-96) eyes.
    """
    if landmarks_2d106 is None or len(landmarks_2d106) < 106:
        return 1.0  # fallback
    
    # In 106 points, eyes are typically 33-42 and 87-96 or similar.
    # We take aspect ratio of bounding box of these points.
    eye1 = landmarks_2d106[33:43]
    eye2 = landmarks_2d106[87:97]
    
    ear1 = _aspect_ratio(eye1)
    ear2 = _aspect_ratio(eye2)
    
    min_ear = min(ear1, ear2)
    
    # Typically EAR < 0.15 is closed, > 0.25 is open.
    # Map to [0,1]
    score = (min_ear - 0.10) / 0.20
    return float(np.clip(score, 0.0, 1.0))


def smile_score(landmarks_2d106: Optional[np.ndarray]) -> float:
    """
    Mouth Aspect Ratio + mouth-corner elevation from 2d106.
    Mouth is typically points 52-71.
    """
    if landmarks_2d106 is None or len(landmarks_2d106) < 106:
        return 0.0  # fallback
        
    mouth = landmarks_2d106[52:72]
    mar = _aspect_ratio(mouth)
    
    # A wide smile increases width, lowering MAR. But an open-mouth smile increases MAR.
    # A simple proxy: mouth wider than distance between eyes.
    # For now, let's just map MAR to a smile proxy or use it directly.
    score = mar / 0.5
    return float(np.clip(score, 0.0, 1.0))


def frontality_score(yaw: float, pitch: float, roll: float) -> float:
    """
    cos(yaw) * cos(pitch), clamped to [0,1].
    Assumes angles are in degrees (or radians, but usually insightface gives radians in some versions, degrees in others - 
    insightface .pose gives pitch, yaw, roll in radians typically, but face_engine.py might convert or leave it. 
    Actually, insightface pose is usually -1.5 to 1.5 radians. Let's assume radians).
    Wait, in face_engine.py, W4.D6 says MAX_YAW_DEG=45, so if the code checks `abs(yaw) > 45` they might be degrees, 
    but Insightface native is radians. face_engine.py just did `float(face.pose[1])`.
    Let's assume the values are small (radians) or we convert.
    """
    # If the values are > pi, they are probably degrees
    y = yaw * math.pi / 180.0 if abs(yaw) > 4 else yaw
    p = pitch * math.pi / 180.0 if abs(pitch) > 4 else pitch
    
    val = math.cos(y) * math.cos(p)
    return float(np.clip(val, 0.0, 1.0))


def exposure_score(web_image_bgr: np.ndarray, bbox_px: tuple) -> float:
    """
    Penalty for clipped highlights/shadows in the face region histogram.
    """
    x1, y1, x2, y2 = [int(v) for v in bbox_px]
    h, w = web_image_bgr.shape[:2]
    
    ix1 = max(0, x1)
    iy1 = max(0, y1)
    ix2 = min(w, x2)
    iy2 = min(h, y2)
    
    face_crop = web_image_bgr[iy1:iy2, ix1:ix2]
    if face_crop.size == 0:
        return 1.0
        
    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    
    # Check percentage of pixels that are completely black (0) or white (255)
    total_pixels = gray.size
    shadows = np.sum(gray < 10)
    highlights = np.sum(gray > 245)
    
    clipped_ratio = (shadows + highlights) / float(total_pixels)
    
    # Score penalty: 0% clipped = 1.0, 20% clipped = 0.0
    score = 1.0 - (clipped_ratio / 0.2)
    return float(np.clip(score, 0.0, 1.0))


def compute_composite(sharpness: float, eye: float, front: float, exp: float, smile: float) -> float:
    """
    composite_quality = 0.30 * sharpness + 0.25 * eye_open + 0.20 * frontality + 0.15 * exposure + 0.10 * smile
    """
    # Configurable weights from env or config.py, using hardcoded defaults from D6 spec
    import os
    w_sharpness = float(os.getenv("QUALITY_W_SHARPNESS", "0.30"))
    w_eye = float(os.getenv("QUALITY_W_EYE_OPEN", "0.25"))
    w_front = float(os.getenv("QUALITY_W_FRONTALITY", "0.20"))
    w_exp = float(os.getenv("QUALITY_W_EXPOSURE", "0.15"))
    w_smile = float(os.getenv("QUALITY_W_SMILE", "0.10"))
    
    val = (
        w_sharpness * sharpness +
        w_eye * eye +
        w_front * front +
        w_exp * exp +
        w_smile * smile
    )
    return float(np.clip(val, 0.0, 1.0))
