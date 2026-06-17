# PWA mobile — Agri-IoT

Application **mobile-first** (Angular 20, standalone + lazy-loading) de supervision des
parcelles : tableau de bord, détail parcelle (recommandation d'irrigation + rendement ML +
historique), alertes. Installable et utilisable hors-ligne (service worker).

Voir l'[ADR 0001](../../docs/adr/0001-pwa-mobile-angular-et-api-v1.md) pour le contexte et les
décisions d'architecture.

## Architecture

```
src/app/
  core/
    config/      AppConfigService — résout l'URL de l'API au runtime (config.json)
    guards/      authGuard — protège la zone authentifiée
    interceptors/auth.interceptor — ajoute le Bearer JWT, gère le 401
    models/      api.models.ts — contrat typé aligné sur les schémas Pydantic
    services/    ApiService (client /api/v1), AuthService (JWT), ConnectivityService
  features/      login, home (accueil), dashboard (parcelles), parcel-detail,
                 weather (météo), alerts — composants lazy
  layout/        shell — en-tête, navigation basse 4 onglets, bannières offline/maj
  shared/        line-chart — mini-graphe SVG sans dépendance
```

Navigation (barre basse, icônes **Angular Material** auto-hébergées) :

| Onglet | Route | Contenu |
|--------|-------|---------|
| Accueil | `/` | Météo du site + KPIs parcelles + accès alertes |
| Parcelles | `/parcels` | Liste des parcelles (→ détail, recommandation, historique) |
| Météo | `/weather` | Conditions courantes (Open-Meteo) |
| Alertes | `/alerts` | Alertes récentes (MQTT) |

- **Configuration runtime** : `AppConfigService.load()` (app initializer) lit `config.json`
  (généré par Nginx depuis `API_BASE_URL`). La **même image** sert en Compose et en Kubernetes
  sans recompilation. En `ng serve`, on retombe sur `environments/environment.ts`.
- **Authentification** : OAuth2 password flow → JWT persisté en `localStorage` ; signal
  `isAuthenticated` réactif. `authGuard` redirige vers `/login` (avec `returnUrl`).
- **Offline** : le service worker (`ngsw-config.json`) précharge l'app-shell et met en cache
  les réponses `GET /api/v1/**` et `/health` en stratégie **freshness** (réseau d'abord,
  bascule sur le cache après 5 s ou hors-ligne). La bannière « Hors-ligne — données en cache »
  s'appuie sur ce cache.

## Développement

```bash
npm install
npm start          # ng serve → http://localhost:4200 (API attendue sur http://localhost:8000)
npm run build      # build de production (dist/pwa/browser)
npm test           # tests unitaires (Vitest + jsdom, single run)
```

Identifiants de démonstration (configurables côté API via `API_AUTH_USER` / `API_AUTH_PASSWORD`,
cf. `.env.example`) : `agri` / `agri-iot-demo`.

> En `ng serve`, le service worker est désactivé (cf. configuration `development` d'`angular.json`).
> Pour tester l'offline, utilisez un build de production servi par un serveur statique ou l'image Docker.

## Tests

Suite **Vitest** (builder expérimental `@angular/build:unit-test`, environnement jsdom) :
services (`ApiService`, `AuthService`), `authGuard`, `auth.interceptor` et composants
(`LineChartComponent`, `WeatherComponent`).

```bash
npm test           # ou : ng test --no-watch · make test-pwa (en conteneur)
```

## Conteneurisation

`Dockerfile` multi-stage : build Node 20-alpine → service par **Nginx non-root** (`nginxinc/nginx-unprivileged`,
écoute sur `:8080`). `entrypoint.sh` génère `config.json` au démarrage à partir de `API_BASE_URL`.

```bash
docker build -t agri-iot-compose-k8s-cloud/pwa:latest .
docker run --rm -p 8080:8080 -e API_BASE_URL=http://localhost:8000 \
  agri-iot-compose-k8s-cloud/pwa:latest
```

## Déploiement

- **Docker Compose** : service `pwa` (cf. `deploy/docker-compose.yml`), `PWA_API_BASE_URL`
  injecté dans `config.json`.
- **Kubernetes** : `Deployment` + `Service` + `HPA` (`deploy/k8s/80-pwa.yaml`) et `Ingress`
  (`deploy/k8s/90-ingress.yaml`) servant PWA (`/`) et API (`/api-backend`) en **même origine**.

## Contrat API consommé (`/api/v1`)

| Écran          | Endpoints |
|----------------|-----------|
| Login          | `POST /auth/login` |
| Accueil        | `GET /overview`, `GET /weather`, `GET /alerts` |
| Parcelles      | `GET /overview` |
| Détail parcelle| `GET /recommend/{parcel}`, `GET /history/{parcel}?metric&range` |
| Météo          | `GET /weather` |
| Alertes        | `GET /alerts?limit` |
| Santé          | `GET /health` |
