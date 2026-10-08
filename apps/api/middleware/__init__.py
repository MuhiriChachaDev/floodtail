"""API middleware — JWT auth helpers (prototype stub roles + Keycloak-ready)."""

from apps.api.middleware.auth import AuthPrincipal, create_access_token, resolve_principal

__all__ = ["AuthPrincipal", "create_access_token", "resolve_principal"]