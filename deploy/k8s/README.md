# ☸️ agri-iot-compose-k8s-cloud sur Kubernetes

Déploiement orchestré de la plateforme agri-iot-compose-k8s-cloud (étape 6 du cahier des charges :
orchestration + scalabilité). Équivalent Kubernetes du `docker-compose.yml`, avec en
plus **HPA** (autoscaling), **probes**, **requests/limits**, **ConfigMap/Secret** et **PVC**.

## Contenu

| Fichier | Ressources |
|---------|------------|
| `00-namespace.yaml` | Namespace `agri-iot-compose-k8s-cloud` |
| `01-config.yaml` | ConfigMap (config) + Secret (tokens/mots de passe) |
| `10-mosquitto.yaml` | ConfigMap + PVC + Deployment + Service (broker MQTT) |
| `20-influxdb.yaml` | PVC + Deployment + Service (base time-series) |
| `30-telegraf.yaml` | ConfigMap + Deployment (ingestion MQTT→Influx) |
| `40-edge-service.yaml` | Deployment + Service + **HPA** (edge, stateless) |
| `50-sensor-simulator.yaml` | Deployment (capteurs, scalable) |
| `60-api-service.yaml` | Deployment + Service (NodePort) + **HPA** (API+ML) |
| `70-grafana.yaml` | PVC + Deployment + Service (NodePort) |
| `kustomization.yaml` | Agrège le tout + labels recommandés `app.kubernetes.io/*` (`kubectl apply -k`) |
| `kind-config.yaml` | Config du cluster kind (nom `agri-iot-compose-k8s-cloud`, NodePorts mappés sur l'hôte) |

## Prérequis

- **kind** + **kubectl** (cluster local jetable). minikube/k3d fonctionnent aussi, mais le
  flux `make` ci-dessous cible kind.
- **metrics-server** (obligatoire pour les HPA) : installé et patché automatiquement par
  `make k8s-metrics` (inclus dans `make k8s-up`).

## Démarrage — tout-en-un

Depuis la racine du dépôt :

```bash
make k8s-up
```

Cette cible enchaîne, de façon idempotente :

1. `make k8s-cluster` — crée le cluster kind **`agri-iot-compose-k8s-cloud`**
   (via `kind-config.yaml`) → nœud `agri-iot-compose-k8s-cloud-control-plane`.
2. `make k8s-metrics` — installe metrics-server (+ patch `--kubelet-insecure-tls`, requis sur kind).
3. `make k8s-load` — `make build` (tags `agri-iot-compose-k8s-cloud/<svc>:latest`, partagés avec
   `docker-compose.yml`) puis `kind load` des 3 images applicatives (pas de registry requis).
4. `make k8s-deploy` — `kubectl apply -k deploy/k8s/`.

Chaque étape reste disponible séparément. Suivi de l'état :

```bash
make k8s-status                         # pods (-o wide) + services + HPA
kubectl -n agri-iot-compose-k8s-cloud get pods -w    # attendre Running/Ready
```

### (Optionnel) Provisionner le dashboard Grafana

```bash
kubectl -n agri-iot-compose-k8s-cloud create configmap grafana-provisioning \
  --from-file=infra/grafana/provisioning/ --dry-run=client -o yaml | kubectl apply -f -
# puis monter ce ConfigMap sur /etc/grafana/provisioning dans 70-grafana.yaml
```

## 3. Accéder aux services

Avec kind (`kind-config.yaml`), les NodePort sont mappés directement sur l'hôte :

```bash
# API FastAPI (Swagger) → http://localhost:30800/docs
# Grafana               → http://localhost:30300   (admin / agri-iot-compose-k8s-cloud)

# Alternative (port-forward, ports décalés pour éviter le conflit compose 3000/8000) :
make k8s-forward        # Grafana :3001 · API :8001
```

## 4. Scalabilité (étape 6 du cahier des charges)

```bash
# Scaling manuel des capteurs (générateur de charge) :
kubectl -n agri-iot-compose-k8s-cloud scale deploy/sensor-simulator --replicas=5

# Observer l'autoscaling de l'edge sous charge :
kubectl -n agri-iot-compose-k8s-cloud get hpa -w
kubectl -n agri-iot-compose-k8s-cloud top pods                      # nécessite metrics-server
```

Le load-test chiffré (débit, latence, pertes, CPU/RAM) est fourni par
[`../../scripts/load-test.sh`](../../scripts/load-test.sh) (`make loadtest`).

## 5. Nettoyage

```bash
make k8s-delete               # kubectl delete -k deploy/k8s/ (supprime les ressources)
make k8s-cluster-delete       # kind delete cluster --name agri-iot-compose-k8s-cloud
```

> ⚠️ **Sécurité (démo)** : le `Secret` contient des valeurs en clair ; l'authentification
> MQTT est activée mais **sans TLS**. En production : gestionnaire de secrets (Vault /
> Sealed Secrets), TLS/mTLS MQTT, NetworkPolicies, tokens InfluxDB à privilèges réduits.
