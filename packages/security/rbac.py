"""Role-based access control (kenyaRE role matrix)."""

from __future__ import annotations

from enum import Enum
from typing import Iterable, Optional, Sequence


class Role(str, Enum):
    ADMIN = "admin"
    DATA_SCIENTIST = "data_scientist"
    ACTUARY = "actuary"
    UNDERWRITER = "underwriter"
    CLIENT_VIEWER = "client_viewer"
    REGULATOR = "regulator"
    AUDITOR = "auditor"


# Permission → roles allowed
PERMISSIONS: dict[str, frozenset[str]] = {
    "portfolio:write": frozenset(
        {Role.ADMIN.value, Role.UNDERWRITER.value, Role.ACTUARY.value, Role.DATA_SCIENTIST.value}
    ),
    "portfolio:read": frozenset(
        {
            Role.ADMIN.value,
            Role.UNDERWRITER.value,
            Role.ACTUARY.value,
            Role.DATA_SCIENTIST.value,
            Role.CLIENT_VIEWER.value,
            Role.REGULATOR.value,
            Role.AUDITOR.value,
        }
    ),
    "run:write": frozenset(
        {Role.ADMIN.value, Role.UNDERWRITER.value, Role.ACTUARY.value, Role.DATA_SCIENTIST.value}
    ),
    "run:read": frozenset(
        {
            Role.ADMIN.value,
            Role.UNDERWRITER.value,
            Role.ACTUARY.value,
            Role.DATA_SCIENTIST.value,
            Role.CLIENT_VIEWER.value,
            Role.REGULATOR.value,
            Role.AUDITOR.value,
        }
    ),
    "model:train": frozenset({Role.ADMIN.value, Role.DATA_SCIENTIST.value}),
    "model:read": frozenset(
        {
            Role.ADMIN.value,
            Role.DATA_SCIENTIST.value,
            Role.ACTUARY.value,
            Role.UNDERWRITER.value,
            Role.REGULATOR.value,
        }
    ),
    "approve": frozenset({Role.ADMIN.value, Role.UNDERWRITER.value, Role.ACTUARY.value}),
    "explain": frozenset(
        {
            Role.ADMIN.value,
            Role.ACTUARY.value,
            Role.DATA_SCIENTIST.value,
            Role.UNDERWRITER.value,
            Role.REGULATOR.value,
        }
    ),
    "audit:read": frozenset(
        {Role.ADMIN.value, Role.AUDITOR.value, Role.REGULATOR.value, Role.ACTUARY.value}
    ),
    "narrative": frozenset(
        {
            Role.ADMIN.value,
            Role.UNDERWRITER.value,
            Role.ACTUARY.value,
            Role.CLIENT_VIEWER.value,
            Role.DATA_SCIENTIST.value,
        }
    ),
    "query": frozenset(
        {
            Role.ADMIN.value,
            Role.UNDERWRITER.value,
            Role.ACTUARY.value,
            Role.DATA_SCIENTIST.value,
        }
    ),
    "knowledge:write": frozenset(
        {
            Role.ADMIN.value,
            Role.UNDERWRITER.value,
            Role.ACTUARY.value,
            Role.DATA_SCIENTIST.value,
        }
    ),
    "knowledge:read": frozenset(
        {
            Role.ADMIN.value,
            Role.UNDERWRITER.value,
            Role.ACTUARY.value,
            Role.DATA_SCIENTIST.value,
            Role.CLIENT_VIEWER.value,
            Role.REGULATOR.value,
            Role.AUDITOR.value,
        }
    ),
    "memory:write": frozenset(
        {
            Role.ADMIN.value,
            Role.UNDERWRITER.value,
            Role.ACTUARY.value,
            Role.DATA_SCIENTIST.value,
        }
    ),
    "memory:read": frozenset(
        {
            Role.ADMIN.value,
            Role.UNDERWRITER.value,
            Role.ACTUARY.value,
            Role.DATA_SCIENTIST.value,
            Role.AUDITOR.value,
        }
    ),
}


class ForbiddenError(PermissionError):
    """Raised when RBAC denies an action."""

    def __init__(self, role: str, permission: str) -> None:
        self.role = role
        self.permission = permission
        super().__init__(f"role {role!r} denied permission {permission!r}")


def normalize_role(role: Optional[str]) -> str:
    r = (role or Role.UNDERWRITER.value).strip().lower()
    try:
        return Role(r).value
    except ValueError:
        return Role.UNDERWRITER.value


def has_permission(role: str, permission: str) -> bool:
    allowed = PERMISSIONS.get(permission)
    if allowed is None:
        return False
    return normalize_role(role) in allowed


def require_permission(role: str, permission: str) -> None:
    if not has_permission(role, permission):
        raise ForbiddenError(normalize_role(role), permission)


def require_any(role: str, permissions: Sequence[str]) -> None:
    if not any(has_permission(role, p) for p in permissions):
        raise ForbiddenError(normalize_role(role), "|".join(permissions))


def roles_for(permission: str) -> Iterable[str]:
    return sorted(PERMISSIONS.get(permission, frozenset()))
