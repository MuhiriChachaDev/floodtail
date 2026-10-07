"""Shared FastAPI dependencies (auth/tenant hooks landed in later phases)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RequestContext:
    """Placeholder request context until Keycloak/JWT middleware is wired."""

    actor: str = "anonymous"
    role: str = "underwriter"
    tenant_id: str = "default"
