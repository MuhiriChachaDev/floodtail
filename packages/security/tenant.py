"""Tenant isolation checks for portfolio / run resources."""

from __future__ import annotations

from typing import Optional, Protocol


class TenantMismatchError(PermissionError):
    def __init__(self, resource_tenant: str, caller_tenant: str) -> None:
        self.resource_tenant = resource_tenant
        self.caller_tenant = caller_tenant
        super().__init__(
            f"tenant mismatch: resource={resource_tenant!r} caller={caller_tenant!r}"
        )


class HasTenant(Protocol):
    tenant_id: str


def assert_same_tenant(
    resource: Optional[HasTenant],
    caller_tenant: str,
    *,
    allow_admin_bypass: bool = False,
    caller_role: str = "",
) -> None:
    """
    Raise TenantMismatchError if resource tenant ≠ caller tenant.
    Admin may bypass when allow_admin_bypass=True.
    """
    if resource is None:
        return
    if allow_admin_bypass and caller_role == "admin":
        return
    res_tenant = getattr(resource, "tenant_id", None) or "default"
    caller = caller_tenant or "default"
    if res_tenant != caller:
        raise TenantMismatchError(res_tenant, caller)


def tenant_filter_ok(resource_tenant: str, caller_tenant: str) -> bool:
    return (resource_tenant or "default") == (caller_tenant or "default")
