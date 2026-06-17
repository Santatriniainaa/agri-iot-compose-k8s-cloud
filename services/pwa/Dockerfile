# syntax=docker/dockerfile:1
# --- Étape 1 : build Angular (production) -------------------------------------
FROM node:20-alpine AS build
WORKDIR /app
# Install déterministe à partir du lockfile (couche cache séparée du code source).
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npx ng build --configuration production

# --- Étape 2 : runtime Nginx non-root -----------------------------------------
# Image « unprivileged » : worker en uid 101, écoute sur 8080 (cohérent non-root).
FROM nginxinc/nginx-unprivileged:1.27-alpine

USER root
# Artefacts navigateur (builder @angular/build → sous-dossier browser/).
COPY --from=build /app/dist/pwa/browser /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY entrypoint.sh /entrypoint.sh
# Rendre le dossier servi inscriptible par le user runtime (génération de config.json).
RUN chmod +x /entrypoint.sh \
 && chown -R 101:0 /usr/share/nginx/html \
 && chmod -R g+w /usr/share/nginx/html
USER 101

EXPOSE 8080
# 127.0.0.1 (et non localhost) : dans l'image, localhost résout d'abord en ::1 (IPv6)
# alors que nginx n'écoute qu'en IPv4 → le healthcheck échouerait à tort.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:8080/ || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
