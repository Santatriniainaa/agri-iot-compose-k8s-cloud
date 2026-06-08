#!/usr/bin/env python3
"""agri-iot-compose-k8s-cloud — Sensor simulator.

Émule un réseau de capteurs agricoles (soil_moisture, temperature, rainfall,
soil_ph) pour une ou plusieurs parcelles et publie des mesures réalistes en MQTT.
Aucun matériel physique : les séries sont générées par un modèle agronomique
simplifié (cycle diurne, évapotranspiration, pluie, dérive du pH, décharge
batterie) avec injection occasionnelle d'anomalies pour exercer l'edge-service.

Stateless : on réplique le conteneur pour simuler davantage de capteurs.
Topics publiés : agri/<site>/<parcel>/raw/<type>
"""
import json
import math
import os
import random
import signal
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

# Configuration
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
SITE = os.getenv("SITE", "farm01")
PARCELS = [p.strip() for p in os.getenv("PARCELS", "zoneA,zoneB,zoneC").split(",") if p.strip()]
PUBLISH_INTERVAL = float(os.getenv("PUBLISH_INTERVAL", "2"))
ANOMALY_PROB = float(os.getenv("ANOMALY_PROB", "0.01"))
RECONNECT_RETRY_S = 2

# Paramètres du modèle agronomique
TEMP_BASE_C = 24.0
TEMP_AMPLITUDE_C = 8.0
TEMP_NOISE_SD = 0.6
PHASE_INFLUENCE = 0.05

RAIN_EVENT_PROB = 0.03
RAIN_MIN_MM, RAIN_MAX_MM = 0.5, 12.0

EVAPO_BASE_C = 18.0           # température au-delà de laquelle l'évapotranspiration s'ajoute
EVAPO_RATE = 0.05
BASELINE_DRY = 0.35          # assèchement permanent par pas (drainage + absorption racinaire) :
                             # empêche la saturation à MOISTURE_MAX et crée un cycle réaliste
                             # assèchement → pluie (l'irrigation peut alors se déclencher)
RAIN_REHYDRATION = 1.8       # gain d'humidité par mm de pluie
MOISTURE_NOISE_SD = 0.30
MOISTURE_MIN, MOISTURE_MAX = 5.0, 60.0

PH_DRIFT_SD = 0.01
PH_MIN, PH_MAX = 4.5, 8.5

BATTERY_DRAIN_MAX = 0.02
BATTERY_MIN = 5.0

INIT_MOISTURE = (28.0, 40.0)
INIT_PH = (6.0, 6.6)
INIT_BATTERY = (85.0, 100.0)

SENSOR_UNITS = {
    "soil_moisture": "%VWC",
    "temperature": "degC",
    "rainfall": "mm",
    "soil_ph": "pH",
}

_stop = threading.Event()     # signalé sur SIGTERM/SIGINT → arrêt propre


def now_iso() -> str:
    """Horodatage UTC ISO 8601 (seconde)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ParcelState:
    """État physique courant d'une parcelle (mémoire entre deux pas de temps)."""

    def __init__(self, parcel: str):
        self.parcel = parcel
        self.soil_moisture = random.uniform(*INIT_MOISTURE)
        self.soil_ph = random.uniform(*INIT_PH)
        self.battery = random.uniform(*INIT_BATTERY)
        # déphasage propre à la parcelle → courbes distinctes d'une parcelle à l'autre
        self.phase = random.uniform(0, 2 * math.pi)

    def step(self) -> dict:
        """Avance l'état d'un pas de temps et renvoie les mesures du moment."""
        now = datetime.now(timezone.utc)
        hour = now.hour + now.minute / 60.0

        day_angle = (hour / 24.0) * 2 * math.pi - math.pi / 2 + self.phase * PHASE_INFLUENCE
        temperature = TEMP_BASE_C + TEMP_AMPLITUDE_C * math.sin(day_angle)
        temperature += random.gauss(0, TEMP_NOISE_SD)

        rainfall = 0.0
        if random.random() < RAIN_EVENT_PROB:
            rainfall = round(random.uniform(RAIN_MIN_MM, RAIN_MAX_MM), 1)

        evapo = max(0.0, temperature - EVAPO_BASE_C) * EVAPO_RATE
        self.soil_moisture += rainfall * RAIN_REHYDRATION - evapo - BASELINE_DRY
        self.soil_moisture += random.gauss(0, MOISTURE_NOISE_SD)
        self.soil_moisture = max(MOISTURE_MIN, min(MOISTURE_MAX, self.soil_moisture))

        self.soil_ph += random.gauss(0, PH_DRIFT_SD)
        self.soil_ph = max(PH_MIN, min(PH_MAX, self.soil_ph))

        self.battery = max(BATTERY_MIN, self.battery - random.uniform(0.0, BATTERY_DRAIN_MAX))

        return {
            "soil_moisture": round(self.soil_moisture, 2),
            "temperature": round(temperature, 2),
            "rainfall": rainfall,
            "soil_ph": round(self.soil_ph, 2),
        }


def maybe_inject_anomaly(values: dict) -> tuple[dict, bool]:
    """Injecte occasionnellement une valeur aberrante pour exercer l'edge-service."""
    if random.random() < ANOMALY_PROB:
        kind = random.choice(["soil_moisture", "temperature", "soil_ph"])
        if kind == "soil_moisture":
            values["soil_moisture"] = random.choice([0.0, 99.0])
        elif kind == "temperature":
            values["temperature"] = random.choice([-10.0, 70.0])
        else:
            values["soil_ph"] = random.choice([1.0, 13.0])
        return values, True
    return values, False


def build_payload(sensor_type: str, parcel: str, value: float, battery: float) -> str:
    """Message JSON brut d'un capteur, conforme au schéma agri-iot-compose-k8s-cloud."""
    return json.dumps({
        "sensor_id": f"{SITE}-{parcel}-{sensor_type}",
        "type": sensor_type,
        "site": SITE,
        "parcel": parcel,
        "value": value,
        "unit": SENSOR_UNITS[sensor_type],
        "battery": round(battery, 1),
        "quality": "ok",
        "ts": now_iso(),
    })


def on_connect(client, userdata, flags, reason_code, properties=None) -> None:
    if reason_code == 0:
        print(f"[simulator] connecté à MQTT {MQTT_HOST}:{MQTT_PORT}", flush=True)
    else:
        print(f"[simulator] échec connexion MQTT, code={reason_code}", flush=True)


def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id=f"sensor-sim-{SITE}-{random.randint(1000, 9999)}")
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
            print(f"[simulator] broker {MQTT_HOST}:{MQTT_PORT} indisponible, "
                  f"nouvelle tentative dans {RECONNECT_RETRY_S}s...", flush=True)
            time.sleep(RECONNECT_RETRY_S)

    client.loop_start()

    states = {parcel: ParcelState(parcel) for parcel in PARCELS}
    print(f"[simulator] site={SITE} parcelles={PARCELS} intervalle={PUBLISH_INTERVAL}s", flush=True)

    while not _stop.is_set():
        for parcel, state in states.items():
            values = state.step()
            values, anomaly = maybe_inject_anomaly(values)
            for sensor_type, value in values.items():
                topic = f"agri/{SITE}/{parcel}/raw/{sensor_type}"
                client.publish(topic, build_payload(sensor_type, parcel, value, state.battery), qos=1)
            if anomaly:
                print(f"[simulator] anomalie injectée sur {parcel}: {values}", flush=True)
        _stop.wait(PUBLISH_INTERVAL)

    print("[simulator] arrêt demandé — déconnexion MQTT propre.", flush=True)
    client.loop_stop()
    client.disconnect()


def _handle_signal(signum, _frame) -> None:
    _stop.set()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    main()
