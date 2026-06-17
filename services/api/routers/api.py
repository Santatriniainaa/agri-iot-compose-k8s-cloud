"""Router métier de l'API (parcelles, historique, recommandation, alertes, overview).

Ce router est monté DEUX fois par `app.py` :
  - sous `/api/v1` → surface versionnée (cible PWA et nouveaux clients) ;
  - sous `/api`    → alias rétro-compatible (Grafana, scripts, `make smoke`).
Aucune logique métier ici : on délègue à `core.influx` et `services.parcels`.
"""
from fastapi import APIRouter, HTTPException

from core import influx, mqtt
from schemas import models
from services import parcels as parcels_svc

router = APIRouter(tags=["agri"])


@router.get("/parcels", response_model=models.Parcels)
def list_parcels():
    try:
        return {"parcels": influx.query_parcels()}
    except Exception as exc:                        # noqa: BLE001
        raise HTTPException(503, f"InfluxDB indisponible: {exc}")


@router.get("/overview", response_model=models.Overview)
def overview():
    """Résumé de toutes les parcelles en un seul appel (optimisé mobile)."""
    try:
        return parcels_svc.overview()
    except Exception as exc:                        # noqa: BLE001
        raise HTTPException(503, f"InfluxDB indisponible: {exc}")


@router.get("/latest/{parcel}", response_model=models.Latest)
def latest(parcel: str):
    return {"parcel": parcel, "data": parcels_svc.latest_or_404(parcel)}


@router.get("/history/{parcel}", response_model=models.History)
def history(parcel: str, metric: str = "soil_moisture_avg", range: str = "-1h"):
    return {"parcel": parcel, "metric": metric,
            "points": influx.query_history(parcel, metric, range)}


@router.get("/recommend/{parcel}", response_model=models.Recommendation)
def recommend(parcel: str):
    return parcels_svc.recommendation(parcel)


@router.get("/predict/yield/{parcel}", response_model=models.YieldPrediction)
def predict(parcel: str):
    return parcels_svc.yield_prediction(parcel)


@router.get("/alerts", response_model=models.Alerts)
def alerts(limit: int = 50):
    return {"count": mqtt.alerts_count(), "alerts": mqtt.recent_alerts(limit)}


@router.get("/weather", response_model=models.Weather)
def weather():
    """Conditions météo courantes du site (Open-Meteo via le weather-service)."""
    try:
        return influx.query_weather()
    except Exception as exc:                        # noqa: BLE001
        raise HTTPException(503, f"InfluxDB indisponible: {exc}")
