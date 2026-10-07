"""API health smoke test."""

from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_root() -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "floodtail-api"
    assert body["status"] == "phase-e"
    assert body["phase"] == "E"


def test_health() -> None:
    r = client.get("/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["streamlit"] == "removed"
    assert body["phase"] == "E-security-xai"
    assert "nairobi_data_ok" in body
    assert "assumptions_version" in body
    assert "ollama_up" in body
