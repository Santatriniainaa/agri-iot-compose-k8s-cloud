#!/usr/bin/env python3
"""
agri-iot-compose-k8s-cloud — Entraînement du modèle de prévision de rendement (yield).

Le modèle estime un *yield index* (0..1) à partir de variables agronomiques
agrégées. Faute de jeu de données réel embarqué, on génère un dataset
synthétique réaliste basé sur un modèle agronomique simple, puis on entraîne
un RandomForestRegressor (scikit-learn). Le modèle est sauvegardé pour être
chargé par l'API.

Variables d'entrée : [soil_moisture_avg, temperature_avg, rainfall_sum, soil_ph_avg]
"""
import os

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

MODEL_PATH = os.getenv("MODEL_PATH", "/app/models/yield_model.pkl")
RNG = np.random.default_rng(42)


def synthetic_yield(moisture, temp, rain, ph):
    """Modèle agronomique synthétique : rendement optimal autour de conditions
    idéales (humidité ~35%, température ~25°C, pH ~6.5), pénalisé par l'écart."""
    moisture_term = 1.0 - ((moisture - 35.0) / 35.0) ** 2
    temp_term = 1.0 - ((temp - 25.0) / 20.0) ** 2
    ph_term = 1.0 - ((ph - 6.5) / 3.0) ** 2
    rain_term = np.clip(rain / 20.0, 0, 1) * 0.15      # un peu de pluie aide
    y = 0.45 * moisture_term + 0.25 * temp_term + 0.15 * ph_term + rain_term
    return np.clip(y, 0.0, 1.0)


def generate_dataset(n=6000):
    moisture = RNG.uniform(5, 60, n)
    temp = RNG.uniform(5, 45, n)
    rain = RNG.uniform(0, 40, n)
    ph = RNG.uniform(4.5, 8.5, n)
    X = np.column_stack([moisture, temp, rain, ph])
    y = synthetic_yield(moisture, temp, rain, ph) + RNG.normal(0, 0.03, n)
    y = np.clip(y, 0.0, 1.0)
    return X, y


def main():
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    X, y = generate_dataset()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(n_estimators=120, max_depth=12, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    mae = mean_absolute_error(y_test, model.predict(X_test))
    print(f"[train] RandomForestRegressor entraîné — MAE test = {mae:.4f}")

    joblib.dump(model, MODEL_PATH)
    print(f"[train] modèle sauvegardé dans {MODEL_PATH}")


if __name__ == "__main__":
    main()
