#!/usr/bin/env python3
"""agri-iot-compose-k8s-cloud — API / ML service (FastAPI).

Expose une API REST au-dessus d'InfluxDB : état temps réel des parcelles,
historique, recommandation d'irrigation, prévision de rendement (modèle
scikit-learn entraîné par train.py) et flux d'alertes (souscription MQTT).

Docs interactives : http://localhost:8000/docs
"""
import json
import os
import re
import threading
from collections import deque
from contextlib import asynccontextmanager

import joblib
import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from influxdb_client import InfluxDBClient

# Configuration
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "agri-iot-compose-k8s-cloud-dev-token-change-me-0123456789")
INFLUX_ORG = os.getenv("INFLUX_ORG", "agri-iot-compose-k8s-cloud")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "telemetry")
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MODEL_PATH = os.getenv("MODEL_PATH", "/app/models/yield_model.pkl")

_alerts = deque(maxlen=200)
_model = None
_mqtt_client = None        # conservé pour une déconnexion propre à l'arrêt

# Validation des entrées : parcel/metric/range sont interpolés dans des requêtes
# Flux → on n'accepte que des identifiants sûrs et une liste blanche de métriques.
_SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_SAFE_RANGE = re.compile(r"^-\d{1,5}[smhdw]$")           # ex. -1h, -30m, -7d
_ALLOWED_METRICS = frozenset({
    "soil_moisture_avg", "soil_moisture_min", "temperature_avg", "rainfall_sum",
    "soil_ph_avg", "irrigation_needed", "irrigation_minutes",
    "irrigation_volume_l_m2", "anomaly", "samples", "window_s",
})


def _safe_parcel(parcel: str) -> str:
    if not _SAFE_NAME.match(parcel):
        raise HTTPException(400, "Nom de parcelle invalide (attendu : [A-Za-z0-9_-])")
    return parcel


# Modèle ML
def load_model():
    global _model
    try:
        _model = joblib.load(MODEL_PATH)
        print(f"[api] modèle ML chargé depuis {MODEL_PATH}", flush=True)
    except Exception as exc:                       # noqa: BLE001
        print(f"[api] modèle ML indisponible ({exc}) — /predict renverra une erreur", flush=True)
        _model = None


def predict_yield(moisture, temp, rain, ph) -> float:
    if _model is None:
        raise HTTPException(503, "Modèle ML non chargé")
    value = float(_model.predict([[moisture, temp, rain, ph]])[0])
    return round(max(0.0, min(1.0, value)), 3)


# Abonnement MQTT aux alertes (thread d'arrière-plan)
def _on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        client.subscribe("agri/+/+/alerts", qos=1)
        print("[api] abonné aux alertes MQTT", flush=True)


def _on_message(client, userdata, msg):
    try:
        _alerts.appendleft(json.loads(msg.payload.decode()))
    except json.JSONDecodeError:
        pass


def start_mqtt():
    global _mqtt_client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="api-alert-listener")
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = _on_connect
    client.on_message = _on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
            break
        except OSError:
            threading.Event().wait(2)
    _mqtt_client = client
    client.loop_forever()       # interrompu par client.disconnect() au shutdown


# InfluxDB
def influx_client() -> InfluxDBClient:
    return InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)


def _query(flux: str):
    """Exécute une requête Flux et renvoie les tables résultantes."""
    with influx_client() as client:
        return client.query_api().query(flux)


def query_latest(parcel: str) -> dict:
    parcel = _safe_parcel(parcel)
    flux = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -1h)
      |> filter(fn: (r) => r._measurement == "agri_processed" and r.parcel == "{parcel}")
      |> last()
    '''
    fields = {}
    for table in _query(flux):
        for record in table.records:
            fields[record.get_field()] = record.get_value()
            fields["_time"] = record.get_time().isoformat()
    return fields


def query_parcels() -> list:
    flux = f'''
    import "influxdata/influxdb/schema"
    schema.tagValues(bucket: "{INFLUX_BUCKET}", tag: "parcel",
      predicate: (r) => r._measurement == "agri_processed", start: -1h)
    '''
    parcels = []
    for table in _query(flux):
        for record in table.records:
            parcels.append(record.get_value())
    return sorted(parcels)


def query_history(parcel: str, metric: str, rng: str) -> list:
    parcel = _safe_parcel(parcel)
    if metric not in _ALLOWED_METRICS:
        raise HTTPException(400, f"Métrique inconnue (autorisées : {sorted(_ALLOWED_METRICS)})")
    if not _SAFE_RANGE.match(rng):
        raise HTTPException(400, "Plage invalide (attendu : -<n><s|m|h|d|w>, ex. -1h)")
    flux = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {rng})
      |> filter(fn: (r) => r._measurement == "agri_processed"
                        and r.parcel == "{parcel}" and r._field == "{metric}")
      |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
    '''
    points = []
    for table in _query(flux):
        for record in table.records:
            points.append({"time": record.get_time().isoformat(), "value": record.get_value()})
    return points


def _latest_or_404(parcel: str) -> dict:
    data = query_latest(parcel)
    if not data:
        raise HTTPException(404, f"Aucune donnée récente pour la parcelle '{parcel}'")
    return data


# Application FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()
    threading.Thread(target=start_mqtt, daemon=True).start()
    yield
    if _mqtt_client is not None:
        _mqtt_client.disconnect()


app = FastAPI(title="agri-iot-compose-k8s-cloud API", version="1.0.0", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <h1>🌱 agri-iot-compose-k8s-cloud API</h1>
    <p>Plateforme cloud-native d'irrigation intelligente.</p>
    <ul>
      <li><a href="/docs">/docs</a> — documentation interactive (Swagger)</li>
      <li><a href="/health">/health</a> — état du service</li>
      <li><a href="/api/parcels">/api/parcels</a> — liste des parcelles</li>
      <li><code>/api/latest/{parcel}</code> — dernières mesures</li>
      <li><code>/api/recommend/{parcel}</code> — recommandation d'irrigation</li>
      <li><code>/api/predict/yield/{parcel}</code> — prévision de rendement (ML)</li>
      <li><a href="/api/alerts">/api/alerts</a> — alertes récentes</li>
    </ul>
    <p>Grafana : <a href="http://localhost:3000">http://localhost:3000</a></p>
    """


@app.get("/health")
def health():
    try:
        with influx_client() as client:
            healthy = client.ping()
    except Exception:                              # noqa: BLE001
        healthy = False
    return {"status": "ok", "influxdb": bool(healthy), "model_loaded": _model is not None}


@app.get("/api/parcels")
def parcels():
    try:
        return {"parcels": query_parcels()}
    except Exception as exc:                        # noqa: BLE001
        raise HTTPException(503, f"InfluxDB indisponible: {exc}")


@app.get("/api/latest/{parcel}")
def latest(parcel: str):
    return {"parcel": parcel, "data": _latest_or_404(parcel)}


@app.get("/api/history/{parcel}")
def history(parcel: str, metric: str = "soil_moisture_avg", range: str = "-1h"):
    return {"parcel": parcel, "metric": metric, "points": query_history(parcel, metric, range)}


@app.get("/api/recommend/{parcel}")
def recommend(parcel: str):
    data = _latest_or_404(parcel)
    moisture = data.get("soil_moisture_avg", 0.0)
    temp = data.get("temperature_avg", 0.0)
    rain = data.get("rainfall_sum", 0.0)
    ph = data.get("soil_ph_avg", 6.5)
    yield_index = predict_yield(moisture, temp, rain, ph) if _model else None
    return {
        "parcel": parcel,
        "irrigation_needed": bool(data.get("irrigation_needed", 0)),
        "irrigation_minutes": data.get("irrigation_minutes", 0),
        "irrigation_volume_l_m2": data.get("irrigation_volume_l_m2", 0.0),
        "anomaly": bool(data.get("anomaly", 0)),
        "predicted_yield_index": yield_index,
        "based_on": {"soil_moisture_avg": moisture, "temperature_avg": temp,
                     "rainfall_sum": rain, "soil_ph_avg": ph},
    }


@app.get("/api/predict/yield/{parcel}")
def predict(parcel: str):
    data = _latest_or_404(parcel)
    yi = predict_yield(data.get("soil_moisture_avg", 0.0), data.get("temperature_avg", 0.0),
                       data.get("rainfall_sum", 0.0), data.get("soil_ph_avg", 6.5))
    return {"parcel": parcel, "predicted_yield_index": yi}


@app.get("/api/alerts")
def alerts(limit: int = 50):
    return {"count": len(_alerts), "alerts": list(_alerts)[:limit]}
