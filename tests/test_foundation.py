"""FLOODTAIL — Phase 1 foundation tests.

Tests cover:
    - PortfolioRecord validation (valid, invalid coords, negative TIV, missing fields)
    - HazardResult validation (invalid depth)
    - VulnerabilityResult validation (invalid damage ratio)
    - LossResult validation (negative loss)
    - Configuration loading (success and failure)
    - RunContext generation
    - AgentResult status validation
    - Application bootstrap smoke test
    - Reproducibility verification
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.config import FLOODTAILConfig, load_config
from src.exceptions import ConfigurationError
from src.schemas import (
    AgentResult,
    AnnualLossResult,
    EventRecord,
    HazardResult,
    LossResult,
    PolicyTailResult,
    PortfolioRecord,
    PricingResult,
    RunContext,
    VulnerabilityResult,
)


# =========================================================================
# Helpers
# =========================================================================

def _valid_portfolio_kwargs() -> dict:
    """Return a minimal valid PortfolioRecord dict."""
    return {
        "policy_id": "POL-001",
        "latitude": -1.2921,
        "longitude": 36.8219,
        "insured_value": 5_000_000.0,
        "property_type": "commercial",
    }


# =========================================================================
# TEST 1 — Valid PortfolioRecord is accepted
# =========================================================================

def test_valid_portfolio_record() -> None:
    rec = PortfolioRecord(**_valid_portfolio_kwargs())
    assert rec.policy_id == "POL-001"
    assert rec.latitude == pytest.approx(-1.2921)
    assert rec.insured_value == 5_000_000.0
    assert rec.construction_class is None  # optional, absent
    assert rec.region is None


# =========================================================================
# TEST 2 — Latitude > 90 rejected
# =========================================================================

def test_latitude_above_90_rejected() -> None:
    kw = _valid_portfolio_kwargs()
    kw["latitude"] = 91.0
    with pytest.raises(ValidationError):
        PortfolioRecord(**kw)


# =========================================================================
# TEST 3 — Latitude < -90 rejected
# =========================================================================

def test_latitude_below_minus_90_rejected() -> None:
    kw = _valid_portfolio_kwargs()
    kw["latitude"] = -91.0
    with pytest.raises(ValidationError):
        PortfolioRecord(**kw)


# =========================================================================
# TEST 4 — Longitude > 180 rejected
# =========================================================================

def test_longitude_above_180_rejected() -> None:
    kw = _valid_portfolio_kwargs()
    kw["longitude"] = 181.0
    with pytest.raises(ValidationError):
        PortfolioRecord(**kw)


# =========================================================================
# TEST 5 — Longitude < -180 rejected
# =========================================================================

def test_longitude_below_minus_180_rejected() -> None:
    kw = _valid_portfolio_kwargs()
    kw["longitude"] = -181.0
    with pytest.raises(ValidationError):
        PortfolioRecord(**kw)


# =========================================================================
# TEST 6 — Negative insured_value rejected
# =========================================================================

def test_negative_insured_value_rejected() -> None:
    kw = _valid_portfolio_kwargs()
    kw["insured_value"] = -100.0
    with pytest.raises(ValidationError):
        PortfolioRecord(**kw)


# =========================================================================
# TEST 7 — Missing policy_id rejected
# =========================================================================

def test_missing_policy_id_rejected() -> None:
    kw = _valid_portfolio_kwargs()
    del kw["policy_id"]
    with pytest.raises(ValidationError):
        PortfolioRecord(**kw)


# =========================================================================
# TEST 8 — Missing property_type rejected
# =========================================================================

def test_missing_property_type_rejected() -> None:
    kw = _valid_portfolio_kwargs()
    del kw["property_type"]
    with pytest.raises(ValidationError):
        PortfolioRecord(**kw)


# =========================================================================
# TEST 9 — Invalid hazard depth rejected
# =========================================================================

def test_invalid_hazard_depth_rejected() -> None:
    with pytest.raises(ValidationError):
        HazardResult(event_id="E-001", policy_id="POL-001", depth_m=-0.5)


# =========================================================================
# TEST 10 — Invalid damage ratio rejected
# =========================================================================

def test_invalid_damage_ratio_rejected() -> None:
    with pytest.raises(ValidationError):
        VulnerabilityResult(event_id="E-001", policy_id="POL-001", damage_ratio=1.5)


# =========================================================================
# TEST 11 — Negative loss rejected
# =========================================================================

def test_negative_loss_rejected() -> None:
    with pytest.raises(ValidationError):
        LossResult(
            event_id="E-001",
            policy_id="POL-001",
            insured_value=1_000_000.0,
            loss=-500.0,
        )


# =========================================================================
# TEST 12 — Configuration loads successfully
# =========================================================================

def test_configuration_loads_successfully() -> None:
    cfg = load_config()
    assert cfg.project.name == "FLOODTAIL"
    assert cfg.simulation.years == 10_000
    assert cfg.simulation.seed == 482913
    assert cfg.risk.tail_confidence == pytest.approx(0.996)
    assert isinstance(cfg.data.portfolio_required_fields, list)


# =========================================================================
# TEST 13 — Invalid configuration fails with ConfigurationError
# =========================================================================

def test_invalid_configuration_raises_error(tmp_path: Path) -> None:
    bad_yaml = tmp_path / "bad_config.yaml"
    bad_yaml.write_text("project:\n  name: 'X'\n", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_config(path=bad_yaml)


# =========================================================================
# TEST 14 — RunContext is generated correctly
# =========================================================================

def test_run_context_generated_correctly() -> None:
    ctx = RunContext(
        model_version="0.1.0",
        random_seed=42,
        simulation_years=1000,
    )
    # run_id is a valid UUID
    uuid.UUID(ctx.run_id)  # raises ValueError if invalid
    assert ctx.model_version == "0.1.0"
    assert ctx.random_seed == 42
    assert ctx.simulation_years == 1000
    assert ctx.created_at.tzinfo is not None  # timezone-aware


# =========================================================================
# TEST 15 — AgentResult accepts valid statuses
# =========================================================================

@pytest.mark.parametrize(
    "status",
    ["PENDING", "RUNNING", "SUCCESS", "WARNING", "FAILED", "REVIEW_REQUIRED"],
)
def test_agent_result_valid_statuses(status: str) -> None:
    result = AgentResult(agent_name="test_agent", status=status)
    assert result.status == status


# =========================================================================
# TEST 16 — AgentResult rejects invalid status
# =========================================================================

def test_agent_result_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        AgentResult(agent_name="test_agent", status="INVALID_STATUS")


# =========================================================================
# TEST 17 — Application bootstrap runs successfully
# =========================================================================

def test_app_bootstrap_runs() -> None:
    """Import and call main() — it should complete without error."""
    from app import main

    main()  # should not raise


# =========================================================================
# TEST 18 — Reproducibility: config preserves critical parameters
# =========================================================================

def test_reproducibility_config_preservation() -> None:
    """Load config twice and confirm seed, years, and version are stable."""
    cfg1 = load_config()
    cfg2 = load_config()

    assert cfg1.simulation.seed == cfg2.simulation.seed
    assert cfg1.simulation.years == cfg2.simulation.years
    assert cfg1.model.model_version == cfg2.model.model_version
    assert cfg1.project.environment == cfg2.project.environment


# =========================================================================
# Additional contract tests (bonus coverage)
# =========================================================================

def test_event_record_valid() -> None:
    event = EventRecord(event_id="E-001", annual_frequency=0.05)
    assert event.event_id == "E-001"
    assert event.severity is None


def test_event_record_negative_severity_rejected() -> None:
    with pytest.raises(ValidationError):
        EventRecord(event_id="E-001", annual_frequency=0.05, severity=-1.0)


def test_annual_loss_result_valid() -> None:
    alr = AnnualLossResult(
        simulation_year=1,
        annual_loss=500_000.0,
        max_event_loss=400_000.0,
        event_ids=["E-001", "E-002"],
    )
    assert alr.simulation_year == 1


def test_policy_tail_result_valid() -> None:
    ptr = PolicyTailResult(policy_id="POL-001", aal=25000.0, tail_contribution=3000.0)
    assert ptr.aal == 25000.0


def test_pricing_result_valid() -> None:
    pr = PricingResult(
        policy_id="POL-001",
        expected_loss=20000.0,
        tail_charge=5000.0,
        expense=3000.0,
        technical_premium=28000.0,
    )
    assert pr.technical_premium == 28000.0


def test_blank_policy_id_rejected() -> None:
    kw = _valid_portfolio_kwargs()
    kw["policy_id"] = ""
    with pytest.raises(ValidationError):
        PortfolioRecord(**kw)


def test_zero_insured_value_rejected() -> None:
    kw = _valid_portfolio_kwargs()
    kw["insured_value"] = 0.0
    with pytest.raises(ValidationError):
        PortfolioRecord(**kw)
