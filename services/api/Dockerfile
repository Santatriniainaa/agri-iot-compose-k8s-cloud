# syntax=docker/dockerfile:1
# ─── Étape 1 : build des wheels (deps lourdes : scikit-learn, numpy) ──────────
# Compilées/téléchargées une seule fois ; cache pip BuildKit → rebuilds rapides.
FROM python:3.12-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --timeout 120 --retries 5 --wheel-dir /wheels -r requirements.txt

# ─── Étape 2 : runtime minimal ───────────────────────────────────────────────
# N'embarque que les wheels pré-construits (pas de compilateur, pas de cache pip).
FROM python:3.12-slim AS runtime

# Image légère et démarrage propre : pas de bytecode, logs non bufferisés,
# pas de cache pip ; MODEL_PATH explicite (entraînement au 1er démarrage).
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MODEL_PATH=/app/models/yield_model.pkl

WORKDIR /app
COPY requirements.txt .
COPY --from=builder /wheels /wheels
# Install hors-ligne depuis les wheels (aucun accès réseau, déterministe).
RUN pip install --no-index --find-links=/wheels -r requirements.txt \
 && rm -rf /wheels
COPY train.py app.py entrypoint.sh ./
COPY core/ ./core/
COPY services/ ./services/
COPY schemas/ ./schemas/
COPY routers/ ./routers/

# Utilisateur non privilégié + dossier modèles inscriptible par lui.
RUN chmod +x entrypoint.sh \
 && useradd --create-home --uid 10001 appuser \
 && mkdir -p /app/models \
 && chown -R appuser:appuser /app/models
USER appuser

EXPOSE 8000
# Sonde de vivacité sans dépendance externe (curl absent de l'image slim).
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

# entrypoint : entraîne le modèle ML (si absent) puis lance l'API
ENTRYPOINT ["./entrypoint.sh"]
