"""Schémas Pydantic des réponses de l'API.

Fournissent un contrat typé (OpenAPI) consommable par la PWA Angular et tout autre
client. Les champs `extra` sont autorisés là où InfluxDB peut renvoyer des mesures
additionnelles, afin de ne pas casser sur de nouvelles métriques.
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class Health(BaseModel):
    status: str = "ok"
    influxdb: bool
    model_loaded: bool

    # `model_loaded` commence par "model_" : on désactive le namespace protégé Pydantic.
    model_config = ConfigDict(protected_namespaces=())


class Parcels(BaseModel):
    parcels: list[str]


class Latest(BaseModel):
    parcel: str
    data: dict


class HistoryPoint(BaseModel):
    time: str
    value: Optional[float] = None


class History(BaseModel):
    parcel: str
    metric: str
    points: list[HistoryPoint]


class BasedOn(BaseModel):
    soil_moisture_avg: float
    temperature_avg: float
    rainfall_sum: float
    soil_ph_avg: float


class Recommendation(BaseModel):
    parcel: str
    irrigation_needed: bool
    irrigation_minutes: float
    irrigation_volume_l_m2: float
    anomaly: bool
    predicted_yield_index: Optional[float] = None
    based_on: BasedOn


class YieldPrediction(BaseModel):
    parcel: str
    predicted_yield_index: float

    model_config = ConfigDict(protected_namespaces=())


class ParcelSummary(BaseModel):
    parcel: str
    time: Optional[str] = None
    soil_moisture_avg: float
    temperature_avg: float
    rainfall_sum: float
    soil_ph_avg: float
    irrigation_needed: bool
    irrigation_minutes: float
    irrigation_volume_l_m2: float
    anomaly: bool
    predicted_yield_index: Optional[float] = None


class Overview(BaseModel):
    count: int = Field(..., description="Nombre de parcelles actives")
    irrigating: int = Field(..., description="Parcelles nécessitant une irrigation")
    anomalies: int = Field(..., description="Parcelles en anomalie")
    parcels: list[ParcelSummary]


class Alerts(BaseModel):
    count: int
    alerts: list[dict]


class Weather(BaseModel):
    """Conditions météo courantes du site (Open-Meteo via le weather-service)."""
    time: Optional[str] = None
    source: Optional[str] = None
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    precipitation_mm: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    pressure_hpa: Optional[float] = None
    cloud_cover_pct: Optional[float] = None

    # Tolère d'éventuels champs météo additionnels sans casser le contrat.
    model_config = ConfigDict(extra="allow")
