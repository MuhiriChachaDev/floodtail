"""Demo auth — issue HS256 JWTs for Contabo/Vercel without Keycloak yet."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from apps.api.middleware.auth import create_access_token
from apps.api.settings import get_settings
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
    role: str
    actor: str
    tenant_id: str


@router.post("/auth/token", response_model=TokenResponse)
def issue_token(body: TokenRequest) -> TokenResponse:
    """
    Demo login for the Next.js UI.

    Accepts any non-empty email/password (prototype gate). Issues an HS256 JWT
    signed with JWT_SECRET — same secret the API uses to validate Bearer tokens.
    Replace with Keycloak when OIDC is wired.
    """
    settings = get_settings()
    email = body.email.strip().lower()
    if "@" not in email:
        raise HTTPException(status_code=400, detail="email must look like an address")
    if not body.password.strip():
        raise HTTPException(status_code=400, detail="password required")

    key = body.role.strip().lower()
    role = normalize_role(_ROLE_ALIASES.get(key, key))
    tenant = (body.tenant_id or settings.tenant_id).strip() or "default"
    actor = email.split("@", 1)[0] or email

    token = create_access_token(
        actor=actor,
        role=role,
        tenant_id=tenant,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        exp_minutes=settings.jwt_exp_minutes,
        extra={"email": email},
    )
    return TokenResponse(
        access_token=token,
        expires_in_minutes=settings.jwt_exp_minutes,
        role=role,
        actor=actor,
        tenant_id=tenant,
    )
