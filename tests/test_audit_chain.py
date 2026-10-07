"""SHA-256 audit chain tests (Phase E)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.settings import get_settings
from apps.api.store import reset_store
from packages.security.audit_log import AuditChain, get_audit_chain, reset_audit_chain

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


def test_chain_append_and_verify() -> None:
    chain = AuditChain()
    e1 = chain.append("ingest", {"n": 1})
    e2 = chain.append("run", {"n": 2})
    assert e1.seq == 1
    assert e2.prev_hash == e1.event_hash
    assert chain.verify() is True


def test_tamper_breaks_chain() -> None:
    chain = get_audit_chain()
    chain.append("a", {"x": 1})
    chain.append("b", {"x": 2})
    assert chain.verify() is True
    # Tamper payload without rehashing
    chain._events[0].payload["x"] = 999  # noqa: SLF001
    assert chain.verify() is False


def test_api_audit_after_run_and_approve() -> None:
    port = client.post("/v1/portfolios", data={"source": "builtin_nairobi"})
    pid = port.json()["portfolio"]["id"]
    run = client.post(
        "/v1/runs",
        json={"portfolio_id": pid, "force_ollama_down": True},
    )
    assert run.status_code == 200
    rid = run.json()["run"]["id"]
    appr = client.post(
        f"/v1/runs/{rid}/approve",
        json={"decision": "ACCEPT", "reason": "Within appetite for demo"},
    )
    assert appr.status_code == 200
    assert appr.json()["chain_valid"] is True

    audit = client.get("/v1/audit", headers={"X-Floodtail-Role": "auditor"})
    assert audit.status_code == 200
    body = audit.json()
    assert body["chain_valid"] is True
    types = {e["event_type"] for e in body["events"]}
    assert "portfolio_ingest" in types
    assert "run_started" in types or "run_completed" in types
    assert "decision" in types
