"""Chargement et inférence du modèle de prévision de rendement (scikit-learn).

Le modèle est entraîné par `train.py` au premier démarrage du conteneur et chargé
ici au lifespan de l'application.
"""
import joblib
from fastapi import HTTPException

from core import config

_model = None


def load_model() -> None:
    global _model
    try:
        _model = joblib.load(config.MODEL_PATH)
        print(f"[api] modèle ML chargé depuis {config.MODEL_PATH}", flush=True)
    except Exception as exc:                       # noqa: BLE001
        print(f"[api] modèle ML indisponible ({exc}) — /predict renverra une erreur", flush=True)
        _model = None


def is_loaded() -> bool:
    return _model is not None


def predict_yield(moisture, temp, rain, ph) -> float:
    if _model is None:
        raise HTTPException(503, "Modèle ML non chargé")
    value = float(_model.predict([[moisture, temp, rain, ph]])[0])
    return round(max(0.0, min(1.0, value)), 3)
