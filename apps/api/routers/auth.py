"""Demo auth — issue HS256 JWTs for Contabo/Vercel without Keycloak yet."""

from __future__ import annotations

import hmac
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from jose import JWTError
from pydantic import BaseModel, Field

from apps.api.middleware.auth import create_access_token, decode_bearer_token
from apps.api.settings import Settings, get_settings
from packages.security.rbac import normalize_role

router = APIRouter()

# UI role labels → API RBAC roles
_ROLE_ALIASES = {
    "underwriter": "underwriter",
    "risk analyst": "actuary",
    "risk_analyst": "actuary",
    "actuary": "actuary",
    "portfolio manager": "underwriter",
    "portfolio_manager": "underwriter",
    "approver": "admin",
    "admin": "admin",
    "data_scientist": "data_scientist",
    "data scientist": "data_scientist",
}


class TokenRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)
    role: str = "underwriter"
    tenant_id: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    idle_timeout_minutes: int
    role: str
    actor: str
    tenant_id: str


def _credentials_configured(settings: Settings) -> bool:
    return bool(settings.login_email.strip() and settings.login_password)


def _secure_eq(left: str, right: str) -> bool:
    """Length-safe compare (hmac.compare_digest raises on length mismatch)."""
    a = left.encode("utf-8")
    b = right.encode("utf-8")
    if len(a) != len(b):
        return False
    return hmac.compare_digest(a, b)


def _credentials_match(settings: Settings, email: str, password: str) -> bool:
    expected_email = settings.login_email.strip().lower()
    expected_password = settings.login_password
    if not expected_email or not expected_password:
        return False
    email_ok = _secure_eq(email.strip().lower(), expected_email)
    password_ok = _secure_eq(password, expected_password)
    return email_ok and password_ok


def _map_role(raw: str) -> str:
    key = raw.strip().lower()
    return normalize_role(_ROLE_ALIASES.get(key, key))


def _issue(
    *,
    email: str,
    role: str,
    tenant_id: str,
    settings: Settings,
) -> TokenResponse:
    actor = email.split("@", 1)[0] or email
    exp = settings.session_idle_minutes or settings.jwt_exp_minutes
    token = create_access_token(
        actor=actor,
        role=role,
        tenant_id=tenant_id,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        exp_minutes=exp,
        extra={"email": email},
    )
    return TokenResponse(
        access_token=token,
        expires_in_minutes=exp,
        idle_timeout_minutes=settings.session_idle_minutes,
        role=role,
        actor=actor,
        tenant_id=tenant_id,
    )


@router.post("/auth/token", response_model=TokenResponse)
def issue_token(body: TokenRequest) -> TokenResponse:
    """
    Login for the Next.js UI.

    Email and password must match LOGIN_EMAIL / LOGIN_PASSWORD from .env.
    Any allowed role may be chosen when credentials match.
    """
    settings = get_settings()
    if not _credentials_configured(settings):
        raise HTTPException(
            status_code=503,
            detail="Login is not configured. Set LOGIN_EMAIL and LOGIN_PASSWORD in .env.",
        )

    email = body.email.strip().lower()
    if "@" not in email:
        raise HTTPException(status_code=400, detail="email must look like an address")
    if not body.password:
        raise HTTPException(status_code=400, detail="password required")

    if not _credentials_match(settings, email, body.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    role = _map_role(body.role)
    tenant = (body.tenant_id or settings.tenant_id).strip() or "default"
    return _issue(email=email, role=role, tenant_id=tenant, settings=settings)


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh_token(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[Optional[str], Header()] = None,
) -> TokenResponse:
    """Extend a valid session (sliding window while the user stays active)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        principal = decode_bearer_token(
            token, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="invalid or expired token") from exc

    email = str(principal.raw_claims.get("email") or "").strip().lower()
    if not email or "@" not in email:
        # Fall back to actor@tenant style if email claim missing
        email = f"{principal.actor}@session.local"
    return _issue(
        email=email,
        role=principal.role,
        tenant_id=principal.tenant_id,
        settings=settings,
    )
