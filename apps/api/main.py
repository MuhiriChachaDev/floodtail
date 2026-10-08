"""FLOODTAIL — Flood CAT API entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routers import (
    audit,
    explanations,
    health,
    insight,
    knowledge,
    memory,
    models,
    portfolios,
    query,
    runs,
    vulnerability,
)
from apps.api.settings import get_settings

_settings = get_settings()
_show_docs = _settings.docs_enabled

app = FastAPI(
    title="FLOODTAIL Flood CAT API",
    version="0.1.0-phase-f",
    description=(
        "Location-flexible flood catastrophe backend for reinsurance underwriters. "
        "Agentic LangGraph orchestration + predictive ML + grounded EP/capital math. "
        "Phase F: E2E hardening — health/registry readiness, integration test, insight demo."
    ),
    docs_url="/docs" if _show_docs else None,
    redoc_url="/redoc" if _show_docs else None,
    openapi_url="/openapi.json" if _show_docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.parsed_cors_origins(),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Authorization",
        "Content-Type",
        "X-Floodtail-Role",
        "X-Floodtail-Actor",
        "X-Floodtail-Tenant",
        "X-Request-Id",
    ],
    allow_credentials=False,
    max_age=600,
)

app.include_router(health.router, prefix="/v1", tags=["health"])
app.include_router(portfolios.router, prefix="/v1", tags=["portfolios"])
app.include_router(runs.router, prefix="/v1", tags=["runs"])
app.include_router(insight.router, prefix="/v1", tags=["insight"])
app.include_router(models.router, prefix="/v1", tags=["models"])
app.include_router(explanations.router, prefix="/v1", tags=["explanations"])
app.include_router(query.router, prefix="/v1", tags=["query"])
app.include_router(knowledge.router, prefix="/v1", tags=["knowledge"])
app.include_router(memory.router, prefix="/v1", tags=["memory"])
app.include_router(audit.router, prefix="/v1", tags=["audit"])
app.include_router(vulnerability.router, prefix="/v1", tags=["vulnerability"])


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
