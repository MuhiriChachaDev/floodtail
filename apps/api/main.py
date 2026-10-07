"""FLOODTAIL — Nairobi Urban Flood CAT API entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routers import health

app = FastAPI(
    title="FLOODTAIL Nairobi Flood CAT API",
    version="0.1.0-scaffold",
    description=(
        "AI/ML + agentic flood catastrophe model for Nairobi pluvial risk. "
        "Deterministic financial/EP core; trained hazard & vulnerability models; "
        "Ollama agents with kenyaRE-style security."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/v1", tags=["health"])


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "floodtail-api",
        "status": "scaffold",
        "docs": "/docs",
        "health": "/v1/health",
    }
