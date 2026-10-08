"""Regression tests for system-wide audit gap fixes."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.settings import get_settings
from apps.api.store import FileStore, reset_store
from packages.agents.tools.portfolio_tools import schema_map
from packages.cat_core.assumptions import AssumptionsProfile, MonteCarloPolicy
from packages.cat_core.engine import run_prior_only
from packages.cat_core.ep import AAL_CAVEAT, AAL_METHOD, discrete_aal
from packages.cat_core.exposure import validate_and_normalize
from packages.cat_core.vulnerability_prior import damage_ratio

client = TestClient(app)
UW = {"X-Floodtail-Role": "underwriter", "X-Floodtail-Actor": "uw-gap"}


@pytest.fixture(autouse=True)
def _clean(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_store()
    get_settings.cache_clear()
    s = get_settings()
    monkeypatch.setattr(s, "allow_prior_only", True)
    monkeypatch.setattr(s, "require_ml", False)
    yield
    reset_store()
    get_settings.cache_clear()


def test_schema_map_accepts_currency_and_geo_aliases() -> None:
    raw = pd.DataFrame(
        {
            "policy_id": ["P1"],
            "latitude": [6.45],
            "longitude": [3.39],
            "occupancy": ["semi_permanent"],
            "tiv_usd": [1_000_000.0],
        }
    )
    mapped, mapping, warnings = schema_map(raw)
    assert "tiv_kes" in mapped.columns
    assert mapping["tiv_kes"] == "tiv_usd"
    assert mapping["lat"] == "latitude"
    assert any("currency-agnostic" in w.lower() or "TIV column" in w for w in warnings)


def test_upload_uses_schema_map() -> None:
    csv = (
        "policy_id,latitude,longitude,occupancy,tiv_usd,"
        "hazard_score_common,hazard_score_occasional,hazard_score_moderate,"
        "hazard_score_severe,hazard_score_extreme\n"
        "LAG-1,6.45,3.39,semi_permanent,2500000,0.2,0.3,0.4,0.5,0.6\n"
    )
    r = client.post(
        "/v1/portfolios",
        data={"source": "upload", "location_label": "Lagos", "sample_rasters": "false"},
        files={"file": ("lagos.csv", csv.encode(), "text/csv")},
        headers=UW,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["portfolio"]["n_rows"] == 1
    assert body["column_mapping"]["tiv_kes"] == "tiv_usd"
    assert body["column_mapping"]["lat"] == "latitude"


def test_metrics_carry_aal_caveat(tmp_path: Path) -> None:
    profile = AssumptionsProfile()
    frame = pd.DataFrame(
        {
            "loc_id": ["A"],
            "lat": [-1.28],
            "lon": [36.82],
            "housing_class": ["concrete_rcc"],
            "tiv_kes": [5e6],
            "hazard_score_common": [0.2],
            "hazard_score_occasional": [0.3],
            "hazard_score_moderate": [0.4],
            "hazard_score_severe": [0.5],
            "hazard_score_extreme": [0.6],
            "synthetic": [True],
        }
    )
    clean, _, _ = validate_and_normalize(frame, profile, location_label="t", source="t")
    result = run_prior_only(
        clean, profile, run_id="r1", portfolio_id="p1", location_label="t"
    )
    m = result.metrics
    assert m.aal_method == AAL_METHOD
    assert "stochastic" in m.aal_caveat.lower() or "catalogue" in m.aal_caveat.lower()
    assert m.data_labels.aal_method == AAL_METHOD
    assert AAL_CAVEAT in m.data_labels.notes or m.data_labels.aal_caveat == AAL_CAVEAT
    assert m.aal_kes == pytest.approx(discrete_aal(m.tier_losses))


def test_pluggable_vulnerability_curve() -> None:
    profile = AssumptionsProfile(
        housing_classes=["timber_frame", "concrete_rcc"],
        vulnerability_curves={
            "timber_frame": [
                [0.0, 0.0],
                [0.5, 0.4],
                [1.0, 0.7],
                [2.0, 0.9],
                [4.0, 1.0],
            ]
        },
    )
    curves = profile.resolved_vulnerability_curves()
    assert "timber_frame" in curves
    assert damage_ratio(1.0, "timber_frame", curves=curves) == pytest.approx(0.7)
    # Default concrete still present
    assert damage_ratio(1.0, "concrete_rcc", curves=curves) > 0


def test_light_mc_aal_band() -> None:
    profile = AssumptionsProfile(monte_carlo=MonteCarloPolicy(enabled=True, n_sims=50))
    frame = pd.DataFrame(
        {
            "loc_id": ["A", "B"],
            "lat": [-1.28, -1.29],
            "lon": [36.82, 36.83],
            "housing_class": ["semi_permanent", "concrete_rcc"],
            "tiv_kes": [3e6, 8e6],
            "hazard_score_common": [0.3, 0.1],
            "hazard_score_occasional": [0.4, 0.2],
            "hazard_score_moderate": [0.5, 0.3],
            "hazard_score_severe": [0.6, 0.4],
            "hazard_score_extreme": [0.7, 0.5],
            "synthetic": [True, True],
        }
    )
    clean, _, _ = validate_and_normalize(frame, profile, location_label="t", source="t")
    result = run_prior_only(
        clean, profile, run_id="r2", portfolio_id="p2", location_label="t"
    )
    band = result.metrics.aal_uncertainty
    assert band is not None
    assert band.n_sims == 50
    assert band.aal_p05_kes <= band.aal_p50_kes <= band.aal_p95_kes


def test_file_store_survives_reload(tmp_path: Path) -> None:
    root = tmp_path / "store"
    store = FileStore(root)
    from packages.cat_core.types import Portfolio

    p = Portfolio(id="pid-1", name="demo", n_rows=1, tenant_id="default")
    frame = pd.DataFrame({"loc_id": ["x"], "tiv_kes": [1.0]})
    store.save_portfolio(p, frame)
    # New instance loads from disk
    store2 = FileStore(root)
    got = store2.get_portfolio("pid-1")
    assert got is not None
    assert got.name == "demo"
    fr = store2.get_portfolio_frame("pid-1")
    assert fr is not None
    assert len(fr) == 1


def test_hazard_zero_fill_warning() -> None:
    profile = AssumptionsProfile()
    frame = pd.DataFrame(
        {
            "loc_id": ["A"],
            "lat": [-1.28],
            "lon": [36.82],
            "housing_class": ["concrete_rcc"],
            "tiv_kes": [1e6],
        }
    )
    _, _, warnings = validate_and_normalize(frame, profile, location_label="t", source="t")
    assert any("HAZARD_ZERO_FILL" in w for w in warnings)
