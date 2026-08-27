from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import cast

from api.dependencies import get_current_user, get_db
from models.user import User
from repositories.event_repository import EventRepository
from schemas.event import EventCreate, EventResponse, EventUpdate

router = APIRouter()


@router.post("/", response_model=EventResponse, status_code=201)
def create_event(
    event_in: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = EventRepository(db)
    return repo.create(event_in, cast(UUID, current_user.id))


@router.get("/", response_model=list[EventResponse])
def list_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = EventRepository(db)
    return repo.get_all(cast(UUID, current_user.id))


@router.get("/{event_id}", response_model=EventResponse)
def get_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = EventRepository(db)
    event = repo.get_by_id(event_id, cast(UUID, current_user.id))
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.put("/{event_id}", response_model=EventResponse)
def update_event(
    event_id: UUID,
    event_in: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = EventRepository(db)
    event = repo.get_by_id(event_id, cast(UUID, current_user.id))
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return repo.update(event, event_in)


@router.delete("/{event_id}", status_code=204)
def delete_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = EventRepository(db)
    event = repo.get_by_id(event_id, cast(UUID, current_user.id))
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    repo.delete(event)


@router.post("/{event_id}/purge", status_code=204)
def purge_event_data(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = EventRepository(db)
    event = repo.get_by_id(event_id, cast(UUID, current_user.id))
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    from models.photo import Photo
    from models.guest import Guest
    from models.upload_batch import UploadBatch
    from services.storage.local import get_storage_backend

    storage = get_storage_backend()
    
    # Storage cleanup for photos
    photos = db.query(Photo).filter(Photo.event_id == event_id).all()
    for p in photos:
        for key in [p.storage_key, p.web_key, p.thumb_key]:
            if key:
                storage.delete(str(key))
                
    # DB Cleanup
    db.query(Photo).filter(Photo.event_id == event_id).delete(synchronize_session=False)
    db.query(Guest).filter(Guest.event_id == event_id).delete(synchronize_session=False)
    db.query(UploadBatch).filter(UploadBatch.event_id == event_id).delete(synchronize_session=False)
    db.commit()


@router.post("/{event_id}/quality-runs", status_code=202)
def trigger_quality_ranking(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Triggers a background task to compute best-of-burst rankings 
    for all guests in the event based on face quality composite scores.
    """
    repo = EventRepository(db)
    event = repo.get_by_id(event_id, cast(UUID, current_user.id))
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    from workers.quality_worker import rank_guest_clusters
    
    # Enqueue background task
    try:
        rank_guest_clusters.delay(str(event.id))  # type: ignore
    except Exception as e:
        # Fallback to sync execution if Celery is not running
        rank_guest_clusters(str(event.id))  # type: ignore
        
    return {"message": "Quality ranking job enqueued."}
