"""Shared FastAPI dependencies — auth, tenant, RBAC hooks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Request

from apps.api.middleware.auth import resolve_principal
from apps.api.settings import Settings, get_settings
from apps.api.store import InMemoryStore, get_store
from packages.security.rbac import ForbiddenError, require_permission
from packages.security.tenant import TenantMismatchError, assert_same_tenant


@dataclass(frozen=True)
class RequestContext:
    actor: str = "anonymous"
    role: str = "underwriter"
    tenant_id: str = "default"
    authenticated: bool = False


def get_request_context(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[Optional[str], Header(default=None)] = None,
    x_floodtail_role: Annotated[Optional[str], Header(default=None)] = None,
    x_floodtail_actor: Annotated[Optional[str], Header(default=None)] = None,
    x_floodtail_tenant: Annotated[Optional[str], Header(default=None)] = None,
) -> RequestContext:
    """
    Resolve caller from JWT or prototype stub headers.

    Prototype headers (env=prototype only):
      X-Floodtail-Role, X-Floodtail-Actor, X-Floodtail-Tenant
    """
    try:
        principal = resolve_principal(
            authorization=authorization,
            env=settings.env,
            jwt_secret=settings.jwt_secret,
            jwt_algorithm=settings.jwt_algorithm,
            default_tenant=settings.tenant_id,
            header_role=x_floodtail_role,
            header_actor=x_floodtail_actor,
            header_tenant=x_floodtail_tenant,
        )
    except PermissionError as exc:
        # Prototype never 401s on missing token; non-prototype does
        if settings.env == "prototype":
            return RequestContext(tenant_id=settings.tenant_id)
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return RequestContext(
        actor=principal.actor,
        role=principal.role,
        tenant_id=principal.tenant_id,
        authenticated=bool(authorization),
    )


def get_app_settings() -> Settings:
    return get_settings()


def get_app_store() -> InMemoryStore:
    return get_store()


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
StoreDep = Annotated[InMemoryStore, Depends(get_app_store)]
ContextDep = Annotated[RequestContext, Depends(get_request_context)]


def enforce_permission(ctx: RequestContext, permission: str) -> None:
    try:
        require_permission(ctx.role, permission)
    except ForbiddenError as exc:
        raise HTTPException(
            status_code=403,
            detail={"message": str(exc), "role": exc.role, "permission": exc.permission},
        ) from exc


def enforce_tenant(resource, ctx: RequestContext) -> None:
    try:
        assert_same_tenant(
            resource,
            ctx.tenant_id,
            allow_admin_bypass=True,
            caller_role=ctx.role,
        )
    except TenantMismatchError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
