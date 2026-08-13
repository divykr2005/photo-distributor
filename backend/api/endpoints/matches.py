from uuid import UUID
from typing import Optional, List, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from api.dependencies import get_current_user, get_db
from models.event import Event
from models.user import User
from models.match import Match
from models.photo_face import PhotoFace
from models.photo import Photo
from models.guest import Guest
from schemas.match import MatchResponse, MatchActionRequest, ManualMatchRequest
from schemas.photo import PhotoResponse

router = APIRouter()


def _verify_event_owner(db: Session, event_id: Any, user_id: Any) -> Event:
    event = (
        db.query(Event)
        .filter(Event.id == event_id, Event.created_by == user_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/events/{event_id}/matches", response_model=List[MatchResponse])
def list_event_matches(
    event_id: UUID,
    decision: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    guest_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_event_owner(db, event_id, current_user.id)

    query = db.query(Match).filter(Match.event_id == event_id)

    if decision:
        query = query.filter(Match.decision == decision)
    if status:
        query = query.filter(Match.status == status)
    if guest_id:
        query = query.filter(Match.guest_id == guest_id)

    query = query.order_by(Match.similarity.desc())
    return query.offset(skip).limit(limit).all()


@router.patch("/matches/{match_id}", response_model=MatchResponse)
def update_match_action(
    match_id: UUID,
    action_in: MatchActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    match_rec: Any = db.query(Match).filter(Match.id == match_id).first()
    if not match_rec:
        raise HTTPException(status_code=404, detail="Match not found")

    _verify_event_owner(db, match_rec.event_id, current_user.id)

    action = action_in.action.lower()
    if action == "confirm":
        match_rec.decision = "auto_confirmed"
        match_rec.status = "active"
    elif action == "reject":
        match_rec.status = "rejected_by_organizer"
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'confirm' or 'reject'.")

    match_rec.reviewed_by = current_user.id
    match_rec.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(match_rec)
    return match_rec


@router.post("/matches", response_model=MatchResponse, status_code=200)
def manual_assign_match(
    req: ManualMatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    face: Any = db.query(PhotoFace).filter(PhotoFace.id == req.photo_face_id).first()
    if not face:
        raise HTTPException(status_code=404, detail="Photo face not found")

    _verify_event_owner(db, face.event_id, current_user.id)

    guest: Any = db.query(Guest).filter(Guest.id == req.guest_id, Guest.event_id == face.event_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found in this event")

    match_rec: Any = db.query(Match).filter(Match.photo_face_id == req.photo_face_id).first()
    if not match_rec:
        match_rec = Match(
            photo_face_id=req.photo_face_id,
            event_id=face.event_id,
            photo_id=face.photo_id,
        )

    match_rec.guest_id = req.guest_id
    match_rec.similarity = 1.0  # Manual assignment
    match_rec.threshold_used = 0.0
    match_rec.decision = "auto_confirmed"
    match_rec.status = "manually_added"
    match_rec.reviewed_by = current_user.id
    match_rec.reviewed_at = datetime.now(timezone.utc)

    db.add(match_rec)
    db.commit()
    db.refresh(match_rec)
    return match_rec


@router.get("/photo-faces/{photo_face_id}/candidates")
def get_face_candidates(
    photo_face_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    face: Any = db.query(PhotoFace).filter(PhotoFace.id == photo_face_id).first()
    if not face:
        raise HTTPException(status_code=404, detail="Photo face not found")

    _verify_event_owner(db, face.event_id, current_user.id)

    match_rec: Any = db.query(Match).filter(Match.photo_face_id == photo_face_id).first()
    candidates = match_rec.top_candidates if match_rec and match_rec.top_candidates else []

    # Enrich candidates with guest names
    enriched = []
    for cand in candidates:
        g_id = cand.get("guest_id")
        guest: Any = db.query(Guest).filter(Guest.id == UUID(g_id)).first() if g_id else None
        enriched.append({
            "guest_id": g_id,
            "guest_name": f"{guest.first_name} {guest.last_name}" if guest else "Unknown",
            "score": cand.get("score"),
            "rank": cand.get("rank"),
        })

    return {
        "photo_face_id": photo_face_id,
        "match": MatchResponse.model_validate(match_rec) if match_rec else None,
        "candidates": enriched,
    }


@router.get("/guests/{guest_id}/photos", response_model=List[PhotoResponse])
def get_guest_matched_photos(
    guest_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    guest: Any = db.query(Guest).filter(Guest.id == guest_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")

    _verify_event_owner(db, guest.event_id, current_user.id)

    # Query confirmed matches
    matches = (
        db.query(Match)
        .filter(
            Match.guest_id == guest_id,
            Match.status.in_(["active", "manually_added"]),
            Match.decision == "auto_confirmed",
        )
        .order_by(Match.similarity.desc())
        .all()
    )

    photo_ids = [m.photo_id for m in matches]
    if not photo_ids:
        return []

    photos = db.query(Photo).filter(Photo.id.in_(photo_ids)).all()
    return [PhotoResponse.model_validate(p) for p in photos]
