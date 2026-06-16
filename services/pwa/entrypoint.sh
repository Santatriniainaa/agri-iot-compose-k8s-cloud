#!/bin/sh
set -e

# Injecte la configuration au RUNTIME : l'URL de l'API est lue depuis l'environnement
# et écrite dans config.json (chargé par la PWA au démarrage). La MÊME image sert ainsi
# en Docker Compose et en Kubernetes sans recompilation.
: "${API_BASE_URL:=http://localhost:8000}"

cat > /usr/share/nginx/html/config.json <<EOF
{ "apiBaseUrl": "${API_BASE_URL}" }
EOF

echo "[pwa] config.json généré — apiBaseUrl=${API_BASE_URL}"

exec "$@"
