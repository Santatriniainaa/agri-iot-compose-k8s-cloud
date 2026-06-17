"""Endpoint météo : protection v1, ouverture de l'alias, exposition OpenAPI."""
from fastapi.testclient import TestClient


def test_weather_requires_token(client: TestClient):
    # Sans jeton, la surface versionnée renvoie 401 avant tout accès aux données.
    assert client.get("/api/v1/weather").status_code == 401


def test_weather_with_token_not_401(client: TestClient, auth_headers: dict):
    # Avec jeton, l'auth passe (503 attendu si InfluxDB absent en test, jamais 401).
    resp = client.get("/api/v1/weather", headers=auth_headers)
    assert resp.status_code != 401


def test_weather_alias_open(client: TestClient):
    # L'alias rétro-compatible /api reste ouvert (cohérent avec les autres routes).
    assert client.get("/api/weather").status_code != 401


def test_weather_documented(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/weather" in paths
