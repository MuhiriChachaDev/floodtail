"""JWT auth middleware + request context resolution.

Prototype mode: unsigned/dev headers or default underwriter role.
Production/development: HS256 JWT (Keycloak-compatible claims).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt

from packages.security.rbac import normalize_role


@dataclass(frozen=True)
class AuthPrincipal:
    actor: str
    role: str
    tenant_id: str
    raw_claims: dict[str, Any]


def create_access_token(
    *,
    actor: str,
    role: str,
    tenant_id: str,
    secret: str,
    algorithm: str = "HS256",
    exp_minutes: int = 15,
    extra: Optional[dict[str, Any]] = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": actor,
        "preferred_username": actor,
        "role": normalize_role(role),
        "realm_access": {"roles": [normalize_role(role)]},
        "tenant_id": tenant_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=exp_minutes)).timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, secret, algorithm=algorithm)


def _role_from_claims(claims: dict[str, Any]) -> str:
    if claims.get("role"):
        return normalize_role(str(claims["role"]))
    realm = claims.get("realm_access") or {}
    roles = realm.get("roles") or []
    if isinstance(roles, list) and roles:
        # Prefer known floodtail roles
        known = {
            "admin",
            "data_scientist",
            "actuary",
            "underwriter",
            "client_viewer",
            "regulator",
            "auditor",
        }
        for r in roles:
            if str(r).lower() in known:
                return normalize_role(str(r))
        return normalize_role(str(roles[0]))
    return "underwriter"


def decode_bearer_token(
    token: str,
    *,
    secret: str,
    algorithm: str = "HS256",
) -> AuthPrincipal:
    claims = jwt.decode(token, secret, algorithms=[algorithm])
    actor = str(
        claims.get("preferred_username")
        or claims.get("sub")
        or claims.get("email")
        or "anonymous"
    )
    tenant = str(claims.get("tenant_id") or claims.get("tenant") or "default")
    return AuthPrincipal(
        actor=actor,
        role=_role_from_claims(claims),
        tenant_id=tenant,
        raw_claims=dict(claims),
    )


def resolve_principal(
    *,
    authorization: Optional[str],
    env: str,
    jwt_secret: str,
    jwt_algorithm: str,
    default_tenant: str,
    stub_role: str = "underwriter",
    stub_actor: str = "anonymous",
    header_role: Optional[str] = None,
    header_actor: Optional[str] = None,
    header_tenant: Optional[str] = None,
) -> AuthPrincipal:
    """
    Resolve caller identity.

    - If Bearer token present → decode JWT (all envs).
    - If env == prototype and no token → stub headers or defaults.
    - If env != prototype and no token → anonymous underwriter with empty actor
      (routers that require auth should 401).
    """
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            return decode_bearer_token(
                token, secret=jwt_secret, algorithm=jwt_algorithm
            )
        except JWTError as exc:
            raise PermissionError(f"invalid token: {exc}") from exc

    if env == "prototype":
        return AuthPrincipal(
            actor=header_actor or stub_actor,
            role=normalize_role(header_role or stub_role),
            tenant_id=header_tenant or default_tenant,
            raw_claims={"mode": "prototype"},
        )

    # Non-prototype without token: unauthenticated
    raise PermissionError("missing bearer token")
