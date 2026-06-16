"""Configuration centralisée de l'API (variables d'environnement).

Regroupe en un seul endroit toute la configuration jadis éparpillée en tête de
`app.py`. Les valeurs par défaut conservent la posture démo du projet.
"""
import os


def _csv(value: str) -> list[str]:
    """Découpe une liste CSV en supprimant les espaces et entrées vides."""
    return [item.strip() for item in value.split(",") if item.strip()]


# InfluxDB
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "agri-iot-compose-k8s-cloud-dev-token-change-me-0123456789")
INFLUX_ORG = os.getenv("INFLUX_ORG", "agri-iot-compose-k8s-cloud")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "telemetry")

# MQTT
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")

# Modèle ML
MODEL_PATH = os.getenv("MODEL_PATH", "/app/models/yield_model.pkl")

# CORS — origines autorisées pour la PWA (navigateur). CSV, "*" pour tout autoriser.
CORS_ORIGINS = _csv(os.getenv("CORS_ORIGINS", "*"))
