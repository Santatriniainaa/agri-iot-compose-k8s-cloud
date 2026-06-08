#!/usr/bin/env bash
# agri-iot-compose-k8s-cloud — test de bout en bout : vérifie que le pipeline complet fonctionne.
set -euo pipefail

API=http://localhost:8000
echo "== agri-iot-compose-k8s-cloud smoke test =="

echo "[1/5] Attente de l'API..."
for i in $(seq 1 30); do
  if curl -sf "$API/health" >/dev/null 2>&1; then break; fi
  sleep 2
done
curl -sf "$API/health" | python3 -m json.tool

echo "[2/5] Attente de l'arrivée des données (edge → Telegraf → InfluxDB)..."
parcels="[]"
for i in $(seq 1 30); do
  parcels=$(curl -sf "$API/api/parcels" | python3 -c "import sys,json;print(json.load(sys.stdin)['parcels'])" 2>/dev/null || echo "[]")
  if [ "$parcels" != "[]" ]; then break; fi
  sleep 3
done
echo "Parcelles détectées : $parcels"
if [ "$parcels" = "[]" ]; then
  echo "❌ Aucune parcelle — vérifier les logs (docker compose logs edge-service telegraf)"; exit 1
fi

echo "[3/5] Dernières mesures (zoneA) :"
curl -sf "$API/api/latest/zoneA" | python3 -m json.tool

echo "[4/5] Recommandation d'irrigation (zoneA) :"
curl -sf "$API/api/recommend/zoneA" | python3 -m json.tool

echo "[5/5] Prévision de rendement ML (zoneA) :"
curl -sf "$API/api/predict/yield/zoneA" | python3 -m json.tool

echo "✅ Smoke test réussi : pipeline capteurs → edge → MQTT → Telegraf → InfluxDB → API/ML opérationnel."
