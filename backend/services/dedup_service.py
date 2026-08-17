import os
import uuid
import logging
import hashlib
from typing import List, Tuple, Dict
import numpy as np

from sqlalchemy.orm import Session
from sqlalchemy import text, insert, update

from models.photo import Photo
from models.photo_cluster import PhotoCluster
from services.hashing import hamming

logger = logging.getLogger(__name__)

class UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))
        self.size = [1] * n

    def find(self, i: int) -> int:
        if self.parent[i] == i:
            return i
        self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i: int, j: int):
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            if self.size[root_i] < self.size[root_j]:
                root_i, root_j = root_j, root_i
            self.parent[root_j] = root_i
            self.size[root_i] += self.size[root_j]

def get_dedup_thresholds() -> Tuple[int, int, int]:
    phash_max = int(os.getenv("DEDUP_PHASH_MAX", 6))
    dhash_max = int(os.getenv("DEDUP_DHASH_MAX", 12))
    time_window = int(os.getenv("DEDUP_TIME_WINDOW_S", 30))
    return phash_max, dhash_max, time_window

class DedupService:
    def __init__(self, db: Session):
        self.db = db

    def cluster_duplicates(self, event_id_str: str) -> dict:
        event_id = uuid.UUID(event_id_str)
        phash_max, dhash_max, time_window = get_dedup_thresholds()
        
        # Load photos for event
        query = text("""
            SELECT id, phash, dhash, exif_taken_at 
            FROM photos 
            WHERE event_id = :event_id 
              AND status = 'processed' 
              AND phash IS NOT NULL 
              AND dhash IS NOT NULL
            ORDER BY exif_taken_at ASC
        """)
        
        rows = self.db.execute(query, {"event_id": event_id}).fetchall()
        if not rows:
            return {"status": "completed", "clusters_created": 0}
            
        N = len(rows)
        photo_ids = [r.id for r in rows]
        phash_arr = np.array([r.phash for r in rows], dtype=np.uint64)
        dhash_arr = np.array([r.dhash for r in rows], dtype=np.uint64)
        time_arr = np.array([r.exif_taken_at.timestamp() if r.exif_taken_at else -1 for r in rows], dtype=np.float64)
        
        # We also need to respect exclusions.
        # Format for exclusions: { "excluded_pairs": [ ["id1", "id2"], ... ] }
        exclusions_query = text("""
            SELECT params FROM photo_clusters WHERE event_id = :event_id AND params IS NOT NULL
        """)
        exclusion_rows = self.db.execute(exclusions_query, {"event_id": event_id}).fetchall()
        
        excluded_pairs = set()
        for r in exclusion_rows:
            params = r.params
            if isinstance(params, dict) and "excluded_pairs" in params:
                for pair in params["excluded_pairs"]:
                    if len(pair) == 2:
                        excluded_pairs.add(frozenset([str(pair[0]), str(pair[1])]))

        uf = UnionFind(N)
        
        # O(N^2) comparison. Blocked to keep memory low.
        block_size = 1024
        for i_start in range(0, N, block_size):
            i_end = min(i_start + block_size, N)
            
            p_i = phash_arr[i_start:i_end]
            d_i = dhash_arr[i_start:i_end]
            t_i = time_arr[i_start:i_end]
            
            for j_start in range(i_start, N, block_size):
                j_end = min(j_start + block_size, N)
                
                p_j = phash_arr[j_start:j_end]
                d_j = dhash_arr[j_start:j_end]
                t_j = time_arr[j_start:j_end]
                
                # Pairwise bitwise XOR popcount
                # p_i is (N_i, ), p_j is (N_j, )
                # We want a distance matrix (N_i, N_j)
                p_dist = _popcount_matrix(p_i, p_j)
                d_dist = _popcount_matrix(d_i, d_j)
                
                # Time distance
                t_i_mat = t_i[:, np.newaxis]
                t_j_mat = t_j[np.newaxis, :]
                
                # if either is -1, time constraint is satisfied
                t_dist = np.abs(t_i_mat - t_j_mat)
                t_valid = (t_i_mat == -1) | (t_j_mat == -1) | (t_dist <= time_window)
                
                # Combined mask
                mask = (p_dist <= phash_max) & (d_dist <= dhash_max) & t_valid
                
                # Zero out upper triangle if j_start == i_start
                if i_start == j_start:
                    mask = np.tril(mask, -1)
                
                # Find pairs
                idx_pairs = np.argwhere(mask)
                for r, c in idx_pairs:
                    global_i = i_start + r
                    global_j = j_start + c
                    pid_i = str(photo_ids[global_i])
                    pid_j = str(photo_ids[global_j])
                    
                    if frozenset([pid_i, pid_j]) not in excluded_pairs:
                        uf.union(global_i, global_j)

        # Build clusters
        clusters_map = {}
        for i in range(N):
            root = uf.find(i)
            clusters_map.setdefault(root, []).append(photo_ids[i])
            
        new_clusters = []
        cluster_updates = []
        photo_updates = []
        clusters_created = 0
        
        for root, p_ids in clusters_map.items():
            if len(p_ids) <= 1:
                # No duplicates for this photo
                continue
                
            sorted_pids = sorted([str(p) for p in p_ids])
            membership_hash = hashlib.sha256(",".join(sorted_pids).encode('utf-8')).hexdigest()
            
            # Find if this cluster already exists
            existing_cluster = self.db.query(PhotoCluster).filter_by(
                event_id=event_id, membership_hash=membership_hash
            ).first()
            
            cluster_id = None
            if existing_cluster:
                cluster_id = existing_cluster.id
            else:
                cluster_id = uuid.uuid4()
                # Compute time span
                c_times = [t for t in (time_arr[i] for i, pid in enumerate(photo_ids) if pid in p_ids) if t != -1]
                time_span = max(c_times) - min(c_times) if c_times else 0
                
                new_clusters.append({
                    "id": cluster_id,
                    "event_id": event_id,
                    "membership_hash": membership_hash,
                    "size": len(p_ids),
                    "time_span_s": time_span,
                    "representative_photo_id": p_ids[0] # Temporary, to be updated by Quality Ranking
                })
                clusters_created += 1
                
            # Assign photos to this cluster
            for pid in p_ids:
                photo_updates.append({
                    "id": pid,
                    "dup_cluster_id": cluster_id,
                    "is_cluster_representative": (pid == p_ids[0])
                })
                
        if new_clusters:
            self.db.execute(insert(PhotoCluster), new_clusters)
            
        if photo_updates:
            self.db.execute(update(Photo), photo_updates)
            
        self.db.commit()
        return {"status": "completed", "clusters_created": clusters_created}

def _popcount_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Compute pairwise popcount(a ^ b) matrix."""
    a_mat = a[:, np.newaxis]
    b_mat = b[np.newaxis, :]
    xor_mat = a_mat ^ b_mat
    
    # Fast popcount using view as uint8
    xor_bytes = xor_mat.view(np.uint8).reshape(*xor_mat.shape, 8)
    # create a lookup table for byte popcounts
    lut = np.zeros(256, dtype=np.uint8)
    for i in range(256):
        lut[i] = bin(i).count('1')
        
    popcounts = lut[xor_bytes]
    # sum over the 8 bytes
    return np.sum(popcounts, axis=-1)
