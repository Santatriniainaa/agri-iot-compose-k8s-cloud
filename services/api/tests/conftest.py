"""Fixtures de test.

Le TestClient est instancié SANS gestionnaire de contexte : le lifespan n'est donc
pas exécuté (pas de thread MQTT ni de chargement de modèle), ce qui rend les tests
hermétiques — aucune dépendance à InfluxDB ou Mosquitto.
"""
import pytest
from fastapi.testclient import TestClient

from app import app

# Identifiants démo par défaut (cf. core/config.py).
DEMO_USER = "agri"
DEMO_PASSWORD = "agri-iot-demo"


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def token(client: TestClient) -> str:
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": DEMO_USER, "password": DEMO_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
