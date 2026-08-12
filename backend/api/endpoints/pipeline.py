from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.dependencies import get_current_user, get_db
from models.event import Event
from models.user import User
from models.photo import Photo
from models.photo_face import PhotoFace
from models.match import Match
from models.match_run import MatchRun
from schemas.match_run import MatchRunCreate, MatchRunResponse
from workers.matching import run_event_match

router = APIRouter()


def _verify_event_owner(db: Session, event_id: UUID, user_id: UUID) -> Event:
    event = (
        db.query(Event)
        .filter(Event.id == event_id, Event.created_by == user_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/events/{event_id}/pipeline-status")
def get_pipeline_status(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_event_owner(db, event_id, current_user.id)

    # Photos counts by status
    photo_status_counts = dict(
        db.query(Photo.status, func.count(Photo.id))
        .filter(Photo.event_id == event_id)
        .group_by(Photo.status)
        .all()
    )

    photos_summary = {
        "pending": photo_status_counts.get("pending", 0),
        "queued": photo_status_counts.get("queued", 0),
        "processing": photo_status_counts.get("processing", 0),
        "processed": photo_status_counts.get("processed", 0),
        "failed": photo_status_counts.get("failed", 0),
    }

    # Faces summary
    total_faces = (
        db.query(func.count(PhotoFace.id))
        .filter(PhotoFace.event_id == event_id)
        .scalar() or 0
    )
    matchable_faces = (
        db.query(func.count(PhotoFace.id))
        .filter(PhotoFace.event_id == event_id, PhotoFace.is_matchable == True)
        .scalar() or 0
    )

    faces_summary = {
        "total": total_faces,
        "matchable": matchable_faces,
        "non_matchable": total_faces - matchable_faces,
    }

    # Matches summary
    match_decision_counts = dict(
        db.query(Match.decision, func.count(Match.id))
        .filter(Match.event_id == event_id, Match.status.in_(["active", "manually_added"]))
        .group_by(Match.decision)
        .all()
    )

    matches_summary = {
        "confirmed": match_decision_counts.get("auto_confirmed", 0),
        "review": match_decision_counts.get("review", 0),
        "rejected": match_decision_counts.get("rejected", 0),
    }

    return {
        "event_id": event_id,
        "photos": photos_summary,
        "faces": faces_summary,
        "matches": matches_summary,
    }


@router.post("/events/{event_id}/match-runs", response_model=MatchRunResponse, status_code=202)
def trigger_match_run(
    event_id: UUID,
    req: MatchRunCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_event_owner(db, event_id, current_user.id)

    task = run_event_match.delay(str(event_id), force=req.force, trigger="manual_rerun")

    # Create dummy initial MatchRun representation for response
    match_run = MatchRun(
        id=UUID(int=0),
        event_id=event_id,
        trigger="manual_rerun",
        scope="full_event" if req.force else "new_photos",
        params={"force": req.force, "task_id": task.id},
        status="running",
    )
    return match_run
