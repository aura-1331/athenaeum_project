"""Token security tests. No database or Redis needed (Redis is faked)."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from jose import jwt

from app import token_manager as tm


class FakeRedis:
    """Tiny in-memory stand-in for the parts of Redis the app uses."""

    def __init__(self):
        self.store = {}

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.store:
            return None
        self.store[key] = value
        return True

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value


@pytest.fixture
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(tm, "redis_client", fake)
    return fake


def test_access_token_round_trip():
    token = tm.create_token({"sub": "7", "role": "The Keeper"}, "access")
    payload = tm.decode_token(token)
    assert payload["sub"] == "7"
    assert payload["role"] == "The Keeper"
    assert payload["type"] == "access"
    assert "jti" not in payload


def test_refresh_token_has_unique_id():
    a = tm.decode_token(tm.create_token({"sub": "7"}, "refresh"))
    b = tm.decode_token(tm.create_token({"sub": "7"}, "refresh"))
    assert a["type"] == "refresh"
    assert a["jti"] and b["jti"] and a["jti"] != b["jti"]


def test_unknown_token_type_rejected():
    with pytest.raises(ValueError):
        tm.create_token({"sub": "7"}, "banana")


def test_tampered_token_rejected():
    token = tm.create_token({"sub": "7"}, "access")
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    with pytest.raises(HTTPException) as exc:
        tm.decode_token(tampered)
    assert exc.value.status_code == 401


def test_token_signed_with_other_algorithm_rejected():
    # A forged token signed with a different algorithm and a made-up secret.
    now = datetime.now(timezone.utc)
    forged = jwt.encode(
        {
            "sub": "1", "role": "The Chief", "type": "access",
            "iss": tm.ISSUER, "aud": tm.AUDIENCE,
            "iat": now, "exp": now + timedelta(minutes=5),
        },
        "attacker-secret",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc:
        tm.decode_token(forged)
    assert exc.value.status_code == 401


def test_expired_token_rejected():
    now = datetime.now(timezone.utc)
    expired = jwt.encode(
        {
            "sub": "1", "type": "access",
            "iss": tm.ISSUER, "aud": tm.AUDIENCE,
            "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1),
        },
        tm.PRIVATE_KEY,
        algorithm=tm.ALGORITHM,
    )
    with pytest.raises(HTTPException) as exc:
        tm.decode_token(expired)
    assert exc.value.status_code == 401


def test_wrong_audience_rejected():
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "1", "type": "access",
            "iss": tm.ISSUER, "aud": "some-other-app",
            "iat": now, "exp": now + timedelta(minutes=5),
        },
        tm.PRIVATE_KEY,
        algorithm=tm.ALGORITHM,
    )
    with pytest.raises(HTTPException) as exc:
        tm.decode_token(token)
    assert exc.value.status_code == 401


def test_access_token_cannot_be_used_as_refresh(fake_redis):
    access = tm.create_token({"sub": "7"}, "access")
    with pytest.raises(HTTPException) as exc:
        tm.verify_refresh_token(access)
    assert exc.value.status_code == 401


def test_refresh_rotation_works_once(fake_redis):
    refresh = tm.create_token({"sub": "7"}, "refresh")
    result = tm.rotate_refresh_token(refresh, "The Keeper")

    assert result["token_type"] == "bearer"
    assert result["old_jti"] != result["new_jti"]
    assert tm.decode_token(result["access_token"])["type"] == "access"
    assert tm.decode_token(result["refresh_token"])["type"] == "refresh"


def test_refresh_token_reuse_is_blocked(fake_redis):
    refresh = tm.create_token({"sub": "7"}, "refresh")
    tm.rotate_refresh_token(refresh, "The Keeper")

    with pytest.raises(HTTPException) as exc:
        tm.rotate_refresh_token(refresh, "The Keeper")
    assert exc.value.status_code == 401


def test_rotation_rejects_invalid_role(fake_redis):
    refresh = tm.create_token({"sub": "7"}, "refresh")
    with pytest.raises(HTTPException) as exc:
        tm.rotate_refresh_token(refresh, "The Emperor")
    assert exc.value.status_code == 401
    # A rejected role must not burn the token.
    assert fake_redis.get(f"revoked:{tm.decode_token(refresh)['jti']}") is None


def test_revoked_refresh_token_rejected(fake_redis):
    refresh = tm.create_token({"sub": "7"}, "refresh")
    tm.revoke_refresh_token(refresh)
    with pytest.raises(HTTPException) as exc:
        tm.verify_refresh_token(refresh)
    assert exc.value.status_code == 401
