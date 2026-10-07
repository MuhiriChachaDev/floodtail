"""Phase A — settings, types, in-memory store, route stubs."""

from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.settings import Settings, get_settings
from apps.api.store import InMemoryStore, reset_store
from packages.cat_core.assumptions import AssumptionsProfile
from packages.cat_core.types import (
    CapitalBand,
    DataLabels,
    InsightPackage,
    MetricsPayload,
    Portfolio,
    Recommendation,
    RunConfig,
    StageStatus,
    AgentResult,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_store() -> None:
    reset_store()
    get_settings.cache_clear()
    yield
    reset_store()
    get_settings.cache_clear()


def test_settings_load_defaults() -> None:
    s = Settings()
    assert s.d_max_m == 4.0
    assert s.parsed_return_periods() == [5, 20, 50, 100, 250]
    assert s.nairobi_data_dir.name == "Nairobi_Data"
    assert s.models_dir.name == "models"
    assert s.ollama_primary_model


def test_assumptions_profile() -> None:
    s = Settings(
        capital_floor_rp=100,
        capital_ceiling_rp=250,
        capital_ceiling_tiv_fraction=0.5,
    )
    profile = s.assumptions_profile()
    assert isinstance(profile, AssumptionsProfile)
    assert profile.assumptions_version == s.assumptions_version
    assert profile.d_max_m == s.d_max_m
    assert profile.return_periods == [5, 20, 50, 100, 250]
    assert profile.capital.floor_return_period == 100
    assert profile.capital.ceiling_return_period == 250
    assert profile.capital.ceiling_tiv_fraction == 0.5
    assert len(profile.tier_names) == 5
    assert "informal_iron_sheet" in profile.housing_classes


def test_types_metrics_require_labels() -> None:
    labels = DataLabels(d_max_m=4.0)
    metrics = MetricsPayload(
        run_id="r1",
        portfolio_id="p1",
        assumptions_version="nairobi-pluvial-v1",
        data_labels=labels,
        n_insured_houses=600,
        total_tiv_kes=1.0e9,
        location_label="Nairobi",
        capital_band=CapitalBand(
            floor_kes=1e6,
            central_kes=2e6,
            ceiling_kes=5e6,
        ),
    )
    assert metrics.data_labels.synthetic_exposure is True
    assert metrics.capital_band is not None
    assert metrics.capital_band.floor_kes <= metrics.capital_band.ceiling_kes


def test_types_insight_package() -> None:
    insight = InsightPackage(
        run_id="r1",
        recommendation=Recommendation.REVIEW,
        insured_houses=600,
        total_tiv_kes=1.0e9,
        location_label="Nairobi",
        set_aside=CapitalBand(floor_kes=1e6, central_kes=2e6, ceiling_kes=5e6),
        why=["Concentration in informal housing"],
        next_steps=["Request actuary review"],
        assumptions_version="nairobi-pluvial-v1",
        data_labels=DataLabels(),
        numbers_source="template",
    )
    assert insight.recommendation == Recommendation.REVIEW
    assert insight.insured_houses == 600


def test_agent_result_status() -> None:
    r = AgentResult(stage="schema_map", status=StageStatus.OK, message="ok", critical=True)
    assert r.status == StageStatus.OK


def test_store_portfolio_and_run_roundtrip() -> None:
    store = InMemoryStore()
    pid = store.create_portfolio_id()
    portfolio = Portfolio(
        id=pid,
        name="demo",
        location_label="Nairobi",
        source="builtin",
        n_rows=2,
    )
    frame = pd.DataFrame(
        {
            "loc_id": ["A", "B"],
            "lat": [-1.3, -1.2],
            "lon": [36.8, 36.9],
            "tiv_kes": [1e6, 2e6],
        }
    )
    store.save_portfolio(portfolio, frame)

    got = store.get_portfolio(pid)
    assert got is not None
    assert got.location_label == "Nairobi"
    got_frame = store.get_portfolio_frame(pid)
    assert got_frame is not None
    assert len(got_frame) == 2

    config = RunConfig(portfolio_id=pid, use_ml=False)
    run = store.create_run(config)
    assert run.status == "PENDING"
    run.status = "COMPLETED"
    store.save_run(run)
    again = store.get_run(run.id)
    assert again is not None
    assert again.status == "COMPLETED"
    assert store.stats()["portfolios"] == 1
    assert store.stats()["runs"] == 1


def test_root_phase_c() -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "floodtail-api"
    assert body["status"] == "phase-c"
    assert body["phase"] == "C"


def test_health_reports_phase_c() -> None:
    r = client.get("/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["phase"] == "C-ml"
    assert body["streamlit"] == "removed"
    assert "assumptions_version" in body
    assert body["return_periods"] == [5, 20, 50, 100, 250]
    assert "capital_policy" in body
    assert "store" in body


def test_remaining_stubs_still_501() -> None:
    assert client.get("/v1/models").status_code == 200  # Phase C live
    assert client.get("/v1/audit").status_code == 501
    assert client.get("/v1/runs/demo/narrative").status_code == 501
    assert client.get("/v1/runs/demo/explanations/global").status_code == 501
