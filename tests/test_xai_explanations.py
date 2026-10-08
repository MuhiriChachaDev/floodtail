"""XAI SHAP / counterfactual / model-card API tests (Phase E)."""

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
from packages.xai.model_card import build_model_card

client = TestClient(app)
SCI = {"X-Floodtail-Role": "data_scientist"}
ACT = {"X-Floodtail-Role": "actuary"}


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
        seed=7,
    )
    run_training_job(
        "vulnerability",
        profile,
        reg,
        tune=False,
        n_iter=2,
        seed=7,
    )
    return reg


def test_model_card_from_registry(trained_models: ModelRegistry) -> None:
    card = build_model_card(trained_models, "hazard")
    assert card["version"]
    assert card["sha256"]
    assert "metrics" in card
    assert card["limitations"]


def test_explanations_for_sample_property(
    trained_models: ModelRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "models_dir", trained_models.root)

    port = client.post("/v1/portfolios", data={"source": "builtin_nairobi"})
    pid = port.json()["portfolio"]["id"]
    haz = trained_models.get_pinned("hazard")
    vuln = trained_models.get_pinned("vulnerability")
    run = client.post(
        "/v1/runs",
        json={
            "portfolio_id": pid,
            "use_ml": True,
            "hazard_model_version": haz,
            "vuln_model_version": vuln,
            "force_ollama_down": True,
        },
    )
    assert run.status_code == 200, run.text
    rid = run.json()["run"]["id"]
    props = client.get(f"/v1/runs/{rid}/properties", params={"limit": 1})
    assert props.status_code == 200
    loc_id = props.json()["properties"][0]["loc_id"]

    g = client.get(
        f"/v1/runs/{rid}/explanations/global",
        params={"model_type": "hazard", "sample_size": 30},
        headers=ACT,
    )
    assert g.status_code == 200, g.text
    assert g.json()["explanation"]["drivers"]

    loc = client.get(
        f"/v1/runs/{rid}/explanations/local/{loc_id}",
        params={"model_type": "vulnerability", "tier": "extreme"},
        headers=ACT,
    )
    assert loc.status_code == 200, loc.text
    assert loc.json()["explanation"]["top_features"]
    assert loc.json()["explanation"]["loc_id"] == str(loc_id)

    cf = client.get(
        f"/v1/runs/{rid}/explanations/counterfactual/{loc_id}",
        params={"model_type": "vulnerability", "depth_m_scale": 0.5},
        headers=ACT,
    )
    assert cf.status_code == 200, cf.text
    body = cf.json()["counterfactual"]
    assert "delta" in body
    assert "loss_kes" in body["delta"]

    card = client.get("/v1/models/hazard/card", headers=SCI)
    assert card.status_code == 200
    assert card.json()["card"]["model_type"] == "hazard"
