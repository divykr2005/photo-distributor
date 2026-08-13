from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class NotificationDispatchOptions(BaseModel):
    channel: str = "console"
    dry_run: bool = False


class NotificationTestRequest(BaseModel):
    channel: str = "console"
    recipient: str


class NotificationPreviewResponse(BaseModel):
    total_guests: int
    eligible_recipients: int
    skipped_zero_photos: int
    skipped_opt_out: int
    skipped_duplicate: int
    sample_subject: str
    sample_text_body: str
    sample_html_body: Optional[str] = None


class NotificationStatusSummary(BaseModel):
    queued: int = 0
    sending: int = 0
    sent: int = 0
    delivered: int = 0
    failed: int = 0
    skipped_opt_out: int = 0
    skipped_duplicate: int = 0
    total: int = 0


class NotificationLogItem(BaseModel):
    id: UUID
    guest_id: UUID
    event_id: UUID
    channel: str
    notification_type: str
    dedupe_key: str
    status: str
    provider: Optional[str] = None
    provider_message_id: Optional[str] = None
    error: Optional[str] = None
    attempts: int
    next_retry_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationStatusResponse(BaseModel):
    summary: NotificationStatusSummary
    logs: List[NotificationLogItem]
