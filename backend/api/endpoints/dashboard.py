from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from models.user import User
from repositories.event_repository import EventRepository
from repositories.guest_repository import GuestRepository

router = APIRouter()


@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event_repo = EventRepository(db)
    guest_repo = GuestRepository(db)
    return {
        "total_events": event_repo.count(current_user.id),
        "total_guests": guest_repo.count_by_user(current_user.id),
        "registered_today": guest_repo.count_today_by_user(current_user.id),
    }

