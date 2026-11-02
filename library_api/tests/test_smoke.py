import os

os.environ.setdefault("ATHENAEUM_ENV", "production")

import pytest
from fastapi.testclient import TestClient

from app.main import app, CORS_ORIGINS

client = TestClient(app)

ALLOWED = [
    "https://athenaeum-project.vercel.app",
    "https://tauri.localhost",
    "http://tauri.localhost",
]


@pytest.mark.parametrize("origin", ALLOWED)
def test_origin_in_production_list(origin):
    assert origin in CORS_ORIGINS


@pytest.mark.parametrize("origin", ALLOWED)
def test_preflight_allowed(origin):
    r = client.options(
        "/token",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == origin


def test_unknown_origin_blocked():
    r = client.options(
        "/token",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert r.status_code == 400


def test_version_route_works():
    r = client.get("/health/version")
    assert r.status_code == 200
    assert "commit" in r.json()