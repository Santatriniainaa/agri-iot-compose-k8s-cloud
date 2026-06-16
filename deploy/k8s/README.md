# ☸️ Déploiement Kubernetes — agri-iot-compose-k8s-cloud

Déploiement orchestré de la plateforme (étape 6 du cahier des charges : **orchestration &
scalabilité**). Équivalent Kubernetes du [`docker-compose.yml`](../docker-compose.yml), enrichi de :
**HPA** (autoscaling), **probes** (liveness/readiness), **requests/limits**, **ConfigMap/Secret**,
**PVC** (stockage persistant) et **labels recommandés** `app.kubernetes.io/*`.

> Pour la vue d'ensemble du projet (architecture, services, API, ML), voir le
> [README racine](../../README.md).

---

## Sommaire

- [Contenu du dossier](#contenu-du-dossier)
- [Prérequis](#prérequis)
- [Démarrage tout-en-un](#démarrage-tout-en-un)
- [Étapes détaillées](#étapes-détaillées)
- [Accès aux services](#accès-aux-services)
- [Opérations courantes](#opérations-courantes)
- [Autoscaling & scalabilité](#autoscaling--scalabilité)
- [Ressources & probes](#ressources--probes)
- [Nettoyage](#nettoyage)
- [Dépannage](#dépannage)

---

## Contenu du dossier

| Fichier | Ressources Kubernetes |
|---------|------------------------|
| `00-namespace.yaml` | `Namespace` **agri-iot-compose-k8s-cloud** |
| `01-config.yaml` | `ConfigMap` (`…-config`) + `Secret` (`…-secret`) — config & identifiants |
| `10-mosquitto.yaml` | `ConfigMap` + `PVC` (1Gi) + `Deployment` + `Service` (broker MQTT) |
| `20-influxdb.yaml` | `ConfigMap` (init Flux) + `PVC` (5Gi) + `Deployment` + `Service` (time-series) |
| `30-telegraf.yaml` | `ConfigMap` + `Deployment` (ingestion MQTT→Influx) |
| `40-edge-service.yaml` | `Deployment` + `Service` (headless) + **`HPA` 1→8** (edge, stateless) |
| `50-sensor-simulator.yaml` | `Deployment` (capteurs, scalable manuellement) |
| `60-api-service.yaml` | `Deployment` + `Service` (NodePort `30800`) + **`HPA` 1→6** (API+ML) |
| `65-grafana-provisioning.yaml` | `ConfigMap` datasources + dashboard (provisioning Grafana) |
| `70-grafana.yaml` | `PVC` (1Gi) + `Deployment` + `Service` (NodePort `30300`) |
| `kustomization.yaml` | Agrège le tout, fixe le namespace + les labels recommandés |
| `kind-config.yaml` | Config du cluster kind (nom + NodePorts mappés sur l'hôte) |

**Configuration centralisée** : tous les services lisent leurs paramètres non sensibles depuis le
`ConfigMap` `agri-iot-compose-k8s-cloud-config` et leurs secrets (tokens, mots de passe) depuis le
`Secret` `agri-iot-compose-k8s-cloud-secret` — jamais en dur dans les manifests applicatifs.

---

## Prérequis

| Outil | Rôle |
|-------|------|
| **kubectl** (≥ 1.27) | pilotage du cluster ; embarque `kustomize` (`kubectl -k`) |
| **kind** | cluster local jetable (minikube / k3d fonctionnent aussi) |
| **Docker** | build des images applicatives |
| **metrics-server** | métriques CPU requises par les **HPA** — installé par `make k8s-metrics` |

> Le flux `make` ci-dessous cible **kind**. Garder un *skew* d'au plus ±1 mineure entre `kubectl` et
> le cluster.

---

## Démarrage tout-en-un

Depuis la **racine du dépôt** :

```bash
make k8s-up
```

Cette cible enchaîne, de façon idempotente :

1. **`make k8s-cluster`** — crée le cluster kind **`agri-iot-compose-k8s-cloud`** (via
   [`kind-config.yaml`](kind-config.yaml)) → nœud `agri-iot-compose-k8s-cloud-control-plane`.
2. **`make k8s-metrics`** — installe metrics-server (+ patch `--kubelet-insecure-tls`, requis sur kind).
3. **`make k8s-load`** — `make build` (images taguées `agri-iot-compose-k8s-cloud/<svc>:latest`,
   partagées avec Compose) puis `kind load` des 3 images applicatives (pas de registry requis).
4. **`make k8s-warmup`** — pré-tire les images tierces (`mosquitto`, `influxdb`, `telegraf`,
   `grafana`) **dans le nœud** avec retries → évite les `ImagePullBackOff` dus à un Docker Hub
   flaky/rate-limité au moment du déploiement.
5. **`make k8s-deploy`** — `kubectl apply -k deploy/k8s/`.

Suivi :

```bash
make k8s-status                                      # pods (-o wide) + services + HPA
kubectl -n agri-iot-compose-k8s-cloud get pods -w    # attendre Running/Ready
```

---

## Étapes détaillées

Chaque étape de `make k8s-up` reste disponible séparément :

```bash
make k8s-cluster        # kind create cluster --config deploy/k8s/kind-config.yaml
make k8s-metrics        # metrics-server + patch kubelet-insecure-tls
make k8s-load           # make build + kind load des 3 images applicatives
make k8s-warmup         # pré-pull des images tierces dans le nœud (anti-ImagePullBackOff)
make k8s-deploy         # kubectl apply -k deploy/k8s
```

> **Pourquoi `kind load` ?** `imagePullPolicy: IfNotPresent` + images locales non publiées : sans
> chargement dans le cluster, les pods tombent en `ErrImageNeverPull`.
>
> **Pourquoi `k8s-warmup` (et pas `kind load`) pour les images tierces ?** Le *containerd image
> store* de Docker produit des archives incomplètes que `ctr import` rejette (`content digest not
> found`) — `kind load docker-image` est donc inutilisable. On fait plutôt **puller le nœud
> directement** (`crictl pull`, avec retries) : fiable, et indépendant des couches locales de l'hôte.

---

## Accès aux services

Avec kind, les NodePort sont **mappés directement sur l'hôte** ([`kind-config.yaml`](kind-config.yaml)) :

| Service | URL | Identifiants |
|---------|-----|--------------|
| API (Swagger) | http://localhost:30800/docs | — |
| Grafana | http://localhost:30300 | `admin` / `${GRAFANA_PASSWORD}` |

Alternative par *port-forward* (ports décalés `3001`/`8001` pour éviter le conflit avec Compose) :

```bash
make k8s-forward        # Grafana :3001 · API :8001 (Ctrl+C arrête les deux)
```

---

## Opérations courantes

Cibles `make` pour piloter les déploiements sans retenir les commandes `kubectl` (depuis la **racine du
dépôt**). `S=` cible **un** déploiement ; vide ⇒ **tous**. `make k8s-deploys` liste les noms valides
(`mosquitto`, `influxdb`, `telegraf`, `edge-service`, `sensor-simulator`, `api-service`, `grafana`).

| Commande | Effet | Équivalent `kubectl` |
|----------|-------|----------------------|
| `make k8s-deploys` | Liste les déploiements du namespace | `get deploy` |
| `make k8s-start [S=deploy] [N=1]` | Scale à `N` (défaut 1) — démarre / scale *out* | `scale deploy/… --replicas=N` |
| `make k8s-stop [S=deploy]` | Scale à 0 — arrête | `scale deploy/… --replicas=0` |
| `make k8s-restart [S=deploy]` | Redémarrage progressif (*rolling*, sans coupure) | `rollout restart deploy/…` |
| `make k8s-logs S=deploy` | Suit les logs d'un déploiement | `logs -f deploy/…` |

```bash
make k8s-deploys                       # voir les déploiements + leur état (READY)
make k8s-restart S=edge-service        # rolling restart d'un déploiement
make k8s-logs S=api-service            # suivre les logs (Ctrl+C pour arrêter)
make k8s-stop S=grafana                # arrêter grafana ; make k8s-start S=grafana pour relancer
```

> ⚠️ `make k8s-stop` scale à 0, mais **`edge-service`** et **`api-service`** ont un `HPA`
> (`minReplicas: 1`) qui les **relance aussitôt**. Pour les figer réellement : supprimer leur HPA ou
> faire `make k8s-delete`. Les déploiements sans HPA (`grafana`, `telegraf`, `sensor-simulator`,
> `mosquitto`, `influxdb`) s'arrêtent proprement.

---

## Autoscaling & scalabilité

| Charge de travail | HPA | Cible | Note |
|-------------------|-----|-------|------|
| `edge-service` | **1 → 8** réplicas | CPU 65 % | stateless + *shared subscription* → pas de doublons |
| `api-service` | **1 → 6** réplicas | CPU 65 % | API REST/ML sans état |
| `sensor-simulator` | manuel | — | `make k8s-start S=sensor-simulator N=…` (générateur de charge) |

```bash
# Générer de la charge : plus de capteurs (raccourci make ⇄ kubectl)
make k8s-start S=sensor-simulator N=5
# équivaut à : kubectl -n agri-iot-compose-k8s-cloud scale deploy/sensor-simulator --replicas=5

# Observer l'autoscaling de l'edge sous charge
kubectl -n agri-iot-compose-k8s-cloud get hpa -w
kubectl -n agri-iot-compose-k8s-cloud top pods        # nécessite metrics-server
```

Grâce aux **shared subscriptions** MQTT (`$share/…`), répliquer l'edge ou Telegraf n'introduit **pas
de doublons** : le broker répartit les messages entre instances. Le load-test chiffré (débit, latence,
pertes, CPU/RAM) est fourni par [`../../scripts/load-test.sh`](../../scripts/load-test.sh) (`make loadtest`).

---

## Ressources & probes

`requests`/`limits` définis sur chaque pod (base du calcul HPA + protection du nœud) :

| Pod | requests (cpu/mem) | limits (cpu/mem) |
|-----|--------------------|------------------|
| `edge-service` | 100m / 64Mi | 500m / 256Mi |
| `api-service` | 100m / 256Mi | 1 / 512Mi |
| `sensor-simulator` | 50m / 64Mi | 250m / 128Mi |
| `mosquitto` | 50m / 64Mi | 250m / 128Mi |
| `influxdb` | 100m / 256Mi | 1 / 1Gi |

**Probes** : `mosquitto`, `influxdb`, `api-service` et `grafana` exposent des *readiness/liveness
probes* (TCP ou HTTP `/health` · `/api/health`) — Kubernetes ne route le trafic que vers les pods prêts
et redémarre les pods bloqués.

**Stockage persistant (PVC)** : `mosquitto-data` (1Gi), `influxdb-data` (5Gi), `grafana-data` (1Gi) —
les données survivent au redémarrage des pods. `mosquitto` et `influxdb` restent à **1 réplica**
(*stateful*).

---

## Nettoyage

```bash
make k8s-delete            # kubectl delete -k deploy/k8s/ (supprime les ressources, garde le cluster)
make k8s-cluster-delete    # kind delete cluster --name agri-iot-compose-k8s-cloud
```

---

## Dépannage

| Symptôme | Cause | Correctif |
|----------|-------|-----------|
| Pods applicatifs `ErrImageNeverPull` | images locales non chargées | `make k8s-load` |
| Pods tiers (`mosquitto`/`grafana`/…) `ImagePullBackOff` (`EOF` Docker Hub) | pull Docker Hub flaky/rate-limité | `make k8s-warmup` puis `kubectl -n … delete pod -l app=<svc>-agri-iot-compose-k8s-cloud` (kubelet réessaie aussi seul) |
| `HPA <unknown>/65%` | metrics-server absent ou non patché | `make k8s-metrics` puis attendre ~1 min |
| `mosquitto` `CrashLoopBackOff` (exit 13) | `/mosquitto/data` créé en root | `chown` avant `exec mosquitto` (déjà en place) |
| `telegraf` `connection refused :1883` | broker pas encore prêt | se reconnecte seul ; sinon `kubectl rollout restart deploy/telegraf` |
| Pods `Pending` | PVC non liés / ressources insuffisantes | `kubectl describe pod …` ; vérifier le *storage class* par défaut |

```bash
kubectl -n agri-iot-compose-k8s-cloud describe pod -l app=mosquitto-agri-iot-compose-k8s-cloud
kubectl -n agri-iot-compose-k8s-cloud logs -f deploy/edge-service
```

> ⚠️ **Sécurité (démo).** Le `Secret` contient des valeurs en clair ; l'auth MQTT est activée mais
> **sans TLS**. En production : gestionnaire de secrets (Vault / Sealed Secrets), TLS/mTLS MQTT,
> `NetworkPolicies`, tokens InfluxDB à privilèges réduits.
