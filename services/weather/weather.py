#!/usr/bin/env python3
"""agri-iot-compose-k8s-cloud — Weather service (API météo → MQTT).

Interroge périodiquement une vraie API météo publique (Open-Meteo, gratuite et
sans clé) pour la position du site agricole, puis publie les conditions courantes
en MQTT pour ingestion (Telegraf → InfluxDB → Grafana, dashboard « agri-api-meteo »).

Résilience : si l'API est injoignable (réseau coupé, cluster kind offline, quota),
le service bascule sur une génération synthétique réaliste (modèle diurne simple)
afin que le dashboard continue de se remplir. Le tag `source` distingue les deux
origines (`open-meteo` vs `synthetic`).

Stateless. Topic publié : agri/<site>/meteo
"""
import json
import math
import os
import random
import signal
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

import paho.mqtt.client as mqtt
import requests

# Configuration
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
SITE = os.getenv("SITE") or "farm01"


def _env_float(name: str, default: str) -> float:
    """Lit une variable d'env numérique, en tolérant la valeur vide.

    Compose interpole une variable absente du .env en chaîne vide ("") ; on
    retombe alors sur le défaut plutôt que de planter sur float("").
    """
    return float(os.getenv(name) or default)


# Position du site (défaut : Antananarivo, Madagascar).
WEATHER_LAT = _env_float("WEATHER_LAT", "-18.8792")
WEATHER_LON = _env_float("WEATHER_LON", "47.5079")
WEATHER_POLL_INTERVAL = _env_float("WEATHER_POLL_INTERVAL", "60")
WEATHER_API_URL = os.getenv("WEATHER_API_URL") or "https://api.open-meteo.com/v1/forecast"
HTTP_TIMEOUT_S = _env_float("WEATHER_HTTP_TIMEOUT", "8")
RECONNECT_RETRY_S = 2

# Variables Open-Meteo demandées → clés normalisées de notre payload.
OPEN_METEO_CURRENT = [
    "temperature_2m", "relative_humidity_2m", "precipitation",
    "wind_speed_10m", "surface_pressure", "cloud_cover",
]
FIELD_MAP = {
    "temperature_2m": "temperature_c",
    "relative_humidity_2m": "humidity_pct",
    "precipitation": "precipitation_mm",
    "wind_speed_10m": "wind_speed_ms",
    "surface_pressure": "pressure_hpa",
    "cloud_cover": "cloud_cover_pct",
}

_stop = threading.Event()     # signalé sur SIGTERM/SIGINT → arrêt propre


def now_iso() -> str:
    """Horodatage UTC ISO 8601 (seconde) — format attendu par Telegraf."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_open_meteo() -> dict:
    """Interroge Open-Meteo et renvoie les conditions courantes normalisées.

    Lève une exception (requests / KeyError / ValueError) en cas d'échec : le
    cycle principal l'intercepte et bascule sur le fallback synthétique.
    """
    query = urlencode({
        "latitude": WEATHER_LAT,
        "longitude": WEATHER_LON,
        "current": ",".join(OPEN_METEO_CURRENT),
        "wind_speed_unit": "ms",
    })
    resp = requests.get(f"{WEATHER_API_URL}?{query}", timeout=HTTP_TIMEOUT_S)
    resp.raise_for_status()
    current = resp.json()["current"]
    reading = {dst: float(current[src]) for src, dst in FIELD_MAP.items()}
    reading["source"] = "open-meteo"
    return reading


def synthetic_reading() -> dict:
    """Conditions plausibles générées localement (fallback hors-ligne).

    Modèle diurne simple : la température suit l'heure du jour, l'humidité varie
    en sens inverse, pluie occasionnelle. Suffisant pour alimenter le dashboard.
    """
    now = datetime.now(timezone.utc)
    hour = now.hour + now.minute / 60.0
    day_angle = (hour / 24.0) * 2 * math.pi - math.pi / 2
    temperature = 22.0 + 7.0 * math.sin(day_angle) + random.gauss(0, 0.5)
    humidity = max(20.0, min(100.0, 70.0 - 1.5 * (temperature - 22.0) + random.gauss(0, 3)))
    precipitation = round(random.uniform(0.2, 6.0), 1) if random.random() < 0.1 else 0.0
    return {
        "temperature_c": round(temperature, 2),
        "humidity_pct": round(humidity, 1),
        "precipitation_mm": precipitation,
        "wind_speed_ms": round(max(0.0, random.gauss(3.0, 1.2)), 2),
        "pressure_hpa": round(random.gauss(1013.0, 3.0), 1),
        "cloud_cover_pct": round(min(100.0, max(0.0, humidity + random.gauss(0, 10))), 0),
        "source": "synthetic",
    }


def build_payload(reading: dict) -> str:
    """Message JSON météo, conforme au schéma d'ingestion Telegraf."""
    payload = {"site": SITE, "ts": now_iso()}
    payload.update({k: round(v, 2) if isinstance(v, float) else v for k, v in reading.items()})
    return json.dumps(payload)


def on_connect(client, userdata, flags, reason_code, properties=None) -> None:
    if reason_code == 0:
        print(f"[weather] connecté à MQTT {MQTT_HOST}:{MQTT_PORT}", flush=True)
    else:
        print(f"[weather] échec connexion MQTT, code={reason_code}", flush=True)


def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"weather-{SITE}")
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    # Connexion résiliente : attendre le broker plutôt que crasher au démarrage.
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
            break
        except OSError:
            print(f"[weather] broker {MQTT_HOST}:{MQTT_PORT} indisponible, "
                  f"nouvelle tentative dans {RECONNECT_RETRY_S}s...", flush=True)
            time.sleep(RECONNECT_RETRY_S)

    client.loop_start()
    topic = f"agri/{SITE}/meteo"
    print(f"[weather] site={SITE} lat={WEATHER_LAT} lon={WEATHER_LON} "
          f"intervalle={WEATHER_POLL_INTERVAL}s → {topic}", flush=True)

    while not _stop.is_set():
        try:
            reading = fetch_open_meteo()
        except Exception as exc:                       # noqa: BLE001
            print(f"[weather] API indisponible ({exc}) — fallback synthétique", flush=True)
            reading = synthetic_reading()
        client.publish(topic, build_payload(reading), qos=1)
        print(f"[weather] {reading['source']}: temp={reading['temperature_c']}°C "
              f"hum={reading['humidity_pct']}% pluie={reading['precipitation_mm']}mm", flush=True)
        _stop.wait(WEATHER_POLL_INTERVAL)

    print("[weather] arrêt demandé — déconnexion MQTT propre.", flush=True)
    client.loop_stop()
    client.disconnect()


def _handle_signal(signum, _frame) -> None:
    _stop.set()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    main()
