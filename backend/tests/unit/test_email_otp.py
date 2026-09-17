import fnmatch
import json
from uuid import uuid4

import pytest

from services import email_otp


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.values:
            return False
        self.values[key] = value
        self.ttls[key] = ex
        return True

    def setex(self, key, ttl, value):
        self.values[key] = value
        self.ttls[key] = ttl

    def get(self, key):
        return self.values.get(key)

    def getdel(self, key):
        self.ttls.pop(key, None)
        return self.values.pop(key, None)

    def incr(self, key):
        self.values[key] = int(self.values.get(key, 0)) + 1
        return self.values[key]

    def expire(self, key, ttl):
        self.ttls[key] = ttl

    def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)
            self.ttls.pop(key, None)

    def eval(self, _script, _numkeys, key, supplied_digest, max_attempts):
        raw = self.values.get(key)
        if raw is None:
            return 0
        data = json.loads(raw)
        data["attempts"] = int(data.get("attempts", 0)) + 1
        if data["attempts"] > int(max_attempts):
            self.delete(key)
            return -1
        if data["digest"] != supplied_digest:
            self.values[key] = json.dumps(data)
            return -2
        self.delete(key)
        return 1


@pytest.fixture
def fake_redis(monkeypatch):
    client = FakeRedis()
    monkeypatch.setattr(email_otp, "_redis", lambda: client)
    monkeypatch.setattr(email_otp.secrets, "randbelow", lambda _limit: 123456)
    return client


def test_email_otp_is_event_bound_and_one_time(fake_redis):
    event_id = uuid4()
    code = email_otp.issue_otp(event_id, "Guest@Example.com")
    assert code == "123456"

    token = email_otp.verify_otp(event_id, "guest@example.com", code)
    verified = email_otp.consume_verification(token, event_id, "GUEST@example.com")
    assert verified.email == "guest@example.com"

    with pytest.raises(email_otp.EmailOtpInvalid):
        email_otp.consume_verification(token, event_id, "guest@example.com")


def test_email_otp_rejects_other_event_and_limits_attempts(fake_redis):
    event_id = uuid4()
    email_otp.issue_otp(event_id, "guest@example.com")

    for _ in range(email_otp.MAX_VERIFY_ATTEMPTS):
        with pytest.raises(email_otp.EmailOtpInvalid):
            email_otp.verify_otp(event_id, "guest@example.com", "000000")

    with pytest.raises(email_otp.EmailOtpInvalid):
        email_otp.verify_otp(event_id, "guest@example.com", "123456")


def test_email_otp_enforces_resend_cooldown(fake_redis):
    event_id = uuid4()
    email_otp.issue_otp(event_id, "guest@example.com")
    with pytest.raises(email_otp.EmailOtpRateLimited):
        email_otp.issue_otp(event_id, "guest@example.com")
