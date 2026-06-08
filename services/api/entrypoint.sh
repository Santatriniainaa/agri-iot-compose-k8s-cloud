#!/bin/sh
set -e

# Entraîne le modèle de prévision de rendement s'il n'existe pas encore.
if [ ! -f /app/models/yield_model.pkl ]; then
  echo "[api] entraînement du modèle ML (yield)..."
  python train.py
fi

echo "[api] démarrage de l'API FastAPI sur :8000"
exec uvicorn app:app --host 0.0.0.0 --port 8000
