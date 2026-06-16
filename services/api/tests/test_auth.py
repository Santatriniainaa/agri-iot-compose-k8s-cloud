"""Authentification JWT."""
from fastapi.testclient import TestClient

from tests.conftest import DEMO_PASSWORD, DEMO_USER


def test_login_success(client: TestClient):
    resp = client.post("/api/v1/auth/login", data={"username": DEMO_USER, "password": DEMO_PASSWORD})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password(client: TestClient):
    resp = client.post("/api/v1/auth/login", data={"username": DEMO_USER, "password": "nope"})
    assert resp.status_code == 401


def test_login_missing_fields(client: TestClient):
    # OAuth2PasswordRequestForm exige username/password → 422 si absents.
    resp = client.post("/api/v1/auth/login", data={"username": DEMO_USER})
    assert resp.status_code == 422
