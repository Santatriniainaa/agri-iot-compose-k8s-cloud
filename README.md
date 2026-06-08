# 🌱 agri-iot-compose-k8s-cloud

> **Plateforme cloud-native d'irrigation intelligente pour l'agriculture connectée (IoT).**
> Projet final — Cloud Computing (Master / S9).
>
> Chaîne de bout en bout : **acquisition** (capteurs) → **edge computing** (filtrage / agrégation /
> décision) → **ingestion** (MQTT) → **stockage** (*time-series*) → **visualisation** →
> **aide à la décision** (recommandation d'irrigation + prévision de rendement par *machine learning*).

![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-HPA-326CE5?logo=kubernetes&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![MQTT](https://img.shields.io/badge/MQTT-Mosquitto-660066?logo=eclipsemosquitto&logoColor=white)
![InfluxDB](https://img.shields.io/badge/InfluxDB-2.7-22ADF6?logo=influxdb&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-11-F46800?logo=grafana&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## Présentation

La plateforme émule un réseau de capteurs agricoles (humidité du sol, température, pluviométrie, pH),
traite les mesures à la volée dans un service *edge* conteneurisé, les ingère dans une base
*time-series*, les visualise dans Grafana et expose une API REST qui **recommande l'irrigation** et
**prévoit le rendement** par apprentissage automatique.

L'ensemble est **100 % logiciel et conteneurisé — aucun matériel physique requis** (les capteurs
sont des *sensor simulators*). Le dépôt est **autonome** : il se clone, se build et se déploie seul,
aussi bien en **Docker Compose** (développement) qu'en **Kubernetes** (orchestration & autoscaling).

> 💡 **Contexte métier.** L'irrigation représente l'essentiel de la consommation d'eau agricole.
> Piloter l'arrosage à partir de mesures temps réel (humidité, météo, pH) plutôt que d'un calendrier
> fixe réduit le gaspillage d'eau et améliore le rendement — c'est l'objectif fonctionnel du projet.

## 📑 Sommaire

[1. Architecture](#1-architecture) · [2. Caractéristiques clés](#2-caractéristiques-clés) ·
[3. Prérequis](#3-prérequis) · [4. Démarrage rapide](#4-démarrage-rapide) ·
[5. Commandes `make`](#5-commandes-make) · [6. API](#6-endpoints-de-lapi) ·
[7. Modèle de données](#7-modèle-de-données) · [8. Scalabilité](#8-scalabilité) ·
[9. Démonstration](#9-démonstration-soutenance) · [10. Arrêt / nettoyage](#10-arrêt--nettoyage) ·
[11. Arborescence](#11-arborescence) · [12. Notes techniques](#12-notes-techniques) ·
[13. Dépannage](#13-dépannage)

---

## 1. Architecture

![Architecture agri-iot-compose-k8s-cloud — capteurs → edge → MQTT → InfluxDB → Grafana / API](assets/architecture.svg)

<details>
<summary>📐 Version ASCII (rendu terminal)</summary>

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      docker compose  (réseau « agri-iot-compose-k8s-cloud »)                    │
│                                                                                │
│  ┌────────────────────┐   MQTT    ┌──────────────┐                             │
│  │ sensor-simulator   │  raw/+    │  edge-service │  filtrage / agrégation /    │
│  │ (Python, paho-mqtt)│ ────────► │  (Python)     │  anomalies / décision       │
│  │  soil_moisture     │           └──────┬───────┘  store-and-forward          │
│  │  temperature       │                  │ processed / alerts                  │
│  │  rainfall          │                  ▼                                     │
│  │  soil_ph           │           ┌──────────────┐                             │
│  └────────────────────┘           │  Mosquitto   │  broker MQTT                │
│                                    └──────┬───────┘                             │
│                                           │ subscribe                           │
│                          ┌────────────────┼─────────────────┐                  │
│                          ▼                ▼                 ▼                  │
│                   ┌────────────┐   ┌────────────┐    ┌──────────────┐          │
│                   │  Telegraf  │   │ api-service│    │  (alerts →    │          │
│                   │ MQTT→Influx│   │ (FastAPI + │    │  api-service) │          │
│                   └─────┬──────┘   │  sklearn)  │    └──────────────┘          │
│                         ▼          └─────┬──────┘                              │
│                   ┌────────────┐         │ query                               │
│                   │  InfluxDB  │ ◄───────┘                                     │
│                   │ time-series│ ◄───────┐                                     │
│                   └────────────┘         │ query                               │
│                                    ┌──────┴───────┐                            │
│                                    │   Grafana    │  dashboards temps réel     │
│                                    └──────────────┘                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

</details>

L'architecture suit un modèle **microservices** découplé par messagerie, organisé en cinq couches :

| Couche | Rôle | Composants |
|--------|------|------------|
| **Acquisition** | Émulation des capteurs, publication MQTT | `sensor-simulator` |
| **Edge** | Filtrage, agrégation par fenêtre, anomalies, décision d'irrigation, *store-and-forward* | `edge-service` |
| **Messagerie** | Bus pub/sub découplant producteurs et consommateurs | `mosquitto` (broker MQTT) |
| **Stockage & ingestion** | Persistance *time-series* + rétention/downsampling | `telegraf` → `influxdb` |
| **Restitution** | Tableaux de bord temps réel + API REST/ML | `grafana`, `api-service` |

Détail des services et de leurs images :

| # | Service | Image / langage | Port | Rôle |
|---|---------|-----------------|------|------|
| 1 | `sensor-simulator` | Python 3.12 + paho-mqtt | — | Émule les capteurs, publie en MQTT (`agri/<site>/<parcel>/raw/<type>`) |
| 2 | `edge-service` | Python 3.12 + paho-mqtt | — | Filtrage, agrégation par fenêtre, anomalies, décision d'irrigation, store-and-forward |
| 3 | `mosquitto` | eclipse-mosquitto:2 | 1883 / 9001 | Broker MQTT (pub/sub) |
| 4 | `telegraf` | telegraf:1.30 | — | Ingestion MQTT → InfluxDB |
| 5 | `influxdb` | influxdb:2.7 | 8086 | Base *time-series* |
| 6 | `api-service` | FastAPI + scikit-learn | 8000 | API REST : état, recommandation, prévision de rendement (ML), alertes |
| 7 | `grafana` | grafana:11 | 3000 | Tableaux de bord temps réel |

### Infrastructure de déploiement

Le même ensemble de services se déploie sur deux infrastructures, du poste de développement au
cluster orchestré :

| | **Docker Compose** (dev) | **Kubernetes** (orchestration) |
|---|--------------------------|--------------------------------|
| **Cible** | poste local, démo rapide | cluster (kind / minikube / k3d) |
| **Définition** | [`deploy/docker-compose.yml`](deploy/docker-compose.yml) | [`deploy/k8s/`](deploy/k8s/) (kustomize) |
| **Config / secrets** | `.env` | `ConfigMap` + `Secret` |
| **Persistance** | volumes Docker | `PersistentVolumeClaim` |
| **Mise à l'échelle** | `--scale` (manuel) | **HPA** (autoscaling CPU) + probes, requests/limits |
| **Réseau** | réseau bridge `agri-iot-compose-k8s-cloud` | `Service` (ClusterIP / NodePort) |
| **Lancement** | `make up` | `make k8s-up` |

> Les images applicatives portent un tag unique (`agri-iot-compose-k8s-cloud/<svc>:latest`) **partagé**
> entre Compose et Kubernetes : un seul `make build` alimente les deux infrastructures.

---

## 2. Caractéristiques clés

- **Découplage pub/sub** : producteurs et consommateurs ne se connaissent pas ; le broker absorbe
  les pics et tolère les déconnexions.
- **Edge computing logiciel** : agrégation par fenêtre, détection d'anomalies, décision d'irrigation
  déterministe, et **store-and-forward** (rejeu des messages après coupure réseau).
- **Scaling horizontal sans doublons** : edge et Telegraf utilisent des **MQTT shared
  subscriptions** (`$share/...`) → le broker répartit les messages entre réplicas (prérequis HPA).
- **Élasticité Kubernetes** : `HorizontalPodAutoscaler` sur l'edge et l'API (+ probes, requests/limits).
- **API robuste** : validation stricte des paramètres (anti-injection Flux), `/health` pour les probes.
- **Arrêt propre** : les services Python gèrent `SIGTERM`/`SIGINT` (pas de coupure brutale).
- **Observabilité « as code »** : datasource + dashboard Grafana **provisionnés** automatiquement.
- **Couche ML** : recommandation d'irrigation + prévision de rendement (RandomForest).

---

## 3. Prérequis

### 3.1 Logiciels

**Indispensables (mode Docker Compose — par défaut)**

| Outil | Version min. | Vérifier | Rôle |
|-------|--------------|----------|------|
| **Docker Engine** | ≥ 20.10 | `docker version` | Exécution des conteneurs |
| **Docker Compose v2** | ≥ 2.0 | `docker compose version` | Orchestration de la stack (plugin `docker compose`, **pas** `docker-compose`) |
| **GNU Make** | ≥ 4.0 | `make --version` | Raccourcis (`make up`, `make demo`…) |
| **Bash** | ≥ 4 | `bash --version` | Scripts `smoke-test.sh` / `load-test.sh` |
| **curl** | toute | `curl --version` | Appels API (`make demo`, *smoke test*) |
| **Python 3** | ≥ 3.8 | `python3 --version` | `make demo` (json.tool) et `make loadtest` (`pip install paho-mqtt`) |

> Le code applicatif tourne **dans les conteneurs** (Python 3.12) : aucune installation Python
> côté hôte n'est nécessaire pour démarrer la plateforme — seulement pour `demo`/`loadtest`.

**Optionnels (mode Kubernetes)**

| Outil | Version conseillée | Rôle |
|-------|--------------------|------|
| **kubectl** | alignée sur le cluster (ex. v1.30.x) | Pilotage du cluster (`make k8s-deploy`) |
| **Cluster local** | kind / minikube / k3d | Cluster k8s mono-nœud (ex. `kind`, image `kindest/node:v1.30.0`) |
| **metrics-server** | — | Métriques CPU/mémoire requises par les **HPA** |

> ⚠️ **kubectl** : garder un *skew* d'au plus ±1 mineure avec le cluster (un client trop récent
> peut planter). Toujours vérifier l'intégrité du binaire téléchargé (`sha256sum` vs le `.sha256`
> officiel) — un téléchargement tronqué provoque un *segfault*.

### 3.2 Matériel / système

| Ressource | Mode Compose | Mode Kubernetes (kind) |
|-----------|--------------|------------------------|
| **CPU** | 2 cœurs | 4 cœurs conseillés |
| **RAM libre** | ~2 Go | ~4 Go (cluster + pods) |
| **Disque libre** | ~3 Go (images) | ~6 Go (+ image node kind ≈ 1,4 Go + PVC) |
| **OS** | Linux / macOS / Windows (WSL2) | idem |
| **Réseau** | Accès Internet pour tirer les images (`docker.io`, `dl.k8s.io`) | idem |

- **Ports libres requis** : `1883` (MQTT), `9001` (MQTT WebSocket), `8000` (API),
  `8086` (InfluxDB), `3000` (Grafana). Vérifier avec `ss -tlnp | grep -E '1883|8000|8086|3000'`.
- **Aucun matériel physique** (capteurs, passerelle LoRa) : tout est simulé logiciellement.

---

## 4. Démarrage rapide

```bash
cd agri-iot-compose-k8s-cloud                  # (dépôt complet : cd final_project/agri-iot-compose-k8s-cloud)
cp .env.example .env          # ajuste les paramètres si besoin
make up                       # build + démarrage des 7 conteneurs
```

> Le fichier compose est sous `deploy/` ; `make` l'invoque avec `--project-directory .`.
> Équivalent direct : `docker compose -f deploy/docker-compose.yml --project-directory . up -d --build`.

Patiente ~30–60 s (build + initialisation d'InfluxDB), puis :

| Service | URL | Identifiants |
|---------|-----|--------------|
| API (Swagger) | http://localhost:8000/docs | — |
| Grafana | http://localhost:3000 | `admin` / `agri-iot-compose-k8s-cloud` |
| InfluxDB | http://localhost:8086 | `admin` / `agri-iot-compose-k8s-cloud123` |

Le dashboard **« agri-iot-compose-k8s-cloud — Supervision des parcelles »** est déjà provisionné dans Grafana.

### Vérifier que tout fonctionne

```bash
make smoke      # test de bout en bout automatisé
# ou manuellement :
curl http://localhost:8000/health
curl http://localhost:8000/api/parcels
curl http://localhost:8000/api/recommend/zoneA
curl http://localhost:8000/api/predict/yield/zoneA
```

---

## 5. Commandes `make`

| Commande | Effet |
|----------|-------|
| `make up` | Build + démarre toute la plateforme |
| `make down` | Arrête les conteneurs (données conservées) |
| `make logs` | Suit les logs de l'edge-service |
| `make ps` | État des conteneurs |
| `make demo` | Interroge l'API (parcelles, recommandation, alertes) |
| `make smoke` | Test de bout en bout automatisé |
| `make scale N=5` | Réplique les `sensor-simulator` (scaling horizontal) |
| `make loadtest` | Load test chiffré (débit/latence/pertes/CPU) |
| `make k8s-deploy` / `k8s-delete` | Déploiement / suppression Kubernetes (`deploy/k8s/`) |
| `make k8s-forward` | Expose Grafana (`:3001`) + API (`:8001`) en local via *port-forward* |
| `make clean` | Arrête tout **et supprime les volumes** (données effacées) |

> Toutes les cibles `make` s'utilisent **depuis `agri-iot-compose-k8s-cloud/`** (le compose est sous `deploy/`,
> invoqué avec `--project-directory .`).

### Commandes utiles (hors `make`)

Raccourci pratique : `export COMPOSE="docker compose -f deploy/docker-compose.yml --project-directory ."`

**Docker Compose — exploitation & debug**
```bash
$COMPOSE ps                          # état des conteneurs
$COMPOSE logs -f                     # suit les logs de TOUS les services
$COMPOSE logs -f mosquitto           # logs d'un service précis
$COMPOSE restart edge-service        # redémarre un service
$COMPOSE up -d --force-recreate mosquitto   # recrée un conteneur (ex. après déplacement du projet)
$COMPOSE exec influxdb sh            # ouvre un shell dans un conteneur
docker stats --no-stream             # CPU/RAM par conteneur
```

**Vérifier le flux de données (capteur → InfluxDB)**
```bash
# Compter les points reçus sur 2 min dans InfluxDB
TOKEN=$($COMPOSE exec -T influxdb printenv DOCKER_INFLUXDB_INIT_ADMIN_TOKEN | tr -d '\r')
$COMPOSE exec -T influxdb influx query \
  'from(bucket:"telemetry") |> range(start:-2m) |> group(columns:["_field"]) |> count()' \
  --org agri-iot-compose-k8s-cloud --token "$TOKEN"

# Suivre les messages MQTT bruts en direct
$COMPOSE exec -T mosquitto mosquitto_sub -t 'agri/#' -u "$MQTT_USERNAME" -P "$MQTT_PASSWORD"
```

**Kubernetes (cluster local kind)**
```bash
export PATH="$HOME/.local/bin:$PATH"            # si kubectl/kind y sont installés

# Tout-en-un : crée le cluster « agri-iot-compose-k8s-cloud », installe metrics-server,
# construit + charge les images, applique les manifests, affiche l'état.
make k8s-up

# (équivaut à enchaîner ces étapes, chacune disponible séparément :)
#   make k8s-cluster   # kind create cluster --config deploy/k8s/kind-config.yaml
#   make k8s-metrics   # metrics-server (+ patch kubelet-insecure-tls, requis par les HPA)
#   make k8s-load      # make build puis kind load des 3 images applicatives
#   make k8s-deploy    # kubectl apply -k deploy/k8s
```

Le cluster est nommé **`agri-iot-compose-k8s-cloud`** → le nœud apparaît comme
`agri-iot-compose-k8s-cloud-control-plane` et toutes les ressources portent le label
`app.kubernetes.io/part-of: agri-iot-compose-k8s-cloud`.

```bash
make k8s-status                                 # pods (-o wide) + services + HPA
kubectl -n agri-iot-compose-k8s-cloud logs -f deploy/edge-service
kubectl -n agri-iot-compose-k8s-cloud describe pod -l app=mosquitto-agri-iot-compose-k8s-cloud   # diagnostiquer un crash

# Accès aux UIs : les NodePort sont mappés sur l'hôte via kind-config.yaml
#   • API     → http://localhost:30800/docs
#   • Grafana → http://localhost:30300
# … ou via port-forward sur ports décalés (3001/8001, évite le conflit compose 3000/8000) :
make k8s-forward

make k8s-delete                                 # supprime les ressources (garde le cluster)
make k8s-cluster-delete                         # supprime le cluster kind
```

---

## 6. Endpoints de l'API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/health` | État du service (InfluxDB, modèle ML) |
| GET | `/api/parcels` | Liste des parcelles actives |
| GET | `/api/latest/{parcel}` | Dernières mesures agrégées |
| GET | `/api/history/{parcel}?metric=soil_moisture_avg&range=-1h` | Historique d'une métrique |
| GET | `/api/recommend/{parcel}` | Recommandation d'irrigation + rendement prévu |
| GET | `/api/predict/yield/{parcel}` | Prévision de rendement (ML) |
| GET | `/api/alerts` | Alertes récentes (souscription MQTT) |

> Documentation interactive complète : **http://localhost:8000/docs** (Swagger).
> `parcel`, `metric` et `range` sont validés : une valeur invalide renvoie **HTTP 400**.

---

## 7. Modèle de données

**Topics MQTT**
```
agri/<site>/<parcel>/raw/<type>     # mesures brutes (simulateur)
agri/<site>/<parcel>/processed      # mesures agrégées + décision (edge → Telegraf)
agri/<site>/<parcel>/alerts         # alertes / recommandations (edge → api-service)
```

**Message brut** (`.../raw/soil_moisture`)
```json
{ "sensor_id": "farm01-zoneA-soil_moisture", "type": "soil_moisture",
  "site": "farm01", "parcel": "zoneA", "value": 27.4, "unit": "%VWC",
  "battery": 92.0, "quality": "ok", "ts": "2026-06-05T08:15:00Z" }
```

**Message agrégé** (`.../processed`)
```json
{ "site": "farm01", "parcel": "zoneA", "samples": 18,
  "soil_moisture_avg": 28.1, "temperature_avg": 24.7, "rainfall_sum": 0.0,
  "soil_ph_avg": 6.3, "irrigation_needed": 1, "irrigation_minutes": 20,
  "irrigation_volume_l_m2": 1.5, "anomaly": 0, "ts": "2026-06-05T08:20:00Z" }
```

**Schéma InfluxDB**

| Measurement | Tags | Fields principaux |
|-------------|------|-------------------|
| `agri_raw` | site, parcel, type, sensor_id | value, battery |
| `agri_processed` | site, parcel | soil_moisture_avg, temperature_avg, rainfall_sum, soil_ph_avg, irrigation_needed, anomaly |

---

## 8. Scalabilité

Les `sensor-simulator` sont **sans état** : on simule davantage de capteurs en répliquant le conteneur.

```bash
make scale N=5          # 5 réplicas de simulateurs
# équivalent : docker compose -f deploy/docker-compose.yml --project-directory . up -d --scale sensor-simulator=5
```

**Load test chiffré** (débit / latence / pertes / CPU-RAM, par paliers) :

```bash
pip install paho-mqtt
make loadtest           # → tableau Markdown + CSV dans scripts/results/
```

**Orchestration Kubernetes** (Deployments, Services, ConfigMap/Secret, PVC et **HPA**
autoscaling) : voir [`deploy/k8s/`](deploy/k8s/) — `make k8s-deploy`.

Grâce aux **shared subscriptions** (`$share/...`), répliquer l'edge ou Telegraf **n'introduit pas
de doublons** : le broker répartit les messages entre instances.

Pistes complémentaires : cluster MQTT (EMQX) en prod · *retention policies* + *downsampling* InfluxDB
· HPA sur profondeur de file en plus du CPU.

---

## 9. Démonstration (soutenance)

1. `make up`, puis ouvrir Grafana → montrer les courbes temps réel se remplir.
2. Baisser `MOISTURE_THRESHOLD` dans `.env` (ex. `45`), puis recréer l'edge :
   `docker compose -f deploy/docker-compose.yml --project-directory . up -d edge-service`
   → les recommandations « IRRIGUER » apparaissent (`/api/alerts`).
3. Monter `ANOMALY_PROB` (ex. `0.2`) → anomalies détectées par l'edge (`/api/alerts`, panneau « Anomalies »).
4. `make scale N=4` → montrer la montée en charge dans les logs et Grafana.
5. `curl /api/recommend/zoneA` et `/api/predict/yield/zoneA` → montrer la couche ML.

---

## 10. Arrêt / nettoyage

```bash
make down        # arrête les conteneurs (données conservées)
make clean       # arrête + supprime les volumes (données effacées)
```

---

## 11. Arborescence

```
agri-iot-compose-k8s-cloud/
├── Makefile                    # raccourcis (up/down/demo/scale/smoke/loadtest/k8s)
├── .env.example                # configuration
│
├── services/                   # microservices applicatifs (code + Dockerfile)
│   ├── simulator/              #   capteurs émulés (Python)
│   ├── edge/                   #   edge computing : filtrage/agrégation/décision
│   └── api/                    #   API REST + ML (FastAPI, scikit-learn)
│
├── infra/                      # configuration des briques d'infrastructure
│   ├── mosquitto/config/       #   broker MQTT
│   ├── telegraf/               #   ingestion MQTT → InfluxDB
│   └── grafana/provisioning/   #   datasource + dashboard auto-provisionnés
│
├── deploy/                     # déploiement
│   ├── docker-compose.yml      #   orchestration des 7 services (dev)
│   └── k8s/                    #   manifests Kubernetes + HPA
│
└── scripts/
    ├── smoke-test.sh           # test de bout en bout
    ├── loadgen.py              # générateur de charge MQTT (débit/latence/pertes)
    └── load-test.sh            # load test chiffré par paliers (+ CPU/RAM)
```

---

## 12. Notes techniques

- **Déjà en place** : **authentification MQTT** (login/mot de passe, `allow_anonymous false`),
  **conteneurs non-root**, validation des entrées API (anti-injection Flux), arrêt propre `SIGTERM`
  (`init: true`), shared subscriptions MQTT, probes & HPA Kubernetes, provisioning Grafana,
  **rétention + downsampling InfluxDB**, rotation des logs conteneurs.
- **Rétention & downsampling** : le bucket brut `telemetry` a une rétention de `INFLUX_RETENTION`
  (30 j par défaut) ; une *task* Flux agrège chaque heure `agri_processed` vers le bucket
  `telemetry_downsampled` (rétention `INFLUX_DOWNSAMPLE_RETENTION`, 90 j). Datasource Grafana
  dédiée **InfluxDB-downsampled** pour les tendances longues. Provisionné par le service one-shot
  **`influx-init`** du `docker-compose` (et un ConfigMap inline côté Kubernetes).
- **Sécurité (dev → prod)** : l'auth MQTT est activée mais **sans TLS** ; le token InfluxDB et le
  mot de passe MQTT sont en clair dans `.env` (valeurs de démo). En production : **TLS/mTLS MQTT**,
  secrets gérés (Vault / K8s Secrets / SOPS), tokens InfluxDB *least privilege*, NetworkPolicies.
- **Modèle ML** : `services/api/train.py` génère un jeu synthétique réaliste et entraîne un
  `RandomForestRegressor` (prévision de *yield index* 0–1), entraîné au premier démarrage du
  conteneur (`entrypoint.sh`).
- **Déploiement réel** : les vrais capteurs communiqueraient via LoRaWAN relayé par un *MQTT bridge*
  logiciel — le cœur cloud-native reste inchangé.

---

## 13. Dépannage

| Symptôme | Cause | Correctif |
|----------|-------|-----------|
| `make k8s-deploy` → `kubectl: No such file or directory` | `kubectl` absent du `PATH` | L'installer (ex. dans `~/.local/bin`) puis `export PATH="$HOME/.local/bin:$PATH"` |
| `kubectl` *segfault* / `make k8s-deploy` → `Segmentation fault` | Binaire **tronqué** (téléchargement coupé) | Re-télécharger en vérifiant le `sha256sum` vs le `.sha256` officiel ; reprendre avec `curl -C -`. Aligner la version sur le cluster |
| Pods k8s en `ErrImageNeverPull` | Images locales non chargées dans le cluster | `make build` puis `kind load docker-image agri-iot-compose-k8s-cloud/<svc>:latest --name agri-iot-compose-k8s-cloud` (`imagePullPolicy: IfNotPresent`) |
| Pod `mosquitto` en `CrashLoopBackOff`, log « Unable to open file `/mosquitto/data/passwd` … File exists » | `mosquitto_passwd -c` refuse d'écraser le passwd persistant au redémarrage | Init idempotent : `rm -f /mosquitto/data/passwd` avant `mosquitto_passwd` (déjà en place) |
| Pod `mosquitto` `CrashLoopBackOff`, **exit 13** | passwd / dossier data créés en `root`, illisibles par l'utilisateur `mosquitto` | `chown -R mosquitto:mosquitto /mosquitto/data` avant `exec mosquitto` (déjà en place) |
| `telegraf` : `dial tcp …:1883: connect: connection refused` | Le broker `mosquitto` est down | Réparer `mosquitto` d'abord ; telegraf se reconnecte ensuite (`restart`/rollout) |
| `edge` en boucle « broker indisponible, nouvelle tentative dans 2s » | Conteneur `mosquitto` arrêté | Vérifier `make ps` / `$COMPOSE ps -a` puis voir la ligne suivante |
| `mosquitto` **Exited (127)** après un déplacement du projet, erreur mount « not a directory … » sur un **ancien chemin** (ex. disque externe `/media/...`) | Le conteneur garde le **bind-mount absolu figé** à sa création | Recréer le conteneur depuis le dossier courant : `$COMPOSE up -d --force-recreate mosquitto`. Après tout déplacement du projet : `make down && make up` pour recréer **tous** les conteneurs |

> Astuce diagnostic : `$COMPOSE ps -a` (conteneurs arrêtés inclus) et
> `docker inspect <conteneur> --format '{{.State.ExitCode}} {{.State.Error}}'` donnent
> la cause exacte d'un arrêt (le `mount` source apparaît aussi dans `.Mounts`).

---

## Licence

Distribué sous licence **MIT** — voir [`LICENSE`](LICENSE). Projet réalisé dans un cadre
académique (Master / S9, Cloud Computing).
