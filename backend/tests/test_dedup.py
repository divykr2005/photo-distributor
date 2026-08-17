import pytest
import uuid
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from models.photo import Photo
from services.dedup_service import DedupService, _popcount_matrix
import numpy as np

def test_popcount_matrix():
    a = np.array([0b1111, 0b0000], dtype=np.uint64)
    b = np.array([0b1010, 0b1111], dtype=np.uint64)
    
    dist = _popcount_matrix(a, b)
    
    assert dist.shape == (2, 2)
    # 1111 ^ 1010 = 0101 (2 bits)
    assert dist[0, 0] == 2
    # 1111 ^ 1111 = 0000 (0 bits)
    assert dist[0, 1] == 0
    # 0000 ^ 1010 = 1010 (2 bits)
    assert dist[1, 0] == 2
    # 0000 ^ 1111 = 1111 (4 bits)
    assert dist[1, 1] == 4

def test_dedup_service_empty(db_session: Session):
    service = DedupService(db_session)
    result = service.cluster_duplicates(str(uuid.uuid4()))
    assert result["clusters_created"] == 0

