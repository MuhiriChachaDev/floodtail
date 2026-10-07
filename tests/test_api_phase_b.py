"""Phase B — portfolio → run → metrics / insight API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.settings import get_settings
from apps.api.store import reset_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean() -> None:
    reset_store()
    get_settings.cache_clear()
    yield
    reset_store()
    get_settings.cache_clear()


def test_builtin_portfolio_run_insight_e2e() -> None:
    r = client.post(
        "/v1/portfolios",
        data={"source": "builtin_nairobi", "location_label": "Nairobi County"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    portfolio = body["portfolio"]
    assert portfolio["n_rows"] == 600
    assert portfolio["ingest_stats"]["n_insured_houses"] == 600
    assert portfolio["synthetic"] is True
    pid = portfolio["id"]

    run_r = client.post("/v1/runs", json={"portfolio_id": pid, "use_ml": False})
    assert run_r.status_code == 200, run_r.text
    run_body = run_r.json()
    assert run_body["run"]["status"] == "COMPLETED"
    rid = run_body["run"]["id"]

    metrics = run_body["metrics"]
    assert metrics["n_insured_houses"] == 600
    assert len(metrics["ep_curve"]) == 5
    assert metrics["capital_band"]["floor_kes"] <= metrics["capital_band"]["ceiling_kes"]
    assert metrics["data_labels"]["synthetic_exposure"] is True
    assert metrics["assumptions_version"]

    insight = run_body["insight"]
    assert insight["insured_houses"] == 600
    assert "set_aside" in insight
    assert insight["numbers_source"] == "template"

    m2 = client.get(f"/v1/runs/{rid}/metrics")
    assert m2.status_code == 200
    i2 = client.get(f"/v1/runs/{rid}/insight")
    assert i2.status_code == 200
    assert i2.json()["insight"]["insured_houses"] == 600

    props = client.get(f"/v1/runs/{rid}/properties?limit=10")
    assert props.status_code == 200
    assert props.json()["total"] == 600
    assert len(props.json()["properties"]) == 10

    accum = client.get(f"/v1/runs/{rid}/accumulation")
    assert accum.status_code == 200
    assert "by_housing_class" in accum.json()["accumulation"]


def test_ml_without_pinned_models_returns_400() -> None:
    r = client.post("/v1/portfolios", data={"source": "builtin_nairobi"})
    pid = r.json()["portfolio"]["id"]
    bad = client.post("/v1/runs", json={"portfolio_id": pid, "use_ml": True})
    assert bad.status_code == 400
