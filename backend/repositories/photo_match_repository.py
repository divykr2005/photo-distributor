from uuid import UUID

from sqlalchemy.orm import Session

from models.photo_match import PhotoMatch


class PhotoMatchRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        event_photo_id: UUID,
        guest_id: UUID,
        confidence: float,
        face_index: int = 0,
        is_solo: bool = False,
    ) -> PhotoMatch:
        record = PhotoMatch(
            event_photo_id=event_photo_id,
            guest_id=guest_id,
            confidence=confidence,
            face_index=face_index,
            is_solo=is_solo,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def create_bulk(self, matches: list[dict]) -> list[PhotoMatch]:
        """Insert multiple match records in one commit."""
        records = [PhotoMatch(**m) for m in matches]
        self.db.add_all(records)
        self.db.commit()
        for r in records:
            self.db.refresh(r)
        return records

    def get_by_photo(self, event_photo_id: UUID) -> list[PhotoMatch]:
        return (
            self.db.query(PhotoMatch)
            .filter(PhotoMatch.event_photo_id == event_photo_id)
            .order_by(PhotoMatch.confidence.desc())
            .all()
        )

    def get_by_guest(self, guest_id: UUID) -> list[PhotoMatch]:
        return (
            self.db.query(PhotoMatch)
            .filter(PhotoMatch.guest_id == guest_id)
            .order_by(PhotoMatch.confidence.desc())
            .all()
        )

    def count_by_user(self, user_id: UUID) -> int:
        """Count all matches across events owned by user."""
        from models.event_photo import EventPhoto
        from models.event import Event

        return (
            self.db.query(PhotoMatch)
            .join(EventPhoto, PhotoMatch.event_photo_id == EventPhoto.id)
            .join(Event, EventPhoto.event_id == Event.id)
            .filter(Event.created_by == user_id)
            .count()
        )

    def count_by_event(self, event_id: UUID) -> int:
        from models.event_photo import EventPhoto

        return (
            self.db.query(PhotoMatch)
            .join(EventPhoto, PhotoMatch.event_photo_id == EventPhoto.id)
            .filter(EventPhoto.event_id == event_id)
            .count()
        )
