"""Login, session and role tests through the real app, on the throwaway database."""
import os

os.environ.setdefault("ATHENAEUM_ENV", "production")

import random
import re
import string
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import auth as auth_module
from app import token_manager as tm
from app.auth import hash_password
from app.database import get_connection
from app.main import app

PASSWORD = "Correct-Horse-9!"


class FakeRedis:
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
    monkeypatch.setattr(auth_module, "redis_client", fake)
    return fake


@pytest.fixture
def make_user():
    """Creates real users in the test database and removes them afterwards."""
    created = []

    def _make(role="The Keeper", status="APPROVED", expires_at=None):
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO users
                    (name, email, role, status, operator_id, hashed_password, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING user_id
                """,
                (
                    f"Test {code}", f"{code.lower()}@example.test", role, status,
                    f"ATH{code}", hash_password(PASSWORD), expires_at,
                ),
            )
            user_id = cur.fetchone()[0]
            conn.commit()
        finally:
            conn.close()
        created.append(user_id)
        return {"user_id": user_id, "code": code, "operator_id": f"ATH{code}"}

    yield _make

    conn = get_connection()
    try:
        cur = conn.cursor()
        for user_id in created:
            cur.execute("DELETE FROM refresh_tokens WHERE user_id = %s", (str(user_id),))
            cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()
    finally:
        conn.close()


def _bearer(user, role, **extra):
    token = tm.create_token({"sub": str(user["user_id"]), "role": role, **extra}, "access")
    return {"Authorization": f"Bearer {token}"}


def _login(client, user, password=PASSWORD, remember_me=False):
    return client.post(
        "/token",
        data={
            "username": user["operator_id"],
            "password": password,
            "remember_me": "true" if remember_me else "false",
        },
    )


# ---------- login ----------

def test_wrong_password_is_rejected(make_user):
    user = make_user()
    r = _login(TestClient(app), user, password="not-the-password")
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid credentials"


def test_unknown_operator_gets_same_error_as_wrong_password(make_user):
    ghost = {"operator_id": "ATHZZZZZ"}
    r = _login(TestClient(app), ghost)
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid credentials"


def test_unapproved_account_cannot_log_in(make_user):
    user = make_user(status="PENDING")
    r = _login(TestClient(app), user)
    assert r.status_code == 403


def test_login_refresh_and_reuse_detection(make_user, fake_redis):
    user = make_user()
    client = TestClient(app)

    # 1. Log in with "remember me"
    r = _login(client, user, remember_me=True)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["role"] == "The Keeper"
    assert tm.decode_token(body["access_token"])["sub"] == str(user["user_id"])
    csrf = body["csrf_token"]
    cookies = " ".join(r.headers.get_list("set-cookie"))
    old_refresh = re.search(r"refresh_token=([^;]+)", cookies).group(1)

    def refresh_with(refresh_token):
        return TestClient(app).post(
            "/auth/refresh",
            headers={
                "Cookie": f"refresh_token={refresh_token}; csrf_token={csrf}",
                "X-CSRF-Token": csrf,
            },
        )

    # 2. A valid refresh gives a new access token and a new refresh cookie
    r2 = refresh_with(old_refresh)
    assert r2.status_code == 200, r2.text
    assert r2.json()["access_token"]
    new_refresh = re.search(r"refresh_token=([^;]+)", " ".join(r2.headers.get_list("set-cookie"))).group(1)
    assert new_refresh != old_refresh

    # 3. Replaying the OLD refresh token is treated as theft
    r3 = refresh_with(old_refresh)
    assert r3.status_code == 401
    assert "reuse" in r3.json()["detail"].lower()

    # 4. ...and it also kills the new session
    r4 = refresh_with(new_refresh)
    assert r4.status_code == 401


# ---------- check-identity ----------

def test_check_identity_accepts_real_operator(make_user):
    user = make_user()
    r = TestClient(app).post("/auth/check-identity", json={"identity_code": user["code"]})
    assert r.status_code == 200


def test_check_identity_unknown_code(make_user):
    r = TestClient(app).post("/auth/check-identity", json={"identity_code": "QQQQQ"})
    assert r.status_code == 404


# ---------- roles and sessions (tokens minted directly, no rate-limited login) ----------

def test_keeper_can_list_users(make_user):
    user = make_user("The Keeper")
    r = TestClient(app).get("/admin/users", headers=_bearer(user, "The Keeper"))
    assert r.status_code == 200
    assert user["operator_id"] in [row["operator_id"] for row in r.json()]


def test_seeker_cannot_list_users(make_user):
    future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=24)
    user = make_user("The Seeker", expires_at=future)
    r = TestClient(app).get("/admin/users", headers=_bearer(user, "The Seeker"))
    assert r.status_code == 403


def test_expired_seeker_session_is_rejected(make_user):
    past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
    user = make_user("The Seeker", expires_at=past)
    r = TestClient(app).get("/admin/users", headers=_bearer(user, "The Seeker"))
    assert r.status_code == 401


def test_unapproved_user_token_is_rejected(make_user):
    user = make_user("The Keeper", status="PENDING")
    r = TestClient(app).get("/admin/users", headers=_bearer(user, "The Keeper"))
    assert r.status_code == 401


def test_half_finished_2fa_token_is_not_a_session(make_user):
    user = make_user("The Keeper")
    headers = _bearer(user, "The Keeper", scope="2fa_preauth")
    r = TestClient(app).get("/admin/users", headers=headers)
    assert r.status_code == 401


def test_refresh_token_cannot_be_used_as_access_token(make_user):
    user = make_user("The Keeper")
    refresh = tm.create_token({"sub": str(user["user_id"]), "role": "The Keeper"}, "refresh")
    r = TestClient(app).get("/admin/users", headers={"Authorization": f"Bearer {refresh}"})
    assert r.status_code == 401
