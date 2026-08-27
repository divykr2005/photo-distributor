import logging
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from celery import shared_task

from database.session import SessionLocal
from models.match import Match
from models.photo_face import PhotoFace
from models.photo_cluster import PhotoCluster
from sqlalchemy import func
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

@shared_task(
    name="workers.quality.rank_guest_clusters",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def rank_guest_clusters(self, event_id_str: str, guest_id_str: Optional[str] = None):
    """
    Ranks matches per guest within each perceptual cluster by composite_quality.
    The highest quality photo in each cluster gets cluster_rank = 1.
    """
    event_id = uuid.UUID(event_id_str)
    
    db = SessionLocal()
    try:
        # We need to rank Matches by the underlying PhotoFace's composite_quality,
        # grouped by (guest_id, dup_cluster_id).
        # dup_cluster_id comes from the Photo table via the PhotoCluster association, 
        # or it's the root_photo_id of the cluster.
        # Actually, let's look at the database schema.
        # Match -> PhotoFace (photo_face_id) -> Photo (photo_id) -> PhotoCluster (cluster_id)
        # For each guest, for each cluster they appear in, sort by face quality.
        
        # 1. Fetch all matches for the event (optionally filtered by guest)
        query = db.query(Match, PhotoFace.composite_quality, PhotoCluster.root_photo_id)\
            .join(PhotoFace, Match.photo_face_id == PhotoFace.id)\
            .outerjoin(PhotoCluster, PhotoFace.photo_id == PhotoCluster.photo_id)\
            .filter(Match.event_id == event_id)
            
        if guest_id_str:
            query = query.filter(Match.guest_id == uuid.UUID(guest_id_str))
            
        matches_data = query.all()
        
        # Group by (guest_id, root_photo_id/photo_id)
        from collections import defaultdict
        
        # We define a "burst group" as either the root_photo_id of its cluster,
        # or its own photo_id if it's not in a cluster.
        clusters = defaultdict(list)
        
        for match, quality, root_id in matches_data:
            # If not in a cluster, the photo forms its own group
            cluster_group = str(root_id) if root_id else str(match.photo_face.photo_id)
            key = (str(match.guest_id), cluster_group)
            
            # Default quality to 0 if missing
            q_val = quality if quality is not None else 0.0
            clusters[key].append((match, q_val))
            
        # Rank and update
        updates = []
        now = datetime.now(timezone.utc)
        
        for key, match_list in clusters.items():
            # Sort by quality descending, then by similarity descending to break ties
            match_list.sort(key=lambda x: (x[1], x[0].similarity), reverse=True)
            
            for rank, (match, _) in enumerate(match_list, start=1):
                if match.cluster_rank != rank:
                    match.cluster_rank = rank
                    match.ranked_at = now
                    updates.append(match)
                    
        if updates:
            db.commit()
            logger.info(f"Updated cluster_rank for {len(updates)} matches in event {event_id_str}.")
        else:
            logger.info(f"No rank updates needed for event {event_id_str}.")
            
        return {"status": "success", "updated_matches": len(updates)}
        
    except Exception as e:
        logger.error(f"Error in rank_guest_clusters for event {event_id_str}: {e}")
        db.rollback()
        raise
    finally:
        db.close()
