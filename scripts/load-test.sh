#!/usr/bin/env bash
# agri-iot-compose-k8s-cloud — load test chiffré (étape 6). Monte en charge par paliers de débit
# MQTT et mesure, par palier, le débit traité, la latence (p50/p95/max), le taux
# de perte (via loadgen.py) et le CPU/RAM du broker et de l'edge (via docker stats).
# Résultats : tableau Markdown + CSV horodaté dans scripts/results/.
#
# Prérequis : stack démarrée (make up) + Docker. Aucune dépendance Python sur
# l'hôte : loadgen.py s'exécute DANS l'image sensor-simulator (Python 3.12 +
# paho-mqtt déjà embarqués), branchée sur le réseau du compose.
# Usage :
#   ./scripts/load-test.sh
#   RATES="50 100 200 400 800" DURATION=20 ./scripts/load-test.sh
set -euo pipefail
cd "$(dirname "$0")/.."

# Charge les identifiants MQTT depuis .env (le broker exige une authentification).
# loadgen.py les lit via MQTT_USERNAME / MQTT_PASSWORD (transmis au conteneur).
if [ -f .env ]; then
  set -a; . ./.env; set +a
fi

# loadgen tourne dans le réseau du compose : il joint le broker par son nom de
# service (mosquitto:1883), pas via le port publié sur l'hôte.
HOST="${LOADTEST_MQTT_HOST:-mosquitto}"
PORT="${LOADTEST_MQTT_PORT:-1883}"
RATES="${RATES:-50 100 200 400 800}"
DURATION="${DURATION:-15}"
BROKER_CT="${BROKER_CT:-agri-iot-compose-k8s-cloud-mosquitto}"
EDGE_CT="${EDGE_CT:-agri-iot-compose-k8s-cloud-edge}"
# Image embarquant paho-mqtt + réseau du compose (projet_réseau).
SIM_IMAGE="${SIM_IMAGE:-agri-iot-compose-k8s-cloud/sensor-simulator:latest}"
NETWORK="${LOADTEST_NETWORK:-agri-iot-compose-k8s-cloud_agri-iot-compose-k8s-cloud}"

# Exécute loadgen.py dans un conteneur jetable (monté en lecture seule) sur le
# réseau du compose. Les identifiants MQTT sont transmis depuis l'environnement.
run_loadgen() {  # "$@" -> arguments de loadgen.py
  docker run --rm --network "$NETWORK" \
    -e MQTT_USERNAME -e MQTT_PASSWORD \
    -v "$PWD/scripts/loadgen.py:/loadgen.py:ro" \
    "$SIM_IMAGE" python /loadgen.py "$@"
}

mkdir -p scripts/results
STAMP="$(date +%Y%m%d-%H%M%S 2>/dev/null || echo run)"
CSV="scripts/results/loadtest-$STAMP.csv"
echo "rate_target,throughput_msg_s,loss_pct,latency_p50_ms,latency_p95_ms,latency_max_ms,broker_cpu_pct,broker_mem_mb,edge_cpu_pct,edge_mem_mb" > "$CSV"

# Vérifs préalables : Docker, image simulateur et réseau du compose présents.
command -v docker >/dev/null || { echo "❌ docker requis"; exit 1; }
docker image inspect "$SIM_IMAGE" >/dev/null 2>&1 \
  || { echo "❌ image $SIM_IMAGE absente — lance d'abord 'make up'"; exit 1; }
docker network inspect "$NETWORK" >/dev/null 2>&1 \
  || { echo "❌ réseau $NETWORK absent — lance d'abord 'make up'"; exit 1; }
# Le post-traitement JSON utilise la lib standard de python3 (présent sur l'hôte).
command -v python3 >/dev/null || { echo "❌ python3 requis (post-traitement JSON)"; exit 1; }

# Échantillonne CPU%/MEM(MiB) d'un conteneur via docker stats (non bloquant).
sample_stats() {  # $1 = nom conteneur -> "cpu mem_mb" ; "NA NA" si indisponible
  local ct="$1" line
  if line=$(docker stats --no-stream --format '{{.CPUPerc}} {{.MemUsage}}' "$ct" 2>/dev/null); then
    local cpu mem
    cpu=$(echo "$line" | awk '{gsub(/%/,"",$1); print $1}')
    mem=$(echo "$line" | awk '{print $2}' | sed 's/MiB//; s/GiB/*1024/' | bc 2>/dev/null || echo "NA")
    echo "${cpu:-NA} ${mem:-NA}"
  else
    echo "NA NA"
  fi
}

echo "== agri-iot-compose-k8s-cloud load test =="
echo "Broker $HOST:$PORT · paliers: $RATES msg/s · durée/palier: ${DURATION}s"
echo
printf '| %-10s | %-12s | %-7s | %-9s | %-9s | %-9s | %-10s | %-9s |\n' \
  "rate(m/s)" "débit(m/s)" "perte%" "p50(ms)" "p95(ms)" "max(ms)" "brokerCPU%" "edgeCPU%"
printf '|%s|%s|%s|%s|%s|%s|%s|%s|\n' "------------" "--------------" "---------" "-----------" "-----------" "-----------" "------------" "-----------"

for rate in $RATES; do
  # Lance la mesure CPU en tâche de fond (milieu du palier)
  ( sleep $((DURATION/2)); sample_stats "$BROKER_CT" > /tmp/_lt_broker; sample_stats "$EDGE_CT" > /tmp/_lt_edge ) &
  STATS_PID=$!

  RES=$(run_loadgen --host "$HOST" --port "$PORT" --rate "$rate" --duration "$DURATION")
  wait $STATS_PID 2>/dev/null || true

  read -r BCPU BMEM < /tmp/_lt_broker 2>/dev/null || { BCPU=NA; BMEM=NA; }
  read -r ECPU EMEM < /tmp/_lt_edge   2>/dev/null || { ECPU=NA; EMEM=NA; }

  # Extrait les champs du JSON (sans dépendre de jq)
  get() { echo "$RES" | python3 -c "import sys,json;print(json.load(sys.stdin)['$1'])"; }
  THR=$(get throughput_msg_s); LOSS=$(get loss_pct)
  P50=$(get latency_ms_p50); P95=$(get latency_ms_p95); PMAX=$(get latency_ms_max)

  printf '| %-10s | %-12s | %-7s | %-9s | %-9s | %-9s | %-10s | %-9s |\n' \
    "$rate" "$THR" "$LOSS" "$P50" "$P95" "$PMAX" "$BCPU" "$ECPU"
  echo "$rate,$THR,$LOSS,$P50,$P95,$PMAX,$BCPU,$BMEM,$ECPU,$EMEM" >> "$CSV"
done

echo
echo "✅ Résultats CSV : $CSV"
echo "   Reporter ce tableau dans docs/rapport.md (§ Analyse de scalabilité)."
