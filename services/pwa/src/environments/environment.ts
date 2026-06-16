/**
 * Environnement de développement.
 * `apiBaseUrl` pointe sur l'API FastAPI locale ; en production il est surchargé
 * au runtime (config.json injecté par Nginx) — cf. AppConfigService (Phase 3.2).
 */
export const environment = {
  production: false,
  apiBaseUrl: 'http://localhost:8000',
};
