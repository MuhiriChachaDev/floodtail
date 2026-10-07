"""Shared FastAPI dependencies (auth/tenant hooks landed in later phases)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from apps.api.settings import Settings, get_settings
from apps.api.store import InMemoryStore, get_store


@dataclass(frozen=True)
class RequestContext:
    """Placeholder request context until Keycloak/JWT middleware is wired."""

    actor: str = "anonymous"
    role: str = "underwriter"
    tenant_id: str = "default"


def get_request_context(
    settings: Annotated[Settings, Depends(get_settings)],
) -> RequestContext:
    return RequestContext(tenant_id=settings.tenant_id)


def get_app_settings() -> Settings:
    return get_settings()


def get_app_store() -> InMemoryStore:
    return get_store()


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
StoreDep = Annotated[InMemoryStore, Depends(get_app_store)]
ContextDep = Annotated[RequestContext, Depends(get_request_context)]
