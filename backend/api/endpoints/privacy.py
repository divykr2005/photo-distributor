from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_current_user
from models.user import User
from models.guest import Guest
from models.audit_log import AuditLog
from models.consent import BiometricConsent
from models.match import Match

router = APIRouter()

@router.get("/guests/{guest_id}/dsar-export")
def export_guest_data(
    guest_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Data Subject Access Request (DSAR) Export Endpoint.
    Returns a JSON payload containing all personal and biometric metadata
    associated with a guest, complying with GDPR Article 15 (Right of Access).
    """
    # Verify guest exists and belongs to an event the current user owns
    guest = db.query(Guest).filter(Guest.id == guest_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")

    from models.event import Event
    event = db.query(Event).filter(Event.id == guest.event_id, Event.created_by == current_user.id).first()
    if not event:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Fetch audit logs
    audit_logs = db.query(AuditLog).filter(AuditLog.guest_id == guest_id).order_by(AuditLog.timestamp.desc()).all()

    consents = (
        db.query(BiometricConsent)
        .filter(BiometricConsent.guest_id == guest_id)
        .order_by(BiometricConsent.given_at.desc())
        .all()
    )
    matches = db.query(Match).filter(Match.guest_id == guest_id).all()

    # Construct DSAR Payload
    return {
        "subject_data": {
            "id": str(guest.id),
            "first_name": guest.first_name,
            "last_name": guest.last_name,
            "phone": guest.phone,
            "email": guest.email,
            "gender": guest.gender,
        },
        "consent_records": [
            {
                "consent_text_version": consent.consent_text_version,
                "phone_e164": consent.phone_e164,
                "given_at": consent.given_at,
                "withdrawn_at": consent.withdrawn_at,
                "notice_text_snapshot": consent.notice_text_snapshot,
            }
            for consent in consents
        ],
        "biometric_metadata": {
            "embedding_status": guest.embedding_status,
            "biometrics_purged_at": guest.biometrics_purged_at,
            "retention_policy": "Biometric retention is enforced by the configured maintenance policy.",
        },
        "matches": [
            {
                "photo_id": str(match.photo_id),
                "similarity": match.similarity,
                "decision": match.decision,
                "status": match.status,
                "created_at": match.created_at,
            } for match in matches
        ],
        "audit_trail": [
            {
                "action": log.action,
                "timestamp": log.timestamp
            } for log in audit_logs
        ]
    }
