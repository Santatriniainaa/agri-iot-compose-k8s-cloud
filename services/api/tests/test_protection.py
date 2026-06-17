"""Protection des routes : /api/v1 exige un JWT, l'alias /api reste ouvert."""
from fastapi.testclient import TestClient


def test_v1_requires_token(client: TestClient):
    # Sans jeton, la surface versionnée renvoie 401 (avant tout accès aux données).
    assert client.get("/api/v1/parcels").status_code == 401
    assert client.get("/api/v1/overview").status_code == 401


def test_v1_with_token_not_401(client: TestClient, auth_headers: dict):
    # Avec jeton, l'auth passe : on n'attend plus 401 (503 si InfluxDB absent en test).
    resp = client.get("/api/v1/parcels", headers=auth_headers)
    assert resp.status_code != 401


def test_legacy_alias_open(client: TestClient):
    # L'alias rétro-compatible /api n'est pas protégé (Grafana, smoke, démo).
    assert client.get("/api/parcels").status_code != 401
