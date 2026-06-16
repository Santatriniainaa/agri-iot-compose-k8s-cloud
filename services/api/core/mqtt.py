"""Souscription MQTT aux alertes (thread d'arrière-plan).

Garde en mémoire les 200 dernières alertes publiées par l'edge sur `agri/+/+/alerts`.
"""
import json
import threading
from collections import deque

import paho.mqtt.client as mqtt

from core import config

_alerts: deque = deque(maxlen=200)
_client = None        # conservé pour une déconnexion propre à l'arrêt


def recent_alerts(limit: int) -> list:
    return list(_alerts)[:limit]


def alerts_count() -> int:
    return len(_alerts)


def _on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        client.subscribe("agri/+/+/alerts", qos=1)
        print("[api] abonné aux alertes MQTT", flush=True)


def _on_message(client, userdata, msg):
    try:
        _alerts.appendleft(json.loads(msg.payload.decode()))
    except json.JSONDecodeError:
        pass


def _run():
    global _client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="api-alert-listener")
    if config.MQTT_USERNAME:
        client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
    client.on_connect = _on_connect
    client.on_message = _on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    while True:
        try:
            client.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=30)
            break
        except OSError:
            threading.Event().wait(2)
    _client = client
    client.loop_forever()       # interrompu par client.disconnect() au shutdown


def start() -> None:
    threading.Thread(target=_run, daemon=True).start()


def stop() -> None:
    if _client is not None:
        _client.disconnect()
