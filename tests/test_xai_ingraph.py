"""In-graph XAI stage attaches SHAP drivers to metrics/allowlist."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.settings import get_settings
from apps.api.store import reset_store
from packages.cat_core.assumptions import AssumptionsProfile
from packages.ml.pipeline import run_training_job
from packages.ml.registry import ModelRegistry
from packages.security.audit_log import reset_audit_chain

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


@pytest.fixture
def trained_models(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModelRegistry:
    settings = get_settings()
    models_dir = tmp_path / "models"
    monkeypatch.setattr(settings, "models_dir", models_dir)
    profile = AssumptionsProfile()
    reg = ModelRegistry(models_dir)
    run_training_job(
        "hazard",
        profile,
        reg,
        exposure_path=settings.nairobi_data_dir / "exposure_nairobi_with_hazard.csv",
        hotspots_path=settings.nairobi_data_dir / settings.hotspots_filename,
        tune=False,
        n_iter=2,
        seed=11,
    )
    run_training_job(
        "vulnerability",
        profile,
        reg,
        tune=False,
        n_iter=2,
        seed=11,
    )
    return reg


def test_run_includes_ingraph_xai(trained_models: ModelRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "models_dir", trained_models.root)

    port = client.post("/v1/portfolios", data={"source": "builtin_nairobi"})
    pid = port.json()["portfolio"]["id"]
    run = client.post(
        "/v1/runs",
        json={
            "portfolio_id": pid,
            "hazard_model_version": trained_models.get_pinned("hazard"),
            "vuln_model_version": trained_models.get_pinned("vulnerability"),
            "force_ollama_down": True,
        },
    )
    assert run.status_code == 200, run.text
    body = run.json()
    stages = {s["stage"]: s for s in body["run"]["stages"]}
    assert stages["xai"]["status"] == "OK"
    assert stages["xai"]["data"]["hazard_top_features"]
    assert stages["xai"]["data"]["vulnerability_top_features"]

    metrics = body["metrics"]
    assert metrics["xai_summary"]["hazard_global"]["top_features"]
    assert metrics["xai_summary"]["vulnerability_global"]["top_features"]
    assert metrics["xai_summary"]["sample_local"]["loc_id"]

    allow = body.get("allowlist") or body["insight"]["allowlist"]
    assert allow.get("shap_hazard_top_features")
    assert allow.get("shap_vulnerability_top_features")
