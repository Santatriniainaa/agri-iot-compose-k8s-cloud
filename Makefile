# ─── agri-iot-compose-k8s-cloud — raccourcis ───────────────────────────────────────────────
# Usage : make up | make down | make logs | make demo | make scale N=3 | make clean
# Lancer depuis le dossier agri-iot-compose-k8s-cloud/.

# Le fichier compose est sous deploy/ ; --project-directory . garde les chemins
# ./services et ./infra relatifs à agri-iot-compose-k8s-cloud/ et charge .env depuis ici.
COMPOSE = docker compose -f deploy/docker-compose.yml --project-directory .
K8S      = deploy/k8s
CLUSTER  = agri-iot-compose-k8s-cloud
NS       = agri-iot-compose-k8s-cloud
NODE     = $(CLUSTER)-control-plane
IMAGES   = edge-service sensor-simulator api-service
# Images tierces (broker, base, ingestion, visualisation) — pré-tirées dans le nœud.
DEPS_IMAGES = eclipse-mosquitto:2 influxdb:2.7 telegraf:1.30 grafana/grafana:11.1.0

.PHONY: help up down build rebuild start stop restart logs ps services demo smoke scale loadtest \
        k8s-cluster k8s-metrics k8s-load k8s-warmup k8s-deploy k8s-up k8s-status k8s-deploys k8s-forward \
        k8s-start k8s-stop k8s-restart k8s-logs k8s-delete k8s-cluster-delete clean

help:
	@echo "Cibles disponibles :"
	@echo "  make up       - construit et démarre toute la plateforme"
	@echo "  make down     - arrête la plateforme"
	@echo "  make build    - (re)construit les images"
	@echo "  make ps       - état des conteneurs"
	@echo "  make services - liste les services compose (valeurs valides pour S=)"
	@echo "  make start [S=svc]   - démarre un service (ou tous si S vide)"
	@echo "  make stop  [S=svc]   - arrête un service (ou tous si S vide)"
	@echo "  make restart [S=svc] - redémarre un service (ou tous si S vide)"
	@echo "  make logs  [S=svc]   - suit les logs d'un service (défaut: edge-service)"
	@echo "  make demo     - interroge l'API (parcelles, recommandation, alertes)"
	@echo "  make smoke    - test de bout en bout automatisé"
	@echo "  make scale N=5- réplique les sensor-simulators (scaling horizontal)"
	@echo "  make loadtest - load test chiffré (débit/latence/pertes/CPU)"
	@echo "  --- Kubernetes (cluster kind « $(CLUSTER) ») ---"
	@echo "  make k8s-up      - cluster + metrics-server + build/load images + déploie (tout-en-un)"
	@echo "  make k8s-cluster - crée le cluster kind (deploy/k8s/kind-config.yaml)"
	@echo "  make k8s-load    - construit et charge les images locales dans le cluster"
	@echo "  make k8s-warmup  - pré-tire les images tierces dans le nœud (anti-ImagePullBackOff)"
	@echo "  make k8s-deploy  - applique les manifests (kubectl apply -k deploy/k8s)"
	@echo "  make k8s-status  - état des pods / services / HPA du namespace"
	@echo "  make k8s-deploys - liste les déploiements (valeurs valides pour S=)"
	@echo "  make k8s-start [S=deploy] [N=1] - scale à N (déf.1) un déploiement (ou tous)"
	@echo "  make k8s-stop  [S=deploy]       - scale à 0 (ou tous) — edge/api: HPA min=1 relance"
	@echo "  make k8s-restart [S=deploy]     - rollout restart (ou tous)"
	@echo "  make k8s-logs S=deploy          - suit les logs d'un déploiement"
	@echo "  make k8s-forward - expose Grafana (3001) + API (8001) en local (port-forward)"
	@echo "  make k8s-delete  - supprime les ressources (garde le cluster)"
	@echo "  make k8s-cluster-delete - supprime le cluster kind"
	@echo "  make clean    - arrête tout et supprime les volumes (données effacées)"

up:
	@test -f .env || cp .env.example .env
	$(COMPOSE) up -d --build
	@echo "\n✅ agri-iot-compose-k8s-cloud démarré."
	@echo "   • API     : http://localhost:8000/docs"
	@echo "   • Grafana : http://localhost:3000  (admin / agri-iot-compose-k8s-cloud)"
	@echo "   • InfluxDB: http://localhost:8086"

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

rebuild:
	$(COMPOSE) build --no-cache

# ─── Cycle de vie par service (compose) ────────────────────────────────────
# S sélectionne UN service ; S vide ⇒ tous les services. Les conteneurs doivent
# déjà exister (créés par `make up`). Ex. : make stop S=grafana · make restart
start:
	$(COMPOSE) start $(S)

stop:
	$(COMPOSE) stop $(S)

restart:
	$(COMPOSE) restart $(S)

# Logs d'un service (suivi). S vide ⇒ edge-service par défaut.
# Ex. : make logs S=api-service · make logs S=mosquitto
logs:
	$(COMPOSE) logs -f --tail=100 $(if $(S),$(S),edge-service)

ps:
	$(COMPOSE) ps

# Liste les services définis dans le compose — valeurs valides pour S=
# (start / stop / restart / logs). Fonctionne stack arrêtée comme démarrée.
services:
	@$(COMPOSE) config --services | sort

demo:
	@echo "→ Parcelles :"      && curl -s http://localhost:8000/api/parcels        | python3 -m json.tool || true
	@echo "→ Recommandation :" && curl -s http://localhost:8000/api/recommend/zoneA | python3 -m json.tool || true
	@echo "→ Alertes :"        && curl -s http://localhost:8000/api/alerts          | python3 -m json.tool || true

smoke:
	./scripts/smoke-test.sh

scale:
	$(COMPOSE) up -d --scale sensor-simulator=$(N)

loadtest:
	./scripts/load-test.sh

# Crée le cluster kind nommé « $(CLUSTER) » → nœud $(CLUSTER)-control-plane.
# Idempotent : ne recrée pas un cluster déjà présent.
k8s-cluster:
	@kind get clusters 2>/dev/null | grep -qx $(CLUSTER) \
		&& echo "✓ cluster « $(CLUSTER) » déjà présent" \
		|| kind create cluster --config $(K8S)/kind-config.yaml

# metrics-server (requis par les HPA). Patch --kubelet-insecure-tls : obligatoire sur kind.
k8s-metrics:
	kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
	kubectl -n kube-system patch deployment metrics-server --type=json \
		-p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
	kubectl -n kube-system rollout status deployment/metrics-server

# Construit les images applicatives (tags partagés avec compose) et les charge dans le cluster.
k8s-load: build
	@for i in $(IMAGES); do \
		echo "→ kind load $(CLUSTER)/$$i:latest"; \
		kind load docker-image $(CLUSTER)/$$i:latest --name $(CLUSTER); \
	done

# Pré-tire les images tierces DANS le nœud kind (containerd), avec retries.
# Évite les ImagePullBackOff dus à un Docker Hub flaky/rate-limité au moment du
# `kubectl apply`. NB : `kind load docker-image` est inutilisable ici car le
# containerd image store de Docker produit des archives incomplètes pour ctr.
k8s-warmup:
	@for img in $(DEPS_IMAGES); do \
		printf "→ pré-pull %s\n" "$$img"; \
		n=0; until docker exec $(NODE) crictl pull "$$img" >/dev/null 2>&1; do \
			n=$$((n+1)); \
			if [ $$n -ge 5 ]; then echo "  ⚠ échec après 5 tentatives — kubelet réessaiera"; break; fi; \
			echo "  Docker Hub injoignable, retry $$n/5..."; sleep 3; \
		done; \
	done

k8s-deploy:
	kubectl apply -k $(K8S)
	kubectl -n $(NS) rollout status deploy/api-service --timeout=120s || true

# Tout-en-un : cluster → metrics-server → images applicatives → images tierces → manifests.
k8s-up: k8s-cluster k8s-metrics k8s-load k8s-warmup k8s-deploy
	@echo "\n✅ Stack déployée sur le cluster kind « $(CLUSTER) »."
	@echo "   • API     : http://localhost:30800/docs"
	@echo "   • Grafana : http://localhost:30300  (admin / agri-iot-compose-k8s-cloud)"
	@$(MAKE) --no-print-directory k8s-status

k8s-status:
	@kubectl -n $(NS) get pods -o wide
	@kubectl -n $(NS) get svc
	@kubectl -n $(NS) get hpa

# Liste les déploiements du namespace — valeurs valides pour S=
# (k8s-start / k8s-stop / k8s-restart / k8s-logs).
k8s-deploys:
	@kubectl -n $(NS) get deploy

# ─── Cycle de vie par déploiement (k8s) ─────────────────────────────────────
# S sélectionne UN déploiement ; S vide ⇒ tous (--all). Déploiements valides :
# mosquitto influxdb telegraf edge-service sensor-simulator api-service grafana

# Démarre/relance : scale à N réplicas (défaut 1). Ex. : make k8s-start S=sensor-simulator N=4
k8s-start:
	@if [ -n "$(S)" ]; then \
		kubectl -n $(NS) scale deploy/$(S) --replicas=$(if $(N),$(N),1); \
	else \
		kubectl -n $(NS) scale deploy --all --replicas=$(if $(N),$(N),1); \
	fi
	@kubectl -n $(NS) get deploy

# Arrête : scale à 0. NB : edge-service et api-service ont un HPA (min=1) qui les
# relance ; pour les figer réellement, supprimer leur HPA ou faire `make k8s-delete`.
k8s-stop:
	@if [ -n "$(S)" ]; then \
		kubectl -n $(NS) scale deploy/$(S) --replicas=0; \
	else \
		kubectl -n $(NS) scale deploy --all --replicas=0; \
	fi
	@echo "ℹ HPA (edge-service, api-service, min=1) : ces déploiements se relancent."
	@kubectl -n $(NS) get deploy

# Redémarrage progressif (rolling) sans coupure. S vide ⇒ tous les déploiements.
k8s-restart:
	@if [ -n "$(S)" ]; then \
		kubectl -n $(NS) rollout restart deploy/$(S); \
		kubectl -n $(NS) rollout status deploy/$(S) --timeout=120s; \
	else \
		kubectl -n $(NS) rollout restart deploy; \
		echo "→ rollout restart lancé sur tous les déploiements"; \
	fi

# Logs d'un déploiement (suivi). S requis. Ex. : make k8s-logs S=api-service
k8s-logs:
	@test -n "$(S)" || { echo "Usage : make k8s-logs S=<edge-service|api-service|sensor-simulator|telegraf|mosquitto|influxdb|grafana>"; exit 2; }
	kubectl -n $(NS) logs -f --tail=100 deploy/$(S)

# Expose Grafana + API du cluster en local (port-forward). Ports décalés (3001 / 8001)
# pour éviter le conflit avec la stack docker-compose (3000 / 8000). Ctrl+C arrête tout.
# Alternative : les NodePort sont déjà mappés sur l'hôte (30800 / 30300) via kind-config.yaml.
k8s-forward:
	@echo "→ Grafana : http://localhost:3001  (admin / agri-iot-compose-k8s-cloud)"
	@echo "→ API     : http://localhost:8001/docs"
	@echo "  (Ctrl+C pour arrêter les deux)"
	@trap 'kill 0' EXIT; \
	kubectl -n $(NS) port-forward svc/grafana 3001:3000 & \
	kubectl -n $(NS) port-forward svc/api-service 8001:8000 & \
	wait

k8s-delete:
	kubectl delete -k $(K8S)

k8s-cluster-delete:
	kind delete cluster --name $(CLUSTER)

clean:
	$(COMPOSE) down -v
