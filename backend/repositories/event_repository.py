from uuid import UUID

from sqlalchemy.orm import Session

from models.event import Event
from schemas.event import EventCreate, EventUpdate


class EventRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, event_in: EventCreate, user_id: UUID) -> Event:
        db_event = Event(
            title=event_in.title,
            description=event_in.description,
            location=event_in.location,
            date=event_in.date,
            created_by=user_id,
        )
        self.db.add(db_event)
        self.db.commit()
        self.db.refresh(db_event)
        return db_event

    def get_by_id(self, event_id: UUID, user_id: UUID) -> Event | None:
        return (
            self.db.query(Event)
            .filter(Event.id == event_id, Event.created_by == user_id)
            .first()
        )

    def get_all(self, user_id: UUID) -> list[Event]:
        return (
            self.db.query(Event)
            .filter(Event.created_by == user_id)
            .order_by(Event.date.desc())
            .all()
        )

    def update(self, event: Event, event_in: EventUpdate) -> Event:
        update_data = event_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(event, field, value)
        self.db.commit()
        self.db.refresh(event)
        return event

    def delete(self, event: Event) -> None:
        self.db.delete(event)
        self.db.commit()

    def count(self, user_id: UUID) -> int:
        return (
            self.db.query(Event)
            .filter(Event.created_by == user_id)
            .count()
        )
