from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from models.user import User
from repositories.event_repository import EventRepository

router = APIRouter()


@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event_repo = EventRepository(db)
    # ponytail: guests/today counts added when guest model exists
    return {
        "total_events": event_repo.count(current_user.id),
        "total_guests": 0,
        "registered_today": 0,
    }
