import hashlib
import logging
import random
import secrets
from datetime import datetime, time, timedelta, timezone
import zoneinfo

from sqlalchemy.orm import Session

from core.celery_app import celery_app
from core.config import settings
from database.session import SessionLocal
from models.event import Event
from models.guest import Guest
from models.guest_access_token import GuestAccessToken
from models.notification_log import NotificationLog, NotificationChannel, NotificationStatus
from services.notifier import get_notifier, render_email_template
from services.visibility import visible_matches

logger = logging.getLogger(__name__)


def is_in_quiet_hours(dt_utc: datetime, tz_name: str = "UTC") -> tuple[bool, datetime | None]:
    """
    Check if dt_utc falls in quiet hours (21:00 - 08:00) in local timezone.
    Returns (is_quiet, next_available_utc_time).
    """
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc

    local_dt = dt_utc.astimezone(tz)
    hour = local_dt.hour

    if hour >= 21 or hour < 8:
        if hour >= 21:
            target_date = local_dt.date() + timedelta(days=1)
        else:
            target_date = local_dt.date()

        target_local = datetime.combine(target_date, time(8, 0, 0), tzinfo=tz)
        target_utc = target_local.astimezone(timezone.utc)
        return True, target_utc

    return False, None


def _get_or_create_magic_token(db: Session, guest: Guest) -> tuple[str, str]:
    """Ensure guest has an active GuestAccessToken, returns (token_prefix, raw_token)."""
    token_record = (
        db.query(GuestAccessToken)
        .filter(
            GuestAccessToken.guest_id == guest.id,
            GuestAccessToken.revoked_at.is_(None),
            GuestAccessToken.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )

    if token_record:
        return token_record.token_prefix, token_record.token_prefix

    # Generate new token
    raw_token = secrets.token_urlsafe(16)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=90)

    token_record = GuestAccessToken(
        guest_id=guest.id,
        event_id=guest.event_id,
        token_hash=token_hash,
        token_prefix=raw_token[:6],
        expires_at=expires_at,
    )
    db.add(token_record)
    db.commit()
    return token_record.token_prefix, raw_token


@celery_app.task(name="workers.notifications.dispatch_guest_notification")
def dispatch_guest_notification(
    guest_id: str,
    channel: str = "console",
    notification_type: str = "magic_link",
    force: bool = False,
) -> dict:
    """
    Celery task to dispatch a notification to a single guest.
    Honors opt-out, zero-photos filter, idempotency, quiet hours, and retries.
    """
    db: Session = SessionLocal()
    try:
        guest = db.query(Guest).filter(Guest.id == guest_id).first()
        if not guest:
            return {"status": "error", "message": f"Guest {guest_id} not found"}

        event = db.query(Event).filter(Event.id == guest.event_id).first()
        if not event:
            return {"status": "error", "message": f"Event {guest.event_id} not found"}

        # 1. Opt-out check (D28)
        if guest.notify_opt_out_at and not force:
            logger.info(f"[NOTIFY] Guest {guest_id} has opted out. Skipping.")
            log = NotificationLog(
                guest_id=guest.id,
                event_id=event.id,
                channel=channel,
                notification_type=notification_type,
                dedupe_key=f"opt_out_{guest_id}",
                status=NotificationStatus.SKIPPED_OPT_OUT.value,
                error="Guest opted out at dispatch time",
            )
            db.add(log)
            db.commit()
            return {"status": NotificationStatus.SKIPPED_OPT_OUT.value}

        # 2. Count visible photos
        matches = visible_matches(db, guest.id).all()
        photo_count = len(matches)
        if photo_count == 0 and not force:
            logger.info(f"[NOTIFY] Guest {guest_id} has 0 visible photos. Skipping.")
            return {"status": "skipped_zero_photos"}

        # 3. Resolve access token
        prefix, raw_token = _get_or_create_magic_token(db, guest)

        # 4. Dedupe key & Idempotency check (D27)
        dedupe_key = f"{prefix}_cnt{photo_count}"
        existing_log = (
            db.query(NotificationLog)
            .filter(
                NotificationLog.guest_id == guest.id,
                NotificationLog.channel == channel,
                NotificationLog.notification_type == notification_type,
                NotificationLog.dedupe_key == dedupe_key,
            )
            .first()
        )

        if existing_log and existing_log.status in [
            NotificationStatus.SENT.value,
            NotificationStatus.DELIVERED.value,
            NotificationStatus.SKIPPED_DUPLICATE.value,
        ] and not force:
            logger.info(f"[NOTIFY] Duplicate notification for guest {guest_id} (key: {dedupe_key}). Skipping.")
            return {"status": NotificationStatus.SKIPPED_DUPLICATE.value}

        if not existing_log:
            existing_log = NotificationLog(
                guest_id=guest.id,
                event_id=event.id,
                channel=channel,
                notification_type=notification_type,
                dedupe_key=dedupe_key,
                status=NotificationStatus.QUEUED.value,
            )
            db.add(existing_log)
            db.flush()

        # 5. Quiet hours check (D28)
        now_utc = datetime.now(timezone.utc)
        in_quiet, next_available_utc = is_in_quiet_hours(now_utc, event.timezone or "UTC")
        if in_quiet and next_available_utc and not force:
            logger.info(f"[NOTIFY] Quiet hours active for event {event.id} ({event.timezone}). Rescheduling for {next_available_utc}.")
            existing_log.status = NotificationStatus.QUEUED.value
            existing_log.next_retry_at = next_available_utc
            db.commit()

            dispatch_guest_notification.apply_async(
                args=[guest_id, channel, notification_type, force],
                eta=next_available_utc,
            )
            return {"status": "rescheduled_quiet_hours", "eta": next_available_utc.isoformat()}

        # 6. Render templates & Dispatch
        app_url = getattr(settings, "APP_URL", "http://localhost:3000")
        magic_link = f"{app_url}/g/{raw_token}"
        opt_out_link = f"{app_url}/api/v1/public/opt-out?guest_id={guest.id}"
        recipient = guest.email if channel == "smtp" else (guest.phone or guest.email or "console")

        subject, text_body, html_body = render_email_template(
            guest_name=guest.first_name,
            event_title=event.title,
            photo_count=photo_count,
            magic_link=magic_link,
            opt_out_link=opt_out_link,
        )

        notifier = get_notifier(channel)
        existing_log.status = NotificationStatus.SENDING.value
        db.commit()

        res = notifier.send(
            recipient=recipient,
            subject=subject,
            body_text=text_body,
            body_html=html_body,
        )

        # 7. Update log result
        if res.success:
            existing_log.status = NotificationStatus.SENT.value
            existing_log.provider = res.provider
            existing_log.provider_message_id = res.provider_message_id
            existing_log.sent_at = datetime.now(timezone.utc)
            existing_log.error = None
            guest.last_notified_at = datetime.now(timezone.utc)
            db.commit()
            return {"status": NotificationStatus.SENT.value, "provider_message_id": res.provider_message_id}
        else:
            existing_log.attempts += 1
            existing_log.error = res.error
            existing_log.provider = res.provider

            if res.is_transient and existing_log.attempts < 5:
                backoff_sec = 60 * (2 ** existing_log.attempts) + random.randint(1, 10)
                next_retry = datetime.now(timezone.utc) + timedelta(seconds=backoff_sec)
                existing_log.status = NotificationStatus.QUEUED.value
                existing_log.next_retry_at = next_retry
                db.commit()

                dispatch_guest_notification.apply_async(
                    args=[guest_id, channel, notification_type, force],
                    countdown=backoff_sec,
                )
                return {"status": "retry_queued", "attempts": existing_log.attempts, "error": res.error}
            else:
                existing_log.status = NotificationStatus.FAILED.value
                db.commit()
                return {"status": NotificationStatus.FAILED.value, "error": res.error}

    finally:
        db.close()


def run_event_notification_dispatch(
    db: Session,
    event_id: str,
    channel: str = "console",
    dry_run: bool = False,
) -> dict:
    """
    Batch helper for event notifications.
    Supports dry-run preview and actual queueing.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError(f"Event {event_id} not found")

    db.commit()

    guests = db.query(Guest).filter(Guest.event_id == event.id).all()
    total_guests = len(guests)

    eligible_recipients = 0
    skipped_zero_photos = 0
    skipped_opt_out = 0
    skipped_duplicate = 0

    dispatched_task_ids = []

    for guest in guests:
        # Check opt-out
        if guest.notify_opt_out_at:
            skipped_opt_out += 1
            continue

        # Check photos
        photo_count = visible_matches(db, guest.id).count()
        if photo_count == 0:
            skipped_zero_photos += 1
            continue

        # Check dedupe
        prefix, raw_token = _get_or_create_magic_token(db, guest)
        dedupe_key = f"{prefix}_cnt{photo_count}"

        existing_log = (
            db.query(NotificationLog)
            .filter(
                NotificationLog.guest_id == guest.id,
                NotificationLog.channel == channel,
                NotificationLog.dedupe_key == dedupe_key,
                NotificationLog.status.in_([
                    NotificationStatus.SENT.value,
                    NotificationStatus.DELIVERED.value,
                    NotificationStatus.SKIPPED_DUPLICATE.value,
                ]),
            )
            .first()
        )

        if existing_log:
            logger.info(f"[DEBUG DEDUPE] Found existing log for guest {guest.id}: {existing_log.status} (key: {dedupe_key})")
            skipped_duplicate += 1
            continue
        else:
            logger.info(f"[DEBUG DEDUPE] No existing log for guest {guest.id} (key: {dedupe_key})")

        eligible_recipients += 1

        if not dry_run:
            task = dispatch_guest_notification.delay(str(guest.id), channel, "magic_link")
            dispatched_task_ids.append(task.id)

    # Render sample for preview
    sample_guest = next((g for g in guests if visible_matches(db, g.id).count() > 0), guests[0] if guests else None)
    sample_name = sample_guest.first_name if sample_guest else "Guest"
    _, sample_token = _get_or_create_magic_token(db, sample_guest) if sample_guest else ("", "sample_token")
    app_url = getattr(settings, "APP_URL", "http://localhost:3000")
    sample_link = f"{app_url}/g/{sample_token}"
    sample_opt_out = f"{app_url}/api/v1/public/opt-out?guest_id={sample_guest.id if sample_guest else 'id'}"

    sample_subject, sample_text, sample_html = render_email_template(
        guest_name=sample_name,
        event_title=event.title,
        photo_count=5,
        magic_link=sample_link,
        opt_out_link=sample_opt_out,
    )

    return {
        "total_guests": total_guests,
        "eligible_recipients": eligible_recipients,
        "skipped_zero_photos": skipped_zero_photos,
        "skipped_opt_out": skipped_opt_out,
        "skipped_duplicate": skipped_duplicate,
        "dispatched_count": len(dispatched_task_ids),
        "dispatched_task_ids": dispatched_task_ids,
        "sample_subject": sample_subject,
        "sample_text_body": sample_text,
        "sample_html_body": sample_html,
    }
