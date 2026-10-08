"""RBAC + tenant + JWT stub tests (Phase E)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.middleware.auth import create_access_token
from apps.api.settings import get_settings
from apps.api.store import reset_store
from packages.security.audit_log import reset_audit_chain
from packages.security.rbac import has_permission

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean() -> None:
    reset_store()
    reset_audit_chain()
    get_settings.cache_clear()
    yield
    reset_store()
    reset_audit_chain()
    get_settings.cache_clear()


def test_underwriter_cannot_train() -> None:
    assert not has_permission("underwriter", "model:train")
    r = client.post(
        "/v1/models/hazard/train",
        json={"tune": False, "n_iter": 2},
        headers={"X-Floodtail-Role": "underwriter"},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["permission"] == "model:train"


def test_data_scientist_allowed_to_train() -> None:
    assert has_permission("data_scientist", "model:train")
    assert has_permission("admin", "model:train")
    # Permission gate passes (not 403) — use absurd path so train fails at 400, not auth
    r = client.post(
        "/v1/models/hazard/train",
        json={"tune": False, "n_iter": 2, "exposure_path": "/no/such/file.csv"},
        headers={"X-Floodtail-Role": "data_scientist"},
    )
    assert r.status_code == 400
    assert "not found" in r.json()["detail"].lower()


def test_auditor_can_read_audit_underwriter_cannot() -> None:
    assert client.get("/v1/audit").status_code == 403
    r = client.get("/v1/audit", headers={"X-Floodtail-Role": "auditor"})
    assert r.status_code == 200
    assert "chain_valid" in r.json()


def test_tenant_mismatch_forbidden() -> None:
    # Create portfolio as tenant A
    a = client.post(
        "/v1/portfolios",
        data={"source": "builtin_nairobi"},
        headers={"X-Floodtail-Tenant": "tenant-a", "X-Floodtail-Role": "underwriter"},
    )
    assert a.status_code == 200
    pid = a.json()["portfolio"]["id"]

    # Tenant B cannot read
    b = client.get(
        f"/v1/portfolios/{pid}",
        headers={"X-Floodtail-Tenant": "tenant-b", "X-Floodtail-Role": "underwriter"},
    )
    assert b.status_code == 403


def test_jwt_bearer_role() -> None:
    settings = get_settings()
    token = create_access_token(
        actor="jwt-user",
        role="auditor",
        tenant_id="default",
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    r = client.get("/v1/audit", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["chain_valid"] is True
