from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from models.guest import Guest
from schemas.guest import GuestCreate, GuestUpdate


class GuestRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, guest_in: GuestCreate) -> Guest:
        db_guest = Guest(
            event_id=guest_in.event_id,
            first_name=guest_in.first_name,
            last_name=guest_in.last_name,
            phone=guest_in.phone,
            email=guest_in.email,
            gender=guest_in.gender,
            notes=guest_in.notes,
            consent_given_at=datetime.now(timezone.utc),
        )
        self.db.add(db_guest)
        self.db.commit()
        self.db.refresh(db_guest)
        return db_guest

    def get_by_id(self, guest_id: UUID) -> Guest | None:
        return self.db.query(Guest).filter(Guest.id == guest_id).first()

    def get_all_by_event(self, event_id: UUID) -> list[Guest]:
        return (
            self.db.query(Guest)
            .filter(Guest.event_id == event_id)
            .order_by(Guest.created_at.desc())
            .all()
        )

    def get_all_by_user(self, user_id: UUID) -> list[Guest]:
        """Get all guests across all events owned by user."""
        from models.event import Event

        return (
            self.db.query(Guest)
            .join(Event, Guest.event_id == Event.id)
            .filter(Event.created_by == user_id)
            .order_by(Guest.created_at.desc())
            .all()
        )

    def search(
        self, user_id: UUID, query: str | None = None, event_id: UUID | None = None
    ) -> list[Guest]:
        from models.event import Event

        q = (
            self.db.query(Guest)
            .join(Event, Guest.event_id == Event.id)
            .filter(Event.created_by == user_id)
        )
        if event_id:
            q = q.filter(Guest.event_id == event_id)
        if query:
            like = f"%{query}%"
            q = q.filter(
                (Guest.first_name.ilike(like))
                | (Guest.last_name.ilike(like))
                | (Guest.phone.ilike(like))
                | (Guest.email.ilike(like))
            )
        return q.order_by(Guest.created_at.desc()).all()

    def update(self, guest: Guest, guest_in: GuestUpdate) -> Guest:
        update_data = guest_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(guest, field, value)
        self.db.commit()
        self.db.refresh(guest)
        return guest

    def update_image(self, guest: Guest, image_path: str) -> Guest:
        guest.image_path = image_path
        self.db.commit()
        self.db.refresh(guest)
        return guest

    def delete(self, guest: Guest) -> None:
        self.db.delete(guest)
        self.db.commit()

    def count_by_user(self, user_id: UUID) -> int:
        from models.event import Event

        return (
            self.db.query(Guest)
            .join(Event, Guest.event_id == Event.id)
            .filter(Event.created_by == user_id)
            .count()
        )

    def count_today_by_user(self, user_id: UUID) -> int:
        from models.event import Event

        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return (
            self.db.query(Guest)
            .join(Event, Guest.event_id == Event.id)
            .filter(Event.created_by == user_id, Guest.created_at >= today_start)
            .count()
        )
