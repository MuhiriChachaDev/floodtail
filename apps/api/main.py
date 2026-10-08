"""FLOODTAIL — Flood CAT API entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routers import (
    audit,
    explanations,
    health,
    insight,
    models,
    portfolios,
    query,
    runs,
)
from apps.api.settings import get_settings

_settings = get_settings()

app = FastAPI(
    title="FLOODTAIL Flood CAT API",
    version="0.1.0-phase-f",
    description=(
        "Location-flexible flood catastrophe backend for reinsurance underwriters. "
        "Agentic LangGraph orchestration + predictive ML + grounded EP/capital math. "
        "Phase F: E2E hardening — health/registry readiness, integration test, insight demo."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/v1", tags=["health"])
app.include_router(portfolios.router, prefix="/v1", tags=["portfolios"])
app.include_router(runs.router, prefix="/v1", tags=["runs"])
app.include_router(insight.router, prefix="/v1", tags=["insight"])
app.include_router(models.router, prefix="/v1", tags=["models"])
app.include_router(explanations.router, prefix="/v1", tags=["explanations"])
app.include_router(query.router, prefix="/v1", tags=["query"])
app.include_router(audit.router, prefix="/v1", tags=["audit"])


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "floodtail-api",
        "status": "phase-f",
        "phase": "F",
        "docs": "/docs",
        "health": "/v1/health",
        "assumptions_version": _settings.assumptions_version,
    }
