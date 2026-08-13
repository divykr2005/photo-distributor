import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.celery_app import celery_app
from models.event import Event
from models.guest import Guest
from models.guest_access_token import GuestAccessToken
from models.match import Match
from models.notification_log import NotificationLog, NotificationStatus
from models.photo import Photo
from models.photo_face import PhotoFace
from models.user import User
from workers.notifications import is_in_quiet_hours, run_event_notification_dispatch

# Enable eager execution for Celery tasks in unit tests
celery_app.conf.task_always_eager = True
celery_app.conf.task_eager_propagates = True


def setup_notification_fixtures(db: Session):
    """Set up test user, event, guests, photos, and matches for Day 19 tests."""
    user = User(
        email=f"organizer_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="fakehash",
        name="Organizer",
    )
    db.add(user)
    db.flush()

    event = Event(
        title="Gala Night 2026",
        date=datetime.now(timezone.utc),
        created_by=user.id,
        timezone="UTC",
    )
    db.add(event)
    db.flush()

    # Guest 1: Active guest with 1 photo
    guest1 = Guest(event_id=event.id, first_name="Alice", last_name="Smith", phone="+15550001", email="alice@example.com")
    # Guest 2: Active guest with 1 photo
    guest2 = Guest(event_id=event.id, first_name="Bob", last_name="Jones", phone="+15550002", email="bob@example.com")
    # Guest 3: Guest with 0 photos
    guest3 = Guest(event_id=event.id, first_name="Charlie", last_name="Brown", phone="+15550003", email="charlie@example.com")
    # Guest 4: Guest who has opted out
    guest4 = Guest(
        event_id=event.id,
        first_name="Diana",
        last_name="Prince",
        phone="+15550004",
        email="diana@example.com",
        notify_opt_out_at=datetime.now(timezone.utc),
    )
    db.add_all([guest1, guest2, guest3, guest4])
    db.flush()

    # Photo & Match for Guest 1 and Guest 2
    photo1 = Photo(
        event_id=event.id,
        uploaded_by=user.id,
        original_filename="p1.jpg",
        storage_key="events/p1.jpg",
        content_hash=uuid.uuid4().hex,
        mime_type="image/jpeg",
        file_size=1000,
        status="processed",
    )
    photo2 = Photo(
        event_id=event.id,
        uploaded_by=user.id,
        original_filename="p2.jpg",
        storage_key="events/p2.jpg",
        content_hash=uuid.uuid4().hex,
        mime_type="image/jpeg",
        file_size=1000,
        status="processed",
    )
    db.add_all([photo1, photo2])
    db.flush()

    face1 = PhotoFace(photo_id=photo1.id, event_id=event.id, bbox_x=0, bbox_y=0, bbox_w=10, bbox_h=10, det_score=0.9, embedding=[0.1]*512)
    face2 = PhotoFace(photo_id=photo2.id, event_id=event.id, bbox_x=0, bbox_y=0, bbox_w=10, bbox_h=10, det_score=0.9, embedding=[0.1]*512)
    db.add_all([face1, face2])
    db.flush()

    match1 = Match(event_id=event.id, photo_id=photo1.id, photo_face_id=face1.id, guest_id=guest1.id, similarity=0.9, threshold_used=0.45, status="active", decision="auto_confirmed")
    match2 = Match(event_id=event.id, photo_id=photo2.id, photo_face_id=face2.id, guest_id=guest2.id, similarity=0.9, threshold_used=0.45, status="active", decision="auto_confirmed")
    db.add_all([match1, match2])
    db.commit()

    return {
        "user": user,
        "event": event,
        "guest1": guest1,
        "guest2": guest2,
        "guest3": guest3,
        "guest4": guest4,
        "photo1": photo1,
        "photo2": photo2,
    }


def test_quiet_hours_calculation():
    """Verify quiet hours check logic (21:00 to 08:00 local time)."""
    # 22:00 UTC (10 PM) -> Should be in quiet hours
    dt_night = datetime(2026, 8, 13, 22, 0, 0, tzinfo=timezone.utc)
    in_quiet, next_available = is_in_quiet_hours(dt_night, "UTC")
    assert in_quiet is True
    assert next_available is not None
    assert next_available.hour == 8
    assert next_available.day == 14  # Next day 8 AM

    # 14:00 UTC (2 PM) -> Should NOT be in quiet hours
    dt_day = datetime(2026, 8, 13, 14, 0, 0, tzinfo=timezone.utc)
    in_quiet, next_available = is_in_quiet_hours(dt_day, "UTC")
    assert in_quiet is False
    assert next_available is None


def test_notification_dry_run(db_session: Session):
    """Verify dry-run calculates correct recipient counts without dispatching."""
    fx = setup_notification_fixtures(db_session)
    res = run_event_notification_dispatch(db_session, str(fx["event"].id), channel="console", dry_run=True)

    assert res["total_guests"] == 4
    assert res["eligible_recipients"] == 2  # Guest 1 & Guest 2
    assert res["skipped_zero_photos"] == 1  # Guest 3
    assert res["skipped_opt_out"] == 1    # Guest 4
    assert res["dispatched_count"] == 0
    assert "Your photos from Gala Night 2026" in res["sample_subject"]


def test_notification_dispatch_and_idempotency(db_session: Session):
    """Verify notification dispatch creates log rows and re-run is 100% idempotent."""
    fx = setup_notification_fixtures(db_session)
    event_id = str(fx["event"].id)

    # 1. Run actual dispatch synchronously
    res1 = run_event_notification_dispatch(db_session, event_id, channel="console", dry_run=False)
    assert res1["eligible_recipients"] == 2

    # Verify log records created for Guest 1 & Guest 2
    logs = db_session.query(NotificationLog).filter(NotificationLog.event_id == fx["event"].id).all()
    assert len(logs) == 2
    for l in logs:
        assert l.status == NotificationStatus.SENT.value
        assert l.channel == "console"

    # 2. Re-run dispatch -> Should skip 100% of eligible guests as duplicates
    res2 = run_event_notification_dispatch(db_session, event_id, channel="console", dry_run=False)
    assert res2["eligible_recipients"] == 0
    assert res2["skipped_duplicate"] == 2


def test_public_opt_out_endpoint(client: TestClient, db_session: Session):
    """Verify public opt-out endpoint sets notify_opt_out_at timestamp."""
    fx = setup_notification_fixtures(db_session)
    guest_id = str(fx["guest1"].id)

    resp = client.get(f"/api/v1/public/opt-out?guest_id={guest_id}")
    assert resp.status_code == 200
    assert "Unsubscribed" in resp.text

    # Verify database record
    db_session.refresh(fx["guest1"])
    assert fx["guest1"].notify_opt_out_at is not None


def test_api_notification_endpoints(client: TestClient, db_session: Session):
    """Verify API endpoints: preview, dispatch, status, and test message."""
    fx = setup_notification_fixtures(db_session)
    event_id = str(fx["event"].id)

    # Get JWT auth token for organizer
    from core.security import create_access_token
    token = create_access_token(data={"sub": str(fx["user"].id)})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Preview endpoint
    r_prev = client.get(f"/api/v1/events/{event_id}/notifications/preview?channel=console", headers=headers)
    assert r_prev.status_code == 200
    p_data = r_prev.json()
    assert p_data["total_guests"] == 4
    assert p_data["eligible_recipients"] == 2

    # 2. Test send endpoint
    r_test = client.post(
        f"/api/v1/events/{event_id}/notifications/test",
        headers=headers,
        json={"channel": "console", "recipient": "organizer@example.com"},
    )
    assert r_test.status_code == 200
    assert r_test.json()["status"] == "success"

    # 3. Batch dispatch endpoint
    r_disp = client.post(
        f"/api/v1/events/{event_id}/notifications/dispatch",
        headers=headers,
        json={"channel": "console", "dry_run": False},
    )
    assert r_disp.status_code == 202

    # 4. Status endpoint
    r_stat = client.get(f"/api/v1/events/{event_id}/notifications/status", headers=headers)
    assert r_stat.status_code == 200
    s_data = r_stat.json()
    assert s_data["summary"]["sent"] == 2
    assert s_data["summary"]["total"] == 2
