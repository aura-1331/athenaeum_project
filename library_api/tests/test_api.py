"""API-level checks through the real app. Needs the throwaway test database."""
import os

os.environ.setdefault("ATHENAEUM_ENV", "production")

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_database_ok():
    r = client.get("/health/")
    assert r.status_code == 200
    assert r.json()["database"]["status"] == "ok"


@pytest.mark.parametrize("path", ["/catalogue/pending-items", "/catalogue/pending-works"])
def test_protected_routes_reject_anonymous(path):
    assert client.get(path).status_code == 401


def test_refresh_without_csrf_is_rejected():
    assert client.post("/auth/refresh").status_code == 403


def test_check_identity_rejects_bad_format():
    r = client.post("/auth/check-identity", json={"identity_code": "!!"})
    assert r.status_code == 400
