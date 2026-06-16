# ADR 0001 — PWA mobile Angular + évolution de l'API (v1)

- **Statut** : Accepté
- **Date** : 2026-06-16
- **Branche** : `feature/pwa-angular-mobile`

## Contexte

La plateforme expose aujourd'hui une **API REST FastAPI** (`services/api`) en lecture seule,
pensée pour la consommation par **Grafana** et **Swagger** : pas de CORS, pas d'endpoint
agrégé « vue d'ensemble », réponses non typées par des schémas, fichier `app.py` monolithique.

On souhaite offrir aux exploitants une **application mobile** (PWA Angular) permettant de
consulter l'état des parcelles, l'historique des métriques, les recommandations d'irrigation,
la prévision de rendement ML et les alertes — depuis un téléphone, en situation terrain.

Une PWA est un client **navigateur** : elle impose donc des contraintes que l'API actuelle ne
satisfait pas (CORS, payloads adaptés au mobile, authentification, contrat typé).

## Décision

### Frontend — `services/pwa`
- **Angular 20.x** (standalone components, lazy-loading), **PWA activée** via
  `@angular/service-worker` (manifest + service worker, app-shell offline).
- Architecture **mobile-first**, découpée en `core/` (services, intercepteurs, guards),
  `features/` (dashboard, détail parcelle, alertes, login) et `shared/`.
- Couche d'accès API **typée** alignée sur les schémas Pydantic du backend.
- Build **Node 20-alpine** → image servie par **Nginx** (Dockerfile multi-stage).
- **Configuration au runtime** (injectée par Nginx au démarrage) pour ne pas recompiler
  l'image entre Compose et Kubernetes.

### Backend — API v1
- **Refactor** de `app.py` en packages : `core/` (config, influx, mqtt, ml),
  `security/` (JWT), `schemas/` (Pydantic), `routers/` (parcels, recommend, alerts,
  overview, auth). Assemblage dans `app.py`.
- **Versioning** : nouvelles routes sous `/api/v1`. Les routes `/api/*` historiques restent
  montées (alias) pour ne rien casser pendant la migration (Grafana, scripts, `make smoke`).
- **CORS** : `CORSMiddleware` configurable par variable d'environnement `CORS_ORIGINS`.
- **Endpoint agrégé** `GET /api/v1/overview` : tous les KPI de toutes les parcelles en
  **un seul appel** (économie réseau cruciale en mobile / réseau dégradé).
- **Schémas Pydantic** typés pour des réponses propres et un contrat exploitable côté client.

### Sécurité
- **JWT léger** (`OAuth2` password flow) : un utilisateur de démonstration paramétré par
  variable d'environnement. Les endpoints de données sont protégés ; `/health` et `/docs`
  restent publics. Côté Angular : `AuthGuard` + `HttpInterceptor` portant le jeton.
- Cohérent avec la **posture démo** du projet (pas de TLS, secrets en `.env`) — le
  durcissement production (TLS/mTLS, secrets gérés) reste en feuille de route.

### Déploiement
- **Docker Compose** : ajout d'un service `pwa`.
- **Kubernetes** : `Deployment` + `Service` + `HPA` pour la PWA, **Ingress** routant API et
  PWA, NodePort pour la démo (`kind`).

## Conséquences

- **Positif** : application mobile installable et hors-ligne ; API au contrat clair, versionnée,
  consommable par d'autres clients ; séparation transport / domaine / accès données facilitant
  les tests et l'évolution.
- **Coût** : surface de code accrue (front + back) ; un service supplémentaire à conteneuriser
  et déployer ; introduction d'une dépendance d'auth.
- **Rétro-compatibilité** : aucune rupture — les routes `/api/*` et le pipeline Grafana/`smoke`
  continuent de fonctionner pendant et après la migration.

## Plan de livraison (phases → commits)

| Phase | Objet | Commits |
|-------|-------|---------|
| 0 | Cadrage (cet ADR + README) | 1 |
| 1 | Refactor API en packages + schémas + versioning + CORS + `/overview` | 3–4 |
| 2 | Authentification JWT | 2 |
| 3 | Bootstrap PWA Angular (scaffold + couche API/auth) | 2 |
| 4 | Écrans mobile (login, dashboard, détail, alertes, offline) | 3 |
| 5 | Conteneurisation & déploiement (Dockerfile, Compose, k8s, Ingress) | 3 |
| 6 | Tests (pytest API) + documentation | 2 |

Chaque phase est livrée et validée indépendamment avant de passer à la suivante.
