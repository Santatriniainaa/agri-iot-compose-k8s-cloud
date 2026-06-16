#!/usr/bin/env python3
"""agri-iot-compose-k8s-cloud — API / ML service (FastAPI).

Assemble l'application : configuration du lifespan (modèle ML + souscription MQTT),
CORS pour la PWA, et montage des routers.

La logique est répartie en packages :
  - core/     : configuration, accès InfluxDB, MQTT, modèle ML, validation ;
  - services/ : logique métier (recommandation, vue d'ensemble) ;
  - schemas/  : schémas Pydantic (contrat OpenAPI) ;
  - routers/  : endpoints HTTP.

Le router métier est monté sous `/api/v1` (surface versionnée, cible PWA) et,
en alias rétro-compatible, sous `/api` (Grafana, scripts, `make smoke`).

Docs interactives : http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core import config, ml, mqtt
from routers import api as api_router
from routers import meta as meta_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    ml.load_model()
    mqtt.start()
    yield
    mqtt.stop()


app = FastAPI(title="agri-iot-compose-k8s-cloud API", version="1.0.0", lifespan=lifespan)

# CORS — la PWA est un client navigateur servi depuis une autre origine.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoints transverses (accueil, santé).
app.include_router(meta_router.router)

# Router métier : surface versionnée + alias rétro-compatible.
app.include_router(api_router.router, prefix="/api/v1")
app.include_router(api_router.router, prefix="/api", include_in_schema=False)
