"""Validation des entrées interpolées dans les requêtes Flux.

`parcel`, `metric` et `range` sont injectés dans des requêtes Flux : on n'accepte
que des identifiants sûrs et une liste blanche de métriques (anti-injection).
"""
import re

from fastapi import HTTPException

_SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_SAFE_RANGE = re.compile(r"^-\d{1,5}[smhdw]$")           # ex. -1h, -30m, -7d

ALLOWED_METRICS = frozenset({
    "soil_moisture_avg", "soil_moisture_min", "temperature_avg", "rainfall_sum",
    "soil_ph_avg", "irrigation_needed", "irrigation_minutes",
    "irrigation_volume_l_m2", "anomaly", "samples", "window_s",
})


def safe_parcel(parcel: str) -> str:
    if not _SAFE_NAME.match(parcel):
        raise HTTPException(400, "Nom de parcelle invalide (attendu : [A-Za-z0-9_-])")
    return parcel


def safe_metric(metric: str) -> str:
    if metric not in ALLOWED_METRICS:
        raise HTTPException(400, f"Métrique inconnue (autorisées : {sorted(ALLOWED_METRICS)})")
    return metric


def safe_range(rng: str) -> str:
    if not _SAFE_RANGE.match(rng):
        raise HTTPException(400, "Plage invalide (attendu : -<n><s|m|h|d|w>, ex. -1h)")
    return rng
