"""Phase F — E2E hardening: upload → train → run → metrics → insight → approve → audit."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.settings import get_settings
from apps.api.store import reset_store
from packages.security.audit_log import reset_audit_chain

client = TestClient(app)

UW = {"X-Floodtail-Role": "underwriter", "X-Floodtail-Actor": "uw-demo"}
SCI = {"X-Floodtail-Role": "data_scientist", "X-Floodtail-Actor": "ds-demo"}
AUD = {"X-Floodtail-Role": "auditor", "X-Floodtail-Actor": "aud-demo"}


@pytest.fixture(autouse=True)
def _clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    reset_store()
    reset_audit_chain()
    get_settings.cache_clear()
    models_dir = tmp_path / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    s = get_settings()
    monkeypatch.setattr(s, "models_dir", models_dir)
    yield
    reset_store()
    reset_audit_chain()
    get_settings.cache_clear()


def test_health_reports_data_ollama_registry() -> None:
    r = client.get("/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["phase"] == "F-e2e-hardening"
    assert "nairobi_data" in body
    assert "nairobi_data_ok" in body
    assert "ollama_up" in body
    assert "registry" in body
    reg = body["registry"]
    assert "registry_ready" in reg
    assert "hazard_pinned" in reg
    assert "vulnerability_pinned" in reg
    assert "n_artifacts" in reg
    # Fresh tmp models dir → not ready until train
    assert reg["registry_ready"] is False
    assert body["status"] == "degraded"


def test_e2e_upload_train_run_insight_approve_audit(
    tmp_path: Path,
) -> None:
    settings = get_settings()
    exposure = settings.nairobi_data_dir / "exposure_nairobi_with_hazard.csv"
    assert exposure.exists()

    # 1) Upload portfolio CSV
    with exposure.open("rb") as fh:
        up = client.post(
            "/v1/portfolios",
            data={
                "source": "upload",
                "location_label": "Nairobi County",
                "name": "phase-f-upload",
            },
            files={"file": ("exposure_nairobi_with_hazard.csv", fh, "text/csv")},
            headers=UW,
        )
    assert up.status_code == 200, up.text
    portfolio = up.json()["portfolio"]
    assert portfolio["n_rows"] == 600
    assert portfolio["synthetic"] is True
    pid = portfolio["id"]

    # 2) Train hazard + vulnerability (data scientist)
    haz = client.post(
        "/v1/models/hazard/train",
        json={"tune": False, "n_iter": 2, "seed": 11},
        headers=SCI,
    )
    assert haz.status_code == 200, haz.text
    assert haz.json()["pinned"] is True
    haz_ver = haz.json()["version"]

    vuln = client.post(
        "/v1/models/vulnerability/train",
        json={"tune": False, "n_iter": 2, "seed": 11},
        headers=SCI,
    )
    assert vuln.status_code == 200, vuln.text
    assert vuln.json()["pinned"] is True
    vuln_ver = vuln.json()["version"]

    health = client.get("/v1/health").json()
    assert health["registry"]["registry_ready"] is True
    assert health["registry"]["hazard_pinned"] == haz_ver
    assert health["registry"]["vulnerability_pinned"] == vuln_ver

    # 3) Run with ML (force Ollama down → template insight path)
    run = client.post(
        "/v1/runs",
        json={
            "portfolio_id": pid,
            "use_ml": True,
            "hazard_model_version": haz_ver,
            "vuln_model_version": vuln_ver,
            "force_ollama_down": True,
        },
        headers=UW,
    )
    assert run.status_code == 200, run.text
    run_body = run.json()
    assert run_body["run"]["status"] == "COMPLETED"
    rid = run_body["run"]["id"]

    # 4) Metrics
    m = client.get(f"/v1/runs/{rid}/metrics", headers=UW)
    assert m.status_code == 200
    metrics = m.json()["metrics"]
    assert metrics["n_insured_houses"] == 600
    assert len(metrics["ep_curve"]) == 5
    assert metrics["hazard_model_version"] == haz_ver
    assert metrics["vuln_model_version"] == vuln_ver
    assert metrics["capital_band"]["floor_kes"] <= metrics["capital_band"]["ceiling_kes"]
    assert metrics["data_labels"]["synthetic_exposure"] is True

    # 5) Insight (actionable set-aside)
    i = client.get(f"/v1/runs/{rid}/insight", headers=UW)
    assert i.status_code == 200
    insight = i.json()["insight"]
    assert insight["insured_houses"] == 600
    assert "set_aside" in insight
    assert insight["recommendation"] in ("ACCEPT", "REVIEW", "ESCALATE")
    assert insight["numbers_source"] in ("template", "ollama", "fallback")

    # 6) Approve (human gate 2)
    ap = client.post(
        f"/v1/runs/{rid}/approve",
        json={
            "decision": insight["recommendation"],
            "reason": "Phase F E2E: capital band and EP reviewed; demo accept path.",
            "gate": "gate2",
        },
        headers=UW,
    )
    assert ap.status_code == 200, ap.text
    assert ap.json()["chain_valid"] is True
    assert ap.json()["decision"]["decision"] == insight["recommendation"]

    # 7) Audit verify
    audit = client.get("/v1/audit", headers=AUD)
    assert audit.status_code == 200
    body = audit.json()
    assert body["chain_valid"] is True
    assert body["total"] >= 1
    types = {e["event_type"] for e in body["events"]}
    assert "portfolio_ingest" in types
    assert "model_train" in types
    assert "run_completed" in types
    assert "decision" in types
