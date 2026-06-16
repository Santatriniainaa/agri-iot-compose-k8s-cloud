/**
 * Modèles TypeScript du contrat API — alignés sur les schémas Pydantic
 * du backend (services/api/schemas/models.py).
 */

export interface Token {
  access_token: string;
  token_type: string;
}

export interface Health {
  status: string;
  influxdb: boolean;
  model_loaded: boolean;
}

export interface BasedOn {
  soil_moisture_avg: number;
  temperature_avg: number;
  rainfall_sum: number;
  soil_ph_avg: number;
}

export interface ParcelSummary {
  parcel: string;
  time: string | null;
  soil_moisture_avg: number;
  temperature_avg: number;
  rainfall_sum: number;
  soil_ph_avg: number;
  irrigation_needed: boolean;
  irrigation_minutes: number;
  irrigation_volume_l_m2: number;
  anomaly: boolean;
  predicted_yield_index: number | null;
}

export interface Overview {
  count: number;
  irrigating: number;
  anomalies: number;
  parcels: ParcelSummary[];
}

export interface Recommendation {
  parcel: string;
  irrigation_needed: boolean;
  irrigation_minutes: number;
  irrigation_volume_l_m2: number;
  anomaly: boolean;
  predicted_yield_index: number | null;
  based_on: BasedOn;
}

export interface YieldPrediction {
  parcel: string;
  predicted_yield_index: number;
}

export interface HistoryPoint {
  time: string;
  value: number | null;
}

export interface History {
  parcel: string;
  metric: string;
  points: HistoryPoint[];
}

export interface Latest {
  parcel: string;
  data: Record<string, unknown>;
}

export interface Alerts {
  count: number;
  alerts: Array<Record<string, unknown>>;
}

/** Métriques exposées par /api/v1/history (liste blanche côté backend). */
export type Metric =
  | 'soil_moisture_avg'
  | 'soil_moisture_min'
  | 'temperature_avg'
  | 'rainfall_sum'
  | 'soil_ph_avg'
  | 'irrigation_minutes'
  | 'irrigation_volume_l_m2'
  | 'samples';
