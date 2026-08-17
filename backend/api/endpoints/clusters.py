from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, update
import uuid
from typing import Any

from api.dependencies import get_db
from models.photo_cluster import PhotoCluster
from models.photo import Photo
from services.dedup_service import DedupService

router = APIRouter()

from worker.tasks import cluster_duplicates_task

@router.post("/{event_id}/clusters/run")
def run_deduplication(event_id: str, db: Session = Depends(get_db)) -> Any:
    # Dispatch Celery task instead of synchronous execution
    task = cluster_duplicates_task.delay(event_id)
    return {"status": "enqueued", "task_id": task.id}

@router.get("/{event_id}/clusters")
def get_clusters(event_id: str, db: Session = Depends(get_db)) -> Any:
    clusters = db.query(PhotoCluster).filter(PhotoCluster.event_id == uuid.UUID(event_id)).all()
    # Eager load representative photo isn't configured in ORM yet so we just return IDs
    return clusters

@router.get("/{event_id}/clusters/{cluster_id}")
def get_cluster_details(event_id: str, cluster_id: str, db: Session = Depends(get_db)) -> Any:
    photos = db.query(Photo).filter(
        Photo.event_id == uuid.UUID(event_id),
        Photo.dup_cluster_id == uuid.UUID(cluster_id)
    ).all()
    return {"cluster_id": cluster_id, "photos": photos}

@router.post("/{event_id}/clusters/{cluster_id}/break")
def break_cluster(event_id: str, cluster_id: str, db: Session = Depends(get_db)) -> Any:
    c = db.query(PhotoCluster).filter(PhotoCluster.id == uuid.UUID(cluster_id)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cluster not found")
        
    photos = db.query(Photo).filter(Photo.dup_cluster_id == uuid.UUID(cluster_id)).all()
    if not photos:
        db.delete(c)
        db.commit()
        return {"status": "success", "message": "Cluster deleted"}
        
    pids = [str(p.id) for p in photos]
    
    # Generate pairwise exclusions
    exclusions = []
    for i in range(len(pids)):
        for j in range(i+1, len(pids)):
            exclusions.append([pids[i], pids[j]])
            
    if not c.params:
        c.params = {}  # type: ignore
    
    if "excluded_pairs" not in c.params:  # type: ignore
        c.params["excluded_pairs"] = []  # type: ignore
    
    c.params["excluded_pairs"].extend(exclusions)  # type: ignore
    
    # Unset cluster id
    db.query(Photo).filter(Photo.dup_cluster_id == uuid.UUID(cluster_id)).update({
        "dup_cluster_id": None,
        "is_cluster_representative": False
    })
    
    # We must keep the cluster record to remember exclusions, but maybe set size to 0
    c.size = 0  # type: ignore
    db.commit()
    return {"status": "success", "message": "Cluster broken"}

@router.post("/{event_id}/clusters/{cluster_id}/exclude")
def exclude_photo(event_id: str, cluster_id: str, photo_id: str, db: Session = Depends(get_db)) -> Any:
    c = db.query(PhotoCluster).filter(PhotoCluster.id == uuid.UUID(cluster_id)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cluster not found")
        
    photo = db.query(Photo).filter(
        Photo.id == uuid.UUID(photo_id), 
        Photo.dup_cluster_id == uuid.UUID(cluster_id)
    ).first()
    
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not in cluster")
        
    # Get all other photos in cluster to create exclusions
    other_photos = db.query(Photo).filter(
        Photo.dup_cluster_id == uuid.UUID(cluster_id),
        Photo.id != uuid.UUID(photo_id)
    ).all()
    
    exclusions = [[photo_id, str(op.id)] for op in other_photos]
    
    if not c.params:
        c.params = {}  # type: ignore
        
    if "excluded_pairs" not in c.params:  # type: ignore
        c.params["excluded_pairs"] = []  # type: ignore
        
    c.params["excluded_pairs"].extend(exclusions)  # type: ignore
    
    photo.dup_cluster_id = None  # type: ignore
    photo.is_cluster_representative = False  # type: ignore
    
    c.size = max(0, c.size - 1)  # type: ignore
    if c.size <= 1:
        # Unset the rest
        db.query(Photo).filter(Photo.dup_cluster_id == uuid.UUID(cluster_id)).update({
            "dup_cluster_id": None,
            "is_cluster_representative": False
        })
        c.size = 0  # type: ignore
    elif c.representative_photo_id == uuid.UUID(photo_id) and other_photos:
        c.representative_photo_id = other_photos[0].id
        other_photos[0].is_cluster_representative = True  # type: ignore
        
    db.commit()
    return {"status": "success"}
    
@router.post("/{event_id}/clusters/{cluster_id}/representative")
def set_representative(event_id: str, cluster_id: str, photo_id: str, db: Session = Depends(get_db)) -> Any:
    c = db.query(PhotoCluster).filter(PhotoCluster.id == uuid.UUID(cluster_id)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cluster not found")
        
    photo = db.query(Photo).filter(
        Photo.id == uuid.UUID(photo_id), 
        Photo.dup_cluster_id == uuid.UUID(cluster_id)
    ).first()
    
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not in cluster")
        
    c.representative_photo_id = photo.id
    
    db.query(Photo).filter(Photo.dup_cluster_id == uuid.UUID(cluster_id)).update({
        "is_cluster_representative": False
    })
    
    photo.is_cluster_representative = True  # type: ignore
    db.commit()
    
    return {"status": "success"}
