"""Phase C — flexible ML pipeline tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.settings import get_settings
from apps.api.store import reset_store
from packages.cat_core.engine import run_cat
from packages.ml.data.labels import build_hazard_labels
from packages.ml.data.loaders import load_training_exposure, train_val_test_split
from packages.ml.features.builder import FeatureBuilder
from packages.ml.geo import haversine_km, nearest_distance_km
from packages.ml.pipeline import run_training_job
from packages.ml.registry import ModelRegistry

client = TestClient(app)


@pytest.fixture
def tmp_registry(tmp_path: Path) -> ModelRegistry:
    return ModelRegistry(tmp_path / "models")


@pytest.fixture
def profile():
    return get_settings().assumptions_profile()


@pytest.fixture(autouse=True)
def _clean_api() -> None:
    reset_store()
    get_settings.cache_clear()
    yield
    reset_store()
    get_settings.cache_clear()


def test_haversine_and_nearest() -> None:
    # ~111 km per degree lat
    d = float(haversine_km(-1.0, 36.0, -1.0, 37.0))
    assert 100 < d < 120
    dist = nearest_distance_km([-1.28], [36.86], [-1.28, -1.30], [36.86, 36.90])
    assert dist[0] == pytest.approx(0.0, abs=1e-6)


def test_split_no_id_leakage(profile, tmp_registry) -> None:
    settings = get_settings()
    frame, _ = load_training_exposure(
        settings.nairobi_data_dir / "exposure_nairobi_with_hazard.csv",
        profile,
        hotspots_path=settings.nairobi_data_dir / "nairobi_hotspots_geocoded.csv",
        use_osm=False,
    )
    train, val, test, meta = train_val_test_split(frame, seed=0)
    assert meta["n_train"] + meta["n_val"] + meta["n_test"] == 600
    ids = lambda df: set(df["loc_id"].astype(str))
    assert ids(train).isdisjoint(ids(val))
    assert ids(train).isdisjoint(ids(test))
    assert ids(val).isdisjoint(ids(test))


def test_feature_builder_train_infer_parity(profile) -> None:
    settings = get_settings()
    frame, _ = load_training_exposure(
        settings.nairobi_data_dir / "exposure_nairobi_with_hazard.csv",
        profile,
        hotspots_path=settings.nairobi_data_dir / "nairobi_hotspots_geocoded.csv",
    )
    frame, label_meta = build_hazard_labels(frame, profile)
    builder = FeatureBuilder("hazard", profile.housing_classes, target_columns=label_meta["target_columns"])
    x1 = builder.fit_transform(frame.head(20))
    state = builder.to_state()
    b2 = FeatureBuilder.from_state(state)
    x2 = b2.transform(frame.head(20))
    assert x1.shape == x2.shape
    np.testing.assert_allclose(x1, x2)

    # unknown housing class → zeros for one-hots, still runs
    weird = frame.head(3).copy()
    weird["housing_class"] = "martian_hut"
    xw = builder.transform(weird)
    assert xw.shape[1] == x1.shape[1]
    assert np.isfinite(xw).all()


def test_train_hazard_and_vuln_and_infer_delta(profile, tmp_registry: ModelRegistry) -> None:
    settings = get_settings()
    exposure = settings.nairobi_data_dir / "exposure_nairobi_with_hazard.csv"
    hotspots = settings.nairobi_data_dir / "nairobi_hotspots_geocoded.csv"

    haz = run_training_job(
        "hazard",
        profile,
        tmp_registry,
        exposure_path=exposure,
        hotspots_path=hotspots,
        use_osm=False,
        tune=True,
        n_iter=3,
        seed=7,
    )
    assert haz.metrics["passed_gate"] is True
    assert tmp_registry.verify_integrity("hazard", haz.version)

    vuln = run_training_job(
        "vulnerability",
        profile,
        tmp_registry,
        tune=True,
        n_iter=3,
        seed=7,
    )
    assert vuln.metrics["passed_gate"] is True

    raw = pd.read_csv(exposure)
    from packages.cat_core.exposure import validate_and_normalize

    frame, stats, _ = validate_and_normalize(
        raw, profile, location_label="Nairobi County", source="test"
    )
    hs = pd.read_csv(hotspots)

    prior = run_cat(
        frame,
        profile,
        run_id="prior",
        portfolio_id="p",
        location_label=stats.location_label,
        hotspots=hs,
        use_ml=False,
    )
    ml = run_cat(
        frame,
        profile,
        run_id="ml",
        portfolio_id="p",
        location_label=stats.location_label,
        hotspots=hs,
        registry=tmp_registry,
        hazard_model_version=haz.version,
        vuln_model_version=vuln.version,
        use_ml=True,
    )
    assert ml.metrics.hazard_model_version == haz.version
    assert ml.metrics.vuln_model_version == vuln.version
    assert ml.metrics.baseline_delta
    # ML path should produce finite AAL; delta dict present
    assert np.isfinite(ml.metrics.aal_kes)
    assert np.isfinite(prior.metrics.aal_kes)
    # Corrupt SHA should fail load
    sha_path = tmp_registry.model_dir("hazard", haz.version) / "SHA256"
    sha_path.write_text("0" * 64 + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256"):
        tmp_registry.load("hazard", haz.version)


def test_api_train_and_ml_run(tmp_path: Path, monkeypatch) -> None:
    settings = get_settings()
    # Point models dir at temp so we don't pollute repo models/
    models_dir = tmp_path / "models"
    monkeypatch.setenv("MODELS_DIR", str(models_dir))
    # Settings caches Path at class default — override via cache clear + env may not map
    # Directly patch settings instance
    get_settings.cache_clear()
    s = get_settings()
    object.__setattr__(s, "models_dir", models_dir) if False else None
    # pydantic settings may be frozen-ish; monkeypatch attribute
    monkeypatch.setattr(s, "models_dir", models_dir)

    port = client.post("/v1/portfolios", data={"source": "builtin_nairobi"})
    assert port.status_code == 200
    pid = port.json()["portfolio"]["id"]

    sci = {"X-Floodtail-Role": "data_scientist"}
    haz = client.post(
        "/v1/models/hazard/train",
        json={"tune": True, "n_iter": 3, "seed": 3},
        headers=sci,
    )
    assert haz.status_code == 200, haz.text
    vuln = client.post(
        "/v1/models/vulnerability/train",
        json={"tune": True, "n_iter": 3, "seed": 3},
        headers=sci,
    )
    assert vuln.status_code == 200, vuln.text

    listed = client.get("/v1/models")
    assert listed.status_code == 200
    assert len(listed.json()["models"]) >= 2

    run = client.post(
        "/v1/runs",
        json={
            "portfolio_id": pid,
            "use_ml": True,
            "hazard_model_version": haz.json()["version"],
            "vuln_model_version": vuln.json()["version"],
            "force_ollama_down": True,
        },
    )
    assert run.status_code == 200, run.text
    metrics = run.json()["metrics"]
    assert metrics["hazard_model_version"] == haz.json()["version"]
    assert metrics["vuln_model_version"] == vuln.json()["version"]
    assert "baseline_delta" in metrics
