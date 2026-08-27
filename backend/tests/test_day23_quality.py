import pytest
from uuid import uuid4
import numpy as np

def test_sharpness_score():
    from services.face_quality import sharpness_score
    # Create a dummy image
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Very blurry image
    score = sharpness_score(img, (10, 10, 90, 90))
    assert score < 0.1
    
    # Add high frequency noise
    np.random.seed(42)
    img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    score_sharp = sharpness_score(img, (10, 10, 90, 90))
    assert score_sharp > 0.9

def test_eye_open_score():
    from services.face_quality import eye_open_score
    # Create dummy landmarks
    landmarks = np.zeros((106, 2))
    # Dummy eye landmarks for open eyes
    # Left eye: 33-42. Right eye: 87-96
    # Width of 10, height of 5 -> EAR = 0.5
    for i in range(33, 43):
        landmarks[i] = [i-33, (i%2)*5]
    for i in range(87, 97):
        landmarks[i] = [i-87+20, (i%2)*5]
        
    score = eye_open_score(landmarks)
    assert score > 0.8
    
    # Closed eyes: height of 1 -> EAR = 0.1
    for i in range(33, 43):
        landmarks[i] = [i-33, (i%2)*1]
    for i in range(87, 97):
        landmarks[i] = [i-87+20, (i%2)*1]
    
    score_closed = eye_open_score(landmarks)
    assert score_closed < 0.2

def test_frontality_score():
    from services.face_quality import frontality_score
    # Perfect frontality
    assert frontality_score(0, 0, 0) == 1.0
    
    # Slight angle
    assert frontality_score(10, 5, 0) > 0.9
    
    # Profile
    score = frontality_score(90, 0, 0)
    assert abs(score - 0.0) < 0.01

def test_exposure_score():
    from services.face_quality import exposure_score
    
    # Perfectly exposed mid-gray
    img = np.ones((100, 100, 3), dtype=np.uint8) * 128
    assert exposure_score(img, (0, 0, 100, 100)) == 1.0
    
    # Completely clipped (white)
    img_white = np.ones((100, 100, 3), dtype=np.uint8) * 255
    assert exposure_score(img_white, (0, 0, 100, 100)) == 0.0
    
    # Completely black
    img_black = np.zeros((100, 100, 3), dtype=np.uint8)
    assert exposure_score(img_black, (0, 0, 100, 100)) == 0.0

def test_compute_composite():
    from services.face_quality import compute_composite
    import os
    # Default weights are 0.3, 0.25, 0.2, 0.15, 0.1
    
    # Perfect score
    assert compute_composite(1.0, 1.0, 1.0, 1.0, 1.0) == 1.0
    
    # Blurry image score
    # sharpness = 0.0
    score = compute_composite(0.0, 1.0, 1.0, 1.0, 1.0)
    assert abs(score - 0.7) < 0.001
