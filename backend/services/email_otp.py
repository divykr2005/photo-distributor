"""Short-lived email OTP state backed by Redis.

No OTP, email address, or verification token is written to the database or logs.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from uuid import UUID

import redis

from core.config import get_redis_url, settings


OTP_TTL_SECONDS = 600
VERIFICATION_TTL_SECONDS = 900
RESEND_COOLDOWN_SECONDS = 60
MAX_SENDS_PER_HOUR = 6
MAX_VERIFY_ATTEMPTS = 5


class EmailOtpError(Exception):
    pass


class EmailOtpRateLimited(EmailOtpError):
    pass


class EmailOtpInvalid(EmailOtpError):
    pass


@dataclass(frozen=True)
class VerifiedEmail:
    event_id: str
    email: str


def _redis() -> redis.Redis:
    return redis.Redis.from_url(get_redis_url(), socket_timeout=2.0, decode_responses=True)


def _identity(event_id: UUID | str, email: str) -> str:
    normalized = email.strip().lower()
    value = f"{event_id}:{normalized}".encode()
    return hmac.new(settings.JWT_SECRET.encode(), value, hashlib.sha256).hexdigest()


def _otp_digest(identity: str, code: str) -> str:
    return hmac.new(
        settings.JWT_SECRET.encode(), f"{identity}:{code}".encode(), hashlib.sha256
    ).hexdigest()


def issue_otp(event_id: UUID, email: str) -> str:
    """Create an OTP, enforcing cooldown and rolling hourly send limits."""
    client = _redis()
    identity = _identity(event_id, email)
    cooldown_key = f"email-otp:cooldown:{identity}"
    hourly_key = f"email-otp:hourly:{identity}"

    if not client.set(cooldown_key, "1", ex=RESEND_COOLDOWN_SECONDS, nx=True):
        raise EmailOtpRateLimited("Please wait before requesting another code.")

    sends = client.incr(hourly_key)
    if sends == 1:
        client.expire(hourly_key, 3600)
    if sends > MAX_SENDS_PER_HOUR:
        client.delete(cooldown_key)
        raise EmailOtpRateLimited("Too many codes requested. Please try again later.")

    code = f"{secrets.randbelow(1_000_000):06d}"
    payload = json.dumps({"digest": _otp_digest(identity, code), "attempts": 0})
    client.setex(f"email-otp:code:{identity}", OTP_TTL_SECONDS, payload)
    return code


def revoke_otp(event_id: UUID, email: str) -> None:
    """Remove a code and cooldown after a delivery failure so retry remains possible."""
    client = _redis()
    identity = _identity(event_id, email)
    client.delete(f"email-otp:code:{identity}", f"email-otp:cooldown:{identity}")


def verify_otp(event_id: UUID, email: str, code: str) -> str:
    client = _redis()
    identity = _identity(event_id, email)
    key = f"email-otp:code:{identity}"
    # Compare, increment the attempt counter and consume a correct code in one
    # Redis operation so parallel requests cannot verify the same OTP twice.
    result = int(
        client.eval(
            """
            local raw = redis.call('GET', KEYS[1])
            if not raw then return 0 end
            local data = cjson.decode(raw)
            data.attempts = (tonumber(data.attempts) or 0) + 1
            if data.attempts > tonumber(ARGV[2]) then
                redis.call('DEL', KEYS[1])
                return -1
            end
            if data.digest ~= ARGV[1] then
                local ttl = redis.call('PTTL', KEYS[1])
                if ttl > 0 then redis.call('SET', KEYS[1], cjson.encode(data), 'PX', ttl) end
                return -2
            end
            redis.call('DEL', KEYS[1])
            return 1
            """,
            1,
            key,
            _otp_digest(identity, code),
            MAX_VERIFY_ATTEMPTS,
        )
    )
    if result == -1:
        raise EmailOtpInvalid("Too many incorrect attempts. Request a new code.")
    if result != 1:
        raise EmailOtpInvalid("The code is invalid or has expired.")

    token = secrets.token_urlsafe(32)
    client.setex(
        f"email-otp:verified:{token}",
        VERIFICATION_TTL_SECONDS,
        json.dumps({"event_id": str(event_id), "email": email.strip().lower()}),
    )
    return token


def consume_verification(token: str, event_id: UUID, email: str) -> VerifiedEmail:
    """Atomically consume a one-time verification token bound to event and email."""
    raw = _redis().getdel(f"email-otp:verified:{token}")
    if not raw:
        raise EmailOtpInvalid("Email verification expired. Please verify your email again.")
    data = json.loads(raw)
    expected_email = email.strip().lower()
    if data.get("event_id") != str(event_id) or data.get("email") != expected_email:
        raise EmailOtpInvalid("Email verification does not match this registration.")
    return VerifiedEmail(event_id=str(event_id), email=expected_email)
