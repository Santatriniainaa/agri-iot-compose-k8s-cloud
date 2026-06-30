FROM python:3.12-slim

# Image légère et démarrage propre : pas de bytecode, logs non bufferisés.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
# Cache pip BuildKit : les wheels ne sont pas re-téléchargés à chaque rebuild.
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
COPY simulator.py .

# Exécution en utilisateur non privilégié (sécurité : pas de root dans le conteneur).
RUN useradd --create-home --uid 10001 appuser
USER appuser

# Conteneur sans état : peut être répliqué pour simuler davantage de parcelles.
CMD ["python", "simulator.py"]
