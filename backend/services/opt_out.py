from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt

from core.config import settings


OPT_OUT_PURPOSE = "notification_opt_out"


def create_opt_out_token(guest_id: UUID, expires_days: int = 180) -> str:
    """Create a signed, scoped token for a notification opt-out link."""
    payload = {
        "sub": str(guest_id),
        "purpose": OPT_OUT_PURPOSE,
        "exp": datetime.now(timezone.utc) + timedelta(days=expires_days),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.ALGORITHM)


def decode_opt_out_token(token: str) -> UUID:
    """Validate an opt-out token and return its guest identifier."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
        if payload.get("purpose") != OPT_OUT_PURPOSE:
            raise ValueError("Invalid token purpose")
        return UUID(payload["sub"])
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid or expired opt-out token") from exc
