from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Any
from uuid import UUID

from api.dependencies import get_current_user, get_db
from models.event import Event
from models.photo_cluster import PhotoCluster
from models.photo import Photo
from models.user import User

router = APIRouter()

from worker.tasks import cluster_duplicates_task


def _owned_event(db: Session, event_id: UUID, user_id: UUID) -> Event:
    event = db.query(Event).filter(
        Event.id == event_id,
        Event.created_by == user_id,
    ).first()
    if not event:
        # Do not reveal whether an event exists for another organizer.
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def _event_cluster(db: Session, event_id: UUID, cluster_id: UUID) -> PhotoCluster:
    cluster = db.query(PhotoCluster).filter(
        PhotoCluster.id == cluster_id,
        PhotoCluster.event_id == event_id,
    ).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster

@router.post("/{event_id}/clusters/run")
def run_deduplication(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _owned_event(db, event_id, current_user.id)  # type: ignore[arg-type]
    # Dispatch Celery task instead of synchronous execution
    task = cluster_duplicates_task.delay(str(event_id))
    return {"status": "enqueued", "task_id": task.id}

@router.get("/{event_id}/clusters")
def get_clusters(
    event_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=200),
    min_size: int = Query(2, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _owned_event(db, event_id, current_user.id)  # type: ignore[arg-type]
    query = db.query(PhotoCluster).filter(
        PhotoCluster.event_id == event_id,
        PhotoCluster.size >= min_size,
    )
    total = query.count()
    clusters = (
        query.order_by(PhotoCluster.created_at.desc(), PhotoCluster.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"data": clusters, "total": total, "page": page, "page_size": page_size}

@router.get("/{event_id}/clusters/{cluster_id}")
def get_cluster_details(
    event_id: UUID,
    cluster_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _owned_event(db, event_id, current_user.id)  # type: ignore[arg-type]
    _event_cluster(db, event_id, cluster_id)
    photos = db.query(Photo).filter(
        Photo.event_id == event_id,
        Photo.dup_cluster_id == cluster_id,
    ).all()
    return {"cluster_id": cluster_id, "photos": photos}

@router.post("/{event_id}/clusters/{cluster_id}/break")
def break_cluster(
    event_id: UUID,
    cluster_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _owned_event(db, event_id, current_user.id)  # type: ignore[arg-type]
    c = _event_cluster(db, event_id, cluster_id)
        
    photos = db.query(Photo).filter(Photo.dup_cluster_id == cluster_id).all()
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
    db.query(Photo).filter(Photo.dup_cluster_id == cluster_id).update({
        "dup_cluster_id": None,
        "is_cluster_representative": False
    })
    
    # We must keep the cluster record to remember exclusions, but maybe set size to 0
    c.size = 0  # type: ignore
    db.commit()
    return {"status": "success", "message": "Cluster broken"}

@router.post("/{event_id}/clusters/{cluster_id}/exclude")
def exclude_photo(
    event_id: UUID,
    cluster_id: UUID,
    photo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _owned_event(db, event_id, current_user.id)  # type: ignore[arg-type]
    c = _event_cluster(db, event_id, cluster_id)
        
    photo = db.query(Photo).filter(
        Photo.id == photo_id,
        Photo.event_id == event_id,
        Photo.dup_cluster_id == cluster_id,
    ).first()
    
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not in cluster")
        
    # Get all other photos in cluster to create exclusions
    other_photos = db.query(Photo).filter(
        Photo.event_id == event_id,
        Photo.dup_cluster_id == cluster_id,
        Photo.id != photo_id,
    ).all()
    
    exclusions = [[str(photo_id), str(op.id)] for op in other_photos]
    
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
        db.query(Photo).filter(Photo.dup_cluster_id == cluster_id).update({
            "dup_cluster_id": None,
            "is_cluster_representative": False
        })
        c.size = 0  # type: ignore
    elif c.representative_photo_id == photo_id and other_photos:
        c.representative_photo_id = other_photos[0].id
        other_photos[0].is_cluster_representative = True  # type: ignore
        
    db.commit()
    return {"status": "success"}
    
@router.post("/{event_id}/clusters/{cluster_id}/representative")
def set_representative(
    event_id: UUID,
    cluster_id: UUID,
    photo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _owned_event(db, event_id, current_user.id)  # type: ignore[arg-type]
    c = _event_cluster(db, event_id, cluster_id)
        
    photo = db.query(Photo).filter(
        Photo.id == photo_id,
        Photo.event_id == event_id,
        Photo.dup_cluster_id == cluster_id,
    ).first()
    
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not in cluster")
        
    c.representative_photo_id = photo.id
    
    db.query(Photo).filter(Photo.dup_cluster_id == cluster_id).update({
        "is_cluster_representative": False
    })
    
    photo.is_cluster_representative = True  # type: ignore
    db.commit()
    
    return {"status": "success"}
