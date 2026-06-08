#!/usr/bin/env python3
"""
agri-iot-compose-k8s-cloud — générateur de charge MQTT (mesure débit / latence / pertes).

Publie des messages JSON sur le broker à un débit cible pendant une durée donnée,
tout en s'abonnant au même topic pour mesurer la latence de bout en bout du chemin
d'ingestion (publish → broker → subscribe) ainsi que le taux de perte.

Sert l'étape 6 du cahier des charges (load testing). cf. rapport §scalabilité.
Réf. : Marinescu ch.12 (data streaming), ch.9 (gestion des ressources).

Dépendance : paho-mqtt  (pip install paho-mqtt)

Exemple :
    python3 loadgen.py --host localhost --rate 200 --duration 20
    # sortie JSON exploitable par load-test.sh
"""
import argparse
import json
import os
import sys
import threading
import time

try:
    import paho.mqtt.client as mqtt
except ImportError:
    sys.stderr.write("paho-mqtt manquant : pip install paho-mqtt\n")
    sys.exit(2)

TOPIC = "agri/loadtest/zoneX/raw/loadtest"


def percentile(values, p):
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--rate", type=int, default=100, help="messages/seconde cible")
    ap.add_argument("--duration", type=int, default=20, help="durée en secondes")
    ap.add_argument("--qos", type=int, default=1)
    ap.add_argument("--username", default=os.getenv("MQTT_USERNAME", ""),
                    help="login MQTT (défaut : variable d'env MQTT_USERNAME)")
    ap.add_argument("--password", default=os.getenv("MQTT_PASSWORD", ""),
                    help="mot de passe MQTT (défaut : variable d'env MQTT_PASSWORD)")
    args = ap.parse_args()

    latencies = []          # ms, accès protégé par lock
    received = {"n": 0}
    lock = threading.Lock()

    sub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="loadgen-sub")
    pub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="loadgen-pub")
    if args.username:
        sub.username_pw_set(args.username, args.password)
        pub.username_pw_set(args.username, args.password)

    def on_message(_c, _u, msg):
        now = time.time()
        try:
            sent = json.loads(msg.payload)["t"]
        except Exception:
            return
        with lock:
            latencies.append((now - sent) * 1000.0)
            received["n"] += 1

    sub.on_message = on_message
    sub.connect(args.host, args.port, keepalive=30)
    sub.subscribe(TOPIC, qos=args.qos)
    sub.loop_start()

    pub.connect(args.host, args.port, keepalive=30)
    pub.loop_start()
    time.sleep(0.5)  # laisse l'abonnement s'établir

    interval = 1.0 / args.rate
    deadline = time.time() + args.duration
    sent_count = 0
    next_t = time.time()
    while time.time() < deadline:
        payload = json.dumps({"seq": sent_count, "t": time.time(), "value": 42.0})
        pub.publish(TOPIC, payload, qos=args.qos)
        sent_count += 1
        next_t += interval
        sleep = next_t - time.time()
        if sleep > 0:
            time.sleep(sleep)

    time.sleep(2.0)  # laisse arriver les derniers messages
    sub.loop_stop(); pub.loop_stop()
    sub.disconnect(); pub.disconnect()

    with lock:
        recv = received["n"]
        lat = list(latencies)
    elapsed = args.duration
    loss = max(0.0, (sent_count - recv) / sent_count * 100.0) if sent_count else 0.0

    result = {
        "rate_target": args.rate,
        "sent": sent_count,
        "received": recv,
        "throughput_msg_s": round(recv / elapsed, 1),
        "loss_pct": round(loss, 2),
        "latency_ms_p50": round(percentile(lat, 50), 2),
        "latency_ms_p95": round(percentile(lat, 95), 2),
        "latency_ms_max": round(max(lat), 2) if lat else 0.0,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
