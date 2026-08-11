from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from models.event_photo import EventPhoto


class EventPhotoRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        event_id: UUID,
        uploaded_by: UUID,
        file_path: str,
        file_size: int,
    ) -> EventPhoto:
        record = EventPhoto(
            event_id=event_id,
            uploaded_by=uploaded_by,
            file_path=file_path,
            file_size=file_size,
            status="pending",
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_by_id(self, photo_id: UUID) -> EventPhoto | None:
        return self.db.query(EventPhoto).filter(EventPhoto.id == photo_id).first()

    def get_by_event(
        self,
        event_id: UUID,
        status: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[EventPhoto], int]:
        q = self.db.query(EventPhoto).filter(EventPhoto.event_id == event_id)
        if status:
            q = q.filter(EventPhoto.status == status)
        total = q.count()
        photos = q.order_by(EventPhoto.created_at.desc()).offset(skip).limit(limit).all()
        return photos, total

    def update_status(
        self, photo: EventPhoto, status: str, faces_detected: int | None = None
    ) -> EventPhoto:
        photo.status = status
        if faces_detected is not None:
            photo.faces_detected = faces_detected
        self.db.commit()
        self.db.refresh(photo)
        return photo

    def count_by_event(self, event_id: UUID) -> int:
        return (
            self.db.query(EventPhoto)
            .filter(EventPhoto.event_id == event_id)
            .count()
        )

    def count_by_user(self, user_id: UUID) -> int:
        return (
            self.db.query(EventPhoto)
            .filter(EventPhoto.uploaded_by == user_id)
            .count()
        )

    def count_today_by_user(self, user_id: UUID) -> int:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return (
            self.db.query(EventPhoto)
            .filter(
                EventPhoto.uploaded_by == user_id,
                EventPhoto.created_at >= today_start,
            )
            .count()
        )
