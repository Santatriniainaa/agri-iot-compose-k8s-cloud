/**
 * Environnement de production. La valeur réelle de `apiBaseUrl` est surchargée
 * au runtime via config.json (généré par Nginx selon les variables d'environnement),
 * ce qui évite de recompiler l'image entre Compose et Kubernetes.
 */
export const environment = {
  production: true,
  apiBaseUrl: '/api-backend',
};
