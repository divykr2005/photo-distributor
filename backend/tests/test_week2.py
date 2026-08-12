import os
import io
import uuid
import json
import pytest
import numpy as np
from datetime import datetime, timezone
from PIL import Image

from database.session import SessionLocal
from models.user import User
from models.event import Event
from models.guest import Guest
from models.face_embedding import FaceEmbedding
from models.photo import Photo
from models.photo_face import PhotoFace
from models.match import Match
from services.matching_service import MatchingService


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_user_and_event(db_session):
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"user_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="pw",
        name="Test User",
    )
    db_session.add(user)

    event_id = uuid.uuid4()
    event = Event(
        id=event_id,
        title="Test Event",
        date=datetime.now(timezone.utc),
        status="active",
        created_by=user_id,
        match_threshold=0.42,
        review_floor=0.32,
        match_margin=0.05,
    )
    db_session.add(event)
    db_session.commit()
    return user, event


def test_multi_reference_scoring_and_distinct_margin(db_session, sample_user_and_event):
    user, event = sample_user_and_event

    # Guest A with 2 reference embeddings: ref1 = 0.48, ref2 = 0.47
    guest_a = Guest(id=uuid.uuid4(), event_id=event.id, first_name="Alice", last_name="Test", phone="+1234567890", email="a@test.com")
    guest_b = Guest(id=uuid.uuid4(), event_id=event.id, first_name="Bob", last_name="Test", phone="+1234567891", email="b@test.com")
    db_session.add_all([guest_a, guest_b])
    db_session.commit()

    # Synthetic reference vectors with exact target cosine similarity
    v_target = np.random.randn(512).astype(np.float32)
    v_target /= np.linalg.norm(v_target)

    def make_vector_with_similarity(base, sim):
        noise = np.random.randn(512).astype(np.float32)
        noise -= (noise @ base) * base
        noise /= np.linalg.norm(noise)
        vec = sim * base + np.sqrt(1.0 - sim**2) * noise
        return vec / np.linalg.norm(vec)

    v_ref_a1 = make_vector_with_similarity(v_target, 0.48)
    v_ref_a2 = make_vector_with_similarity(v_target, 0.47)
    v_ref_b1 = make_vector_with_similarity(v_target, 0.43)

    db_session.add_all([
        FaceEmbedding(id=uuid.uuid4(), guest_id=guest_a.id, embedding=v_ref_a1.tolist()),
        FaceEmbedding(id=uuid.uuid4(), guest_id=guest_a.id, embedding=v_ref_a2.tolist()),
        FaceEmbedding(id=uuid.uuid4(), guest_id=guest_b.id, embedding=v_ref_b1.tolist()),
    ])
    db_session.commit()

    # Photo & PhotoFace
    photo = Photo(
        id=uuid.uuid4(),
        event_id=event.id,
        uploaded_by=user.id,
        original_filename="test.jpg",
        storage_key=f"events/{event.id}/photos/p1/original.jpg",
        content_hash=uuid.uuid4().hex,
        mime_type="image/jpeg",
        file_size=100,
        status="processed",
    )
    db_session.add(photo)
    db_session.commit()

    pf = PhotoFace(
        id=uuid.uuid4(),
        photo_id=photo.id,
        event_id=event.id,
        bbox_x=0.1, bbox_y=0.1, bbox_w=0.2, bbox_h=0.2,
        det_score=0.95,
        embedding=v_target.tolist(),
        is_matchable=True,
    )
    db_session.add(pf)
    db_session.commit()

    # Run matching engine
    service = MatchingService(db_session)
    result = service.match_pending_faces(str(event.id), force=True, trigger="manual_rerun")

    match_rec = db_session.query(Match).filter(Match.photo_face_id == pf.id).first()
    assert match_rec is not None
    assert match_rec.guest_id == guest_a.id

    # Crucial assertion: Top-2 margin uses distinct guest IDs (Guest A vs Guest B)
    # Margin should be approximately 0.48 - 0.43 = 0.05, NOT 0.48 - 0.47 = 0.01!
    assert match_rec.second_guest_id == guest_b.id
    assert match_rec.margin > 0.02, f"Margin {match_rec.margin} should be between distinct guests (Guest A vs Guest B)"


def test_protected_manual_decisions(db_session, sample_user_and_event):
    user, event = sample_user_and_event

    guest_a = Guest(id=uuid.uuid4(), event_id=event.id, first_name="Alice", last_name="Test", phone="+1234567892", email="a2@test.com")
    guest_b = Guest(id=uuid.uuid4(), event_id=event.id, first_name="Bob", last_name="Test", phone="+1234567893", email="b2@test.com")
    db_session.add_all([guest_a, guest_b])
    db_session.commit()

    photo = Photo(
        id=uuid.uuid4(),
        event_id=event.id,
        uploaded_by=user.id,
        original_filename="test2.jpg",
        storage_key=f"events/{event.id}/photos/p2/original.jpg",
        content_hash=uuid.uuid4().hex,
        mime_type="image/jpeg",
        file_size=100,
        status="processed",
    )
    db_session.add(photo)
    db_session.commit()

    v_vec = np.random.randn(512).astype(np.float32)
    v_vec /= np.linalg.norm(v_vec)

    db_session.add_all([
        FaceEmbedding(id=uuid.uuid4(), guest_id=guest_a.id, embedding=v_vec.tolist()),
        FaceEmbedding(id=uuid.uuid4(), guest_id=guest_b.id, embedding=v_vec.tolist()),
    ])
    db_session.commit()

    pf = PhotoFace(
        id=uuid.uuid4(),
        photo_id=photo.id,
        event_id=event.id,
        bbox_x=0.1, bbox_y=0.1, bbox_w=0.2, bbox_h=0.2,
        det_score=0.95,
        embedding=v_vec.tolist(),
        is_matchable=True,
        matched_at=None,
    )
    db_session.add(pf)
    db_session.commit()

    # Insert manual match decision for Guest B
    match_rec = Match(
        id=uuid.uuid4(),
        event_id=event.id,
        guest_id=guest_b.id,
        photo_id=photo.id,
        photo_face_id=pf.id,
        similarity=0.9,
        threshold_used=0.42,
        decision="auto_confirmed",
        status="manually_added",
        reviewed_by=user.id,
        reviewed_at=datetime.now(timezone.utc),
    )
    db_session.add(match_rec)
    db_session.commit()

    # Re-run matching without force
    service = MatchingService(db_session)
    res = service.match_pending_faces(str(event.id), force=False)

    db_session.refresh(match_rec)
    assert match_rec.guest_id == guest_b.id
    assert match_rec.status == "manually_added"
    assert res.get("protected_rows") == 1
