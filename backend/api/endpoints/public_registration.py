import os
import uuid
from html import escape
from typing import cast, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from sqlalchemy.orm import Session
from pydantic import EmailStr

from datetime import datetime, timezone

from api.dependencies import get_db
from models.event import Event
from models.consent import BiometricConsent
from core.config import settings
from repositories.guest_repository import GuestRepository
from schemas.guest import GuestCreate
from worker.face_processor import FaceQualityError
from middleware.rate_limit import limiter
from schemas.email_otp import EmailOtpRequest, EmailOtpVerified, EmailOtpVerify
from services.email_otp import (
    EmailOtpInvalid,
    EmailOtpRateLimited,
    consume_verification,
    issue_otp,
    revoke_otp,
    verify_otp,
)
from services.notifier import get_notifier

router = APIRouter()

UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "guests"
)


@router.post("/events/{event_id}/email-otp/request", status_code=202)
@limiter.limit("5/minute")
def request_email_otp(
    request: Request,
    event_id: UUID,
    payload: EmailOtpRequest,
    db: Session = Depends(get_db),
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    email = str(payload.email).strip().lower()
    try:
        code = issue_otp(event_id, email)
    except EmailOtpRateLimited as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Email verification is temporarily unavailable.") from exc

    title = str(event.title).replace("\r", " ").replace("\n", " ")
    result = get_notifier("smtp").send(
        recipient=email,
        subject=f"Your verification code for {title}",
        body_text=(
            f"Your SnapTracer verification code is {code}. "
            "It expires in 10 minutes. If you did not request this code, ignore this email."
        ),
        body_html=(
            f"<p>Your verification code for {escape(title)} is:</p>"
            f"<p style=\"font-size:28px;font-weight:700;letter-spacing:6px\">{code}</p>"
            "<p>It expires in 10 minutes. If you did not request this code, ignore this email.</p>"
        ),
    )
    if not result.success:
        revoke_otp(event_id, email)
        raise HTTPException(status_code=503, detail="We could not send the verification email. Please try again.")
    return {"message": "If the address can receive mail, a verification code has been sent."}


@router.post("/events/{event_id}/email-otp/verify", response_model=EmailOtpVerified)
@limiter.limit("10/minute")
def confirm_email_otp(request: Request, event_id: UUID, payload: EmailOtpVerify):
    try:
        token = verify_otp(event_id, str(payload.email), payload.code)
    except EmailOtpInvalid as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Email verification is temporarily unavailable.") from exc
    return EmailOtpVerified(verification_token=token)

@router.get("/events/{event_id}")
def get_public_event_details(
    event_id: UUID,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Returns basic non-sensitive event details for the public registration page.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
        
    return {
        "id": str(event.id),
        "title": str(event.title),
        "date": cast(Any, event.date),
        "biometric_consent_text_version": settings.CURRENT_BIOMETRIC_CONSENT_VERSION,
    }


@router.post("/events/{event_id}/register")
async def public_guest_register(
    event_id: UUID,
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: str = Form(...),
    email: EmailStr = Form(...),
    email_verification_token: str = Form(...),
    gender: str | None = Form(None),
    biometric_consent: bool = Form(False),
    biometric_consent_text_version: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Public endpoint for a guest to register themselves with a selfie.
    Requires a one-time token proving email address ownership.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if not biometric_consent:
        raise HTTPException(status_code=400, detail="Biometric processing consent is required to register.")
    if biometric_consent_text_version != settings.CURRENT_BIOMETRIC_CONSENT_VERSION:
        raise HTTPException(status_code=400, detail="The biometric consent notice is out of date. Please reload and try again.")

    # File validation
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(
            status_code=400, detail="Only JPEG, PNG, or WebP images are accepted."
        )

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be under 10 MB.")

    # Reject before creating a guest or writing anything to persistent storage.
    from services.face_presence import contains_face
    if not contains_face(contents):
        raise HTTPException(
            status_code=422,
            detail="No face detected. Centre your face in the camera and retake the selfie.",
        )

    # Phone normalization to E.164
    import phonenumbers
    try:
        parsed_phone = phonenumbers.parse(phone, "US") # Default region US if no + provided
        if not phonenumbers.is_valid_number(parsed_phone):
            raise ValueError("Invalid phone number")
        formatted_phone = phonenumbers.format_number(parsed_phone, phonenumbers.PhoneNumberFormat.E164)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid phone number format: {str(e)}")

    # Consume only after all cheap validation succeeds, immediately before the
    # first persistent write. The token is one-time and event/email bound.
    try:
        verified = consume_verification(email_verification_token, event_id, str(email))
    except EmailOtpInvalid as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Email verification is temporarily unavailable.") from exc

    # Create the guest record
    repo = GuestRepository(db)
    
    guest_in = GuestCreate(
        event_id=event_id,
        first_name=first_name,
        last_name=last_name,
        phone=formatted_phone,
        email=verified.email,
        gender=gender,
        consent_source=None,
        consent_text_version=None,
        consent_given_at=datetime.now(timezone.utc) if biometric_consent else None,
        biometric_consent_text_version=biometric_consent_text_version if biometric_consent else None,
    )
    guest = repo.create(guest_in)

    consent = BiometricConsent(
        guest_id=guest.id,
        consent_text_version=settings.CURRENT_BIOMETRIC_CONSENT_VERSION,
        phone_e164=formatted_phone,
        given_at=guest.consent_given_at,
        notice_text_snapshot=(
            "I consent to temporary facial-feature processing to find and deliver "
            "my event photos, subject to the published retention policy."
        ),
    )
    db.add(consent)
    db.commit()

    ext = (
        file.filename.rsplit(".", 1)[-1]
        if file.filename and "." in file.filename
        else "jpg"
    )
    filename = f"{uuid.uuid4()}.{ext}"

    # Update image path
    storage_key = f"uploads/guests/{filename}"
    
    from services.storage import get_storage_backend
    storage = get_storage_backend()
    storage.put(storage_key, contents)
    
    guest = repo.update_image(guest, storage_key)

    # Enqueue only after the consent evidence is committed so the worker cannot
    # race the transaction and incorrectly reject a valid registration.
    from worker.tasks import process_guest_registration_photo_task
    process_guest_registration_photo_task.delay(str(guest.id), storage_key)

    # Log biometric consent audit
    from models.audit_log import AuditLog
    audit = AuditLog(
        guest_id=guest.id,
        event_id=event.id,
        action="biometric_consent_granted_via_registration",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(audit)
    db.commit()

    db.refresh(guest)
    
    return {
        "success": True,
        "message": "Registered successfully",
        "guest_id": str(guest.id)
    }
