"""Logique métier des parcelles : état, recommandation, vue d'ensemble.

Combine la couche d'accès données (`core.influx`) et le modèle ML (`core.ml`)
pour produire les objets métier exposés par les routers.
"""
from fastapi import HTTPException

from core import influx, ml


def latest_or_404(parcel: str) -> dict:
    data = influx.query_latest(parcel)
    if not data:
        raise HTTPException(404, f"Aucune donnée récente pour la parcelle '{parcel}'")
    return data


def recommendation(parcel: str) -> dict:
    """Recommandation d'irrigation + prévision de rendement pour une parcelle."""
    data = latest_or_404(parcel)
    moisture = data.get("soil_moisture_avg", 0.0)
    temp = data.get("temperature_avg", 0.0)
    rain = data.get("rainfall_sum", 0.0)
    ph = data.get("soil_ph_avg", 6.5)
    yield_index = ml.predict_yield(moisture, temp, rain, ph) if ml.is_loaded() else None
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


def yield_prediction(parcel: str) -> dict:
    data = latest_or_404(parcel)
    yi = ml.predict_yield(data.get("soil_moisture_avg", 0.0), data.get("temperature_avg", 0.0),
                          data.get("rainfall_sum", 0.0), data.get("soil_ph_avg", 6.5))
    return {"parcel": parcel, "predicted_yield_index": yi}


def overview() -> dict:
    """Vue d'ensemble agrégée : un résumé par parcelle en un seul appel.

    Pensé pour la PWA mobile (réseau dégradé) : évite N+1 appels au dashboard.
    Les parcelles sans modèle ML chargé renvoient un rendement à null.
    """
    parcels = influx.query_parcels()
    items = []
    for parcel in parcels:
        data = influx.query_latest(parcel)
        if not data:
            continue
        moisture = data.get("soil_moisture_avg", 0.0)
        temp = data.get("temperature_avg", 0.0)
        rain = data.get("rainfall_sum", 0.0)
        ph = data.get("soil_ph_avg", 6.5)
        items.append({
            "parcel": parcel,
            "time": data.get("_time"),
            "soil_moisture_avg": moisture,
            "temperature_avg": temp,
            "rainfall_sum": rain,
            "soil_ph_avg": ph,
            "irrigation_needed": bool(data.get("irrigation_needed", 0)),
            "irrigation_minutes": data.get("irrigation_minutes", 0),
            "irrigation_volume_l_m2": data.get("irrigation_volume_l_m2", 0.0),
            "anomaly": bool(data.get("anomaly", 0)),
            "predicted_yield_index": (
                ml.predict_yield(moisture, temp, rain, ph) if ml.is_loaded() else None
            ),
        })
    return {
        "count": len(items),
        "irrigating": sum(1 for i in items if i["irrigation_needed"]),
        "anomalies": sum(1 for i in items if i["anomaly"]),
        "parcels": items,
    }
