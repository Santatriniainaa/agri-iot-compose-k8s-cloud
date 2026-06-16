"""Endpoints transverses (publics)."""
from fastapi.testclient import TestClient


def test_health_ok(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    # InfluxDB injoignable en test → False, mais l'endpoint répond (pas d'exception).
    assert body["influxdb"] is False
    assert body["model_loaded"] is False


def test_openapi_exposes_v1(client: TestClient):
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    # La surface versionnée est documentée ; l'alias /api est masqué (include_in_schema=False).
    assert "/api/v1/overview" in paths
    assert "/api/overview" not in paths
