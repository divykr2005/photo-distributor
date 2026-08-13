from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from models.event import Event
from models.guest import Guest
from models.notification_log import NotificationLog, NotificationStatus
from models.user import User
from schemas.notification import (
    NotificationDispatchOptions,
    NotificationLogItem,
    NotificationPreviewResponse,
    NotificationStatusResponse,
    NotificationStatusSummary,
    NotificationTestRequest,
)
from services.notifier import get_notifier, render_email_template
from workers.notifications import run_event_notification_dispatch

router = APIRouter()


@router.get(
    "/events/{event_id}/notifications/preview",
    response_model=NotificationPreviewResponse,
    status_code=status.HTTP_200_OK,
)
def preview_notifications(
    event_id: UUID,
    channel: str = Query("console"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dry-run preview of notification recipients and rendered sample message.
    """
    event = db.query(Event).filter(Event.id == event_id, Event.created_by == current_user.id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    result = run_event_notification_dispatch(db, str(event_id), channel=channel, dry_run=True)
    return NotificationPreviewResponse(**result)


@router.post(
    "/events/{event_id}/notifications/dispatch",
    response_model=NotificationPreviewResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def dispatch_notifications(
    event_id: UUID,
    options: NotificationDispatchOptions,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Initiate batch notification dispatch to all guests with visible photos.
    Idempotent and rate-limited.
    """
    event = db.query(Event).filter(Event.id == event_id, Event.created_by == current_user.id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    result = run_event_notification_dispatch(db, str(event_id), channel=options.channel, dry_run=options.dry_run)
    return NotificationPreviewResponse(**result)


@router.get(
    "/events/{event_id}/notifications/status",
    response_model=NotificationStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_notification_status(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get live send-status summary counts and recent notification log records for an event.
    """
    event = db.query(Event).filter(Event.id == event_id, Event.created_by == current_user.id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    logs = (
        db.query(NotificationLog)
        .filter(NotificationLog.event_id == event_id)
        .order_by(NotificationLog.created_at.desc())
        .limit(100)
        .all()
    )

    summary = NotificationStatusSummary()
    summary.total = len(logs)

    for log in logs:
        st = log.status
        if st == NotificationStatus.QUEUED.value:
            summary.queued += 1
        elif st == NotificationStatus.SENDING.value:
            summary.sending += 1
        elif st == NotificationStatus.SENT.value:
            summary.sent += 1
        elif st == NotificationStatus.DELIVERED.value:
            summary.delivered += 1
        elif st == NotificationStatus.FAILED.value:
            summary.failed += 1
        elif st == NotificationStatus.SKIPPED_OPT_OUT.value:
            summary.skipped_opt_out += 1
        elif st == NotificationStatus.SKIPPED_DUPLICATE.value:
            summary.skipped_duplicate += 1

    return NotificationStatusResponse(
        summary=summary,
        logs=[NotificationLogItem.model_validate(l) for l in logs],
    )


@router.post(
    "/events/{event_id}/notifications/test",
    status_code=status.HTTP_200_OK,
)
def send_test_notification(
    event_id: UUID,
    payload: NotificationTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a single test notification to organizer's test address/number before batch dispatch.
    """
    event = db.query(Event).filter(Event.id == event_id, Event.created_by == current_user.id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    subject, text_body, html_body = render_email_template(
        guest_name=current_user.name or "Organizer",
        event_title=event.title,
        photo_count=12,
        magic_link="http://localhost:3000/g/test_token_preview",
        opt_out_link="http://localhost:3000/api/v1/public/opt-out?guest_id=test",
    )

    notifier = get_notifier(payload.channel)
    res = notifier.send(
        recipient=payload.recipient,
        subject=subject,
        body_text=text_body,
        body_html=html_body,
    )

    if not res.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Test notification failed via {res.provider}: {res.error}",
        )

    return {
        "status": "success",
        "provider": res.provider,
        "provider_message_id": res.provider_message_id,
        "message": f"Test notification sent successfully to {payload.recipient}",
    }


# Public opt-out router
public_opt_out_router = APIRouter()


@public_opt_out_router.get(
    "/public/opt-out",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
)
def guest_opt_out(
    guest_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Public opt-out link endpoint allowing guests to unsubscribe from event notifications.
    """
    guest = db.query(Guest).filter(Guest.id == guest_id).first()
    if not guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest record not found")

    guest.notify_opt_out_at = datetime.now(timezone.utc)
    db.commit()

    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Opt-Out Confirmed</title>
</head>
<body style="font-family: system-ui, sans-serif; background-color: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0;">
    <div style="background-color: #1e293b; padding: 32px; border-radius: 16px; border: 1px solid #334155; text-align: center; max-width: 400px;">
        <h2 style="color: #c084fc; margin-top: 0;">Unsubscribed</h2>
        <p style="color: #94a3b8; font-size: 15px;">You have successfully opted out of further notifications for this event.</p>
    </div>
</body>
</html>"""
