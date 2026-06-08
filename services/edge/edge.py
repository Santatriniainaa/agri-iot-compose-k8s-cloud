#!/usr/bin/env python3
"""agri-iot-compose-k8s-cloud — Edge service (edge computing logiciel, sans matériel).

S'abonne aux mesures brutes (agri/<site>/<parcel>/raw/<type>), filtre le bruit,
détecte les anomalies, agrège par fenêtre glissante et par parcelle, décide
l'irrigation (règle déterministe) puis re-publie :
    agri/<site>/<parcel>/processed   mesures agrégées (→ Telegraf → InfluxDB)
    agri/<site>/<parcel>/alerts      alertes / recommandations

Store-and-forward : si le broker est indisponible, les messages sont mis en file
localement puis rejoués à la reconnexion. Le service est stateless (l'état n'est
qu'un cache mémoire) donc réplicable ; la shared subscription évite les doublons.
"""
import json
import os
import signal
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

# Configuration
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
WINDOW_SECONDS = float(os.getenv("WINDOW_SECONDS", "10"))
MOISTURE_THRESHOLD = float(os.getenv("MOISTURE_THRESHOLD", "30"))  # %VWC → irriguer en dessous
RAIN_SKIP_MM = float(os.getenv("RAIN_SKIP_MM", "2"))              # pluie cumulée annulant l'irrigation

# Constantes de réglage
BUFFER_MAXLEN = 2000          # mesures conservées par (site, parcelle, type)
PENDING_MAXLEN = 10_000       # capacité du buffer store-and-forward
WINDOW_LOOKBACK_FACTOR = 1.5  # marge sur la fenêtre (absorbe la gigue d'arrivée)
FROZEN_MIN_SAMPLES = 8        # échantillons mini pour juger un capteur « figé »
MIN_IRRIGATION_MIN = 5
MAX_IRRIGATION_MIN = 60
MINUTES_PER_DEFICIT_PT = 3    # minutes d'irrigation par point d'humidité manquant
VOLUME_PER_DEFICIT_PT = 0.3   # L/m² par point d'humidité manquant
RECONNECT_RETRY_S = 2

# Plages physiques plausibles (hors plage ⇒ anomalie / valeur filtrée)
VALID_RANGES = {
    "soil_moisture": (3.0, 65.0),
    "temperature": (-5.0, 60.0),
    "rainfall": (0.0, 200.0),
    "soil_ph": (3.5, 9.5),
}

# État partagé (protégé par _lock)
_buffers = defaultdict(lambda: deque(maxlen=BUFFER_MAXLEN))  # (site, parcel, type) -> deque[(ts, value)]
_parcels = set()
_lock = threading.Lock()

_pending = deque(maxlen=PENDING_MAXLEN)  # store-and-forward (broker indisponible)
_connected = threading.Event()           # vrai tant que le broker est joignable
_stop = threading.Event()                # signalé sur SIGTERM/SIGINT → arrêt propre


def now_iso() -> str:
    """Horodatage UTC ISO 8601 (seconde) — format attendu par Telegraf."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Callbacks MQTT
def on_connect(client, userdata, flags, reason_code, properties=None) -> None:
    if reason_code == 0:
        print(f"[edge] connecté à MQTT {MQTT_HOST}:{MQTT_PORT}", flush=True)
        # Shared subscription : avec plusieurs réplicas, le broker répartit les
        # messages entre eux (pas de doublons). Identique avec un seul réplica.
        client.subscribe("$share/edge/agri/+/+/raw/+", qos=1)
        _connected.set()
        flush_pending(client)
    else:
        print(f"[edge] échec connexion, code={reason_code}", flush=True)


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties=None) -> None:
    _connected.clear()
    print(f"[edge] déconnecté (code={reason_code}) — store-and-forward actif", flush=True)


def on_message(client, userdata, msg) -> None:
    """Range chaque mesure brute valide dans le buffer de sa série temporelle."""
    try:
        data = json.loads(msg.payload.decode())
        site = data["site"]
        parcel = data["parcel"]
        stype = data["type"]
        value = float(data["value"])
    except (ValueError, KeyError, json.JSONDecodeError):
        return
    with _lock:
        _parcels.add((site, parcel))
        _buffers[(site, parcel, stype)].append((time.monotonic(), value))


# Logique métier (pure, testable)
def is_anomaly(stype: str, values: list) -> bool:
    """Anomalie si une valeur est hors plage physique, ou si le capteur est figé."""
    if not values:
        return False
    lo, hi = VALID_RANGES.get(stype, (float("-inf"), float("inf")))
    if any(v < lo or v > hi for v in values):
        return True
    if stype in ("soil_moisture", "temperature") and len(values) >= FROZEN_MIN_SAMPLES:
        if max(values) - min(values) == 0:
            return True
    return False


def window_values(buf: deque, horizon: float) -> list:
    """Valeurs du buffer plus récentes que `horizon` secondes."""
    cutoff = time.monotonic() - horizon
    return [v for (t, v) in buf if t >= cutoff]


def compute_irrigation(moisture_avg, rain_sum):
    """Règle d'irrigation déterministe (explicable / démontrable).

    Retourne (needed: int, minutes: int, volume_l_m2: float, reason: str).
    """
    if rain_sum is not None and rain_sum > RAIN_SKIP_MM:
        return 0, 0, 0.0, f"pluie suffisante ({rain_sum:.1f} mm) — pas d'irrigation"
    if moisture_avg is None:
        return 0, 0, 0.0, "données insuffisantes"
    if moisture_avg < MOISTURE_THRESHOLD:
        deficit = MOISTURE_THRESHOLD - moisture_avg
        minutes = int(min(MAX_IRRIGATION_MIN, max(MIN_IRRIGATION_MIN, deficit * MINUTES_PER_DEFICIT_PT)))
        volume = round(deficit * VOLUME_PER_DEFICIT_PT, 2)
        return 1, minutes, volume, (
            f"humidité {moisture_avg:.1f}% < seuil {MOISTURE_THRESHOLD:.0f}% "
            f"et pluie {rain_sum or 0:.1f} mm")
    return 0, 0, 0.0, f"humidité {moisture_avg:.1f}% au-dessus du seuil"


# Publication MQTT avec store-and-forward
def flush_pending(client) -> None:
    """Rejoue les messages bufferisés tant que le broker accepte."""
    while _pending and _connected.is_set():
        topic, payload = _pending[0]
        if client.publish(topic, payload, qos=1).rc == mqtt.MQTT_ERR_SUCCESS:
            _pending.popleft()
        else:
            break


def publish(client, topic: str, payload: str) -> None:
    """Publie, ou met en file si déconnecté / échec (store-and-forward)."""
    if _connected.is_set() and client.publish(topic, payload, qos=1).rc == mqtt.MQTT_ERR_SUCCESS:
        return
    _pending.append((topic, payload))


# Agrégation
def _window(snapshot: dict, key: tuple) -> list:
    """Valeurs d'une série (site, parcelle, type) sur la fenêtre + marge."""
    return window_values(deque(snapshot.get(key, [])), WINDOW_SECONDS * WINDOW_LOOKBACK_FACTOR)


def _in_range(stype: str, values: list) -> list:
    """Écarte les valeurs hors plage physique avant de moyenner."""
    lo, hi = VALID_RANGES.get(stype, (float("-inf"), float("inf")))
    return [v for v in values if lo <= v <= hi]


def _mean(values: list):
    """Moyenne arrondie (2 décimales), ou None si la liste est vide."""
    return round(sum(values) / len(values), 2) if values else None


def process_parcel(client, site: str, parcel: str, snapshot: dict) -> None:
    """Agrège une parcelle sur la fenêtre courante, décide l'irrigation et publie."""
    moisture = _window(snapshot, (site, parcel, "soil_moisture"))
    temperature = _window(snapshot, (site, parcel, "temperature"))
    rainfall = _window(snapshot, (site, parcel, "rainfall"))
    ph = _window(snapshot, (site, parcel, "soil_ph"))

    samples = max(len(moisture), len(temperature), len(rainfall), len(ph))
    if samples == 0:
        return

    anomaly = any((
        is_anomaly("soil_moisture", moisture),
        is_anomaly("temperature", temperature),
        is_anomaly("soil_ph", ph),
    ))

    moisture_clean = _in_range("soil_moisture", moisture)
    temp_clean = _in_range("temperature", temperature)
    ph_clean = _in_range("soil_ph", ph)

    moisture_avg = _mean(moisture_clean)
    moisture_min = round(min(moisture_clean), 2) if moisture_clean else None
    temp_avg = _mean(temp_clean)
    rain_sum = round(sum(rainfall), 2) if rainfall else 0.0
    ph_avg = _mean(ph_clean)

    needed, minutes, volume, reason = compute_irrigation(moisture_avg, rain_sum)

    processed = {
        "site": site,
        "parcel": parcel,
        "window_s": WINDOW_SECONDS,
        "samples": samples,
        "soil_moisture_avg": moisture_avg if moisture_avg is not None else 0.0,
        "soil_moisture_min": moisture_min if moisture_min is not None else 0.0,
        "temperature_avg": temp_avg if temp_avg is not None else 0.0,
        "rainfall_sum": rain_sum,
        "soil_ph_avg": ph_avg if ph_avg is not None else 0.0,
        "irrigation_needed": needed,
        "irrigation_minutes": minutes,
        "irrigation_volume_l_m2": volume,
        "anomaly": 1 if anomaly else 0,
        "ts": now_iso(),
    }
    publish(client, f"agri/{site}/{parcel}/processed", json.dumps(processed))

    if needed or anomaly:
        alert = {
            "site": site,
            "parcel": parcel,
            "level": "critical" if anomaly else "warning",
            "reason": ("anomalie capteur détectée — " + reason) if anomaly else reason,
            "recommendation": {
                "action": "irrigate" if needed else "inspect_sensor",
                "minutes": minutes,
                "volume_l_m2": volume,
            },
            "ts": now_iso(),
        }
        publish(client, f"agri/{site}/{parcel}/alerts", json.dumps(alert))
        print(f"[edge] ALERTE {parcel}: {alert['level']} — {alert['reason']}", flush=True)
    else:
        print(f"[edge] {parcel}: moisture={moisture_avg} temp={temp_avg} "
              f"rain={rain_sum} ph={ph_avg} (n={samples})", flush=True)


def aggregation_loop(client) -> None:
    """Toutes les WINDOW_SECONDS : prend un instantané de l'état et traite chaque parcelle."""
    while not _stop.is_set():
        _stop.wait(WINDOW_SECONDS)
        if _stop.is_set():
            break
        with _lock:
            parcels = list(_parcels)
            snapshot = {key: list(buf) for key, buf in _buffers.items()}
        for site, parcel in parcels:
            process_parcel(client, site, parcel, snapshot)


def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="edge-service")
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    print(f"[edge] démarrage — fenêtre={WINDOW_SECONDS}s seuil={MOISTURE_THRESHOLD}%", flush=True)
    # Connexion résiliente : attendre le broker plutôt que crasher au démarrage.
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
            break
        except OSError:
            print(f"[edge] broker indisponible, nouvelle tentative dans {RECONNECT_RETRY_S}s...", flush=True)
            time.sleep(RECONNECT_RETRY_S)

    client.loop_start()
    aggregation_loop(client)

    print("[edge] arrêt demandé — déconnexion MQTT propre.", flush=True)
    client.loop_stop()
    client.disconnect()


def _handle_signal(signum, _frame) -> None:
    _stop.set()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    main()
