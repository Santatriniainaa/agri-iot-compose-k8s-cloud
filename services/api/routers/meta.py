"""Router des endpoints transverses : page d'accueil et santé.

Publics (non versionnés, non protégés) — utilisés par les sondes Docker/Kubernetes.
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from core import influx, ml
from schemas import models

router = APIRouter(tags=["meta"])


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def root():
    return """
    <h1>🌱 agri-iot-compose-k8s-cloud API</h1>
    <p>Plateforme cloud-native d'irrigation intelligente.</p>
    <ul>
      <li><a href="/docs">/docs</a> — documentation interactive (Swagger)</li>
      <li><a href="/health">/health</a> — état du service</li>
      <li><a href="/api/v1/parcels">/api/v1/parcels</a> — liste des parcelles</li>
      <li><a href="/api/v1/overview">/api/v1/overview</a> — vue d'ensemble (optimisée mobile)</li>
      <li><code>/api/v1/latest/{parcel}</code> — dernières mesures</li>
      <li><code>/api/v1/recommend/{parcel}</code> — recommandation d'irrigation</li>
      <li><code>/api/v1/predict/yield/{parcel}</code> — prévision de rendement (ML)</li>
      <li><a href="/api/v1/alerts">/api/v1/alerts</a> — alertes récentes</li>
    </ul>
    <p>Grafana : <a href="http://localhost:3000">http://localhost:3000</a></p>
    """


@router.get("/health", response_model=models.Health)
def health():
    return {"status": "ok", "influxdb": influx.ping(), "model_loaded": ml.is_loaded()}
