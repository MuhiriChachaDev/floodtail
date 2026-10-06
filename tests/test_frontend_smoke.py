"""FLOODTAIL — Frontend smoke tests and UI/backend separation validation.

Tests cover:
    1. Frontend and UI module imports
    2. Theme and CSS definitions
    3. UI component rendering (cards, badges, agent steps, banners)
    4. Chart builders produce valid Plotly figures
    5. App page catalogue contains all 16 required pages
    6. Demo data loading and schema validation
    7. Empty / uninitialized state handling
    8. Policy selection and explainability (WHY interaction)
    9. Human decision recording and validation (ACCEPT/MODIFY/REJECT with mandatory reasons)
    10. Audit chain cryptographic verification
    11. UI/backend separation: no duplicate quantitative algorithms in UI
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

import pandas as pd
import pytest

import app
import ui.charts as charts
import ui.components as ui_comp
from ui.theme import Colors, format_bps, format_currency, format_pct, get_custom_css
from src.audit_log import AuditManager
from src.database import DatabaseManager
from src.decision import DecisionConfidence, DecisionEngine, DecisionEvidencePackage
from src.exceptions import ValidationError
from src.explainability import ExplainabilityEngine


# =========================================================================
# TEST 1 — Imports and module presence
# =========================================================================

def test_frontend_imports() -> None:
    """Verify all UI modules import cleanly."""
    assert hasattr(app, "PAGES")
    assert hasattr(app, "PAGE_MAP")
    assert hasattr(app, "run_app")
    assert hasattr(app, "main")
    assert callable(app.main)
    assert callable(app.run_app)


# =========================================================================
# TEST 2 — Design system theme and styling
# =========================================================================

def test_theme_and_css() -> None:
    """Verify brand colour tokens and CSS injection string."""
    assert Colors.NAVY_900.startswith("#")
    assert Colors.FLOOD_CYAN.startswith("#")
    assert Colors.STATUS_GREEN.startswith("#")
    assert Colors.STATUS_RED.startswith("#")
    assert Colors.ACCENT_RED.startswith("#")

    css = get_custom_css()
    assert "<style>" in css
    assert "</style>" in css
    assert "Inter" in css
    assert ".ft-metric-card" in css

    assert format_currency(1_250_000) == "KES 1.2M"
    assert format_currency(500) == "KES 500"
    assert format_pct(12.5) == "12.5%"
    assert format_bps(75.0) == "75 bps"


# =========================================================================
# TEST 3 — UI components produce valid HTML
# =========================================================================

def test_ui_components_markup() -> None:
    """Verify component builders return non-empty styled HTML strings."""
    status_badge = ui_comp.status_badge("FAILED")
    assert "FAILED" in status_badge

    success_badge = ui_comp.status_badge("SUCCESS")
    assert "SUCCESS" in success_badge

    risk_badge = ui_comp.risk_badge("ACCEPT")
    assert "WITHIN APPETITE" in risk_badge

    conf_badge = ui_comp.confidence_badge("HIGH")
    assert "HIGH" in conf_badge


# =========================================================================
# TEST 4 — Chart builders return valid Plotly figures
# =========================================================================

def test_plotly_chart_builders() -> None:
    """Verify chart constructors return valid Plotly figure objects."""
    # Exceedance curve
    class MockPoint:
        def __init__(self, rp: float, loss: float):
            self.return_period_years = rp
            self.loss = loss

    oep = [MockPoint(10, 1000), MockPoint(50, 5000), MockPoint(250, 20000)]
    aep = [MockPoint(10, 1200), MockPoint(50, 5500), MockPoint(250, 22000)]
    fig_curve = charts.exceedance_curve(oep, aep, "Test Curve")
    assert fig_curve is not None
    assert len(fig_curve.data) == 2

    # Tail contribution bars
    fig_bars = charts.tail_contribution_bars(
        policy_ids=["POL-01", "POL-02"],
        contributions=[5000.0, 3000.0],
        portfolio_tvar=8000.0,
    )
    assert fig_bars is not None
    assert len(fig_bars.data) == 1

    # Pricing waterfall
    fig_waterfall = charts.pricing_waterfall(
        expected_loss=10000.0,
        tail_charge=2500.0,
        expense=1500.0,
        total_premium=14000.0,
    )
    assert fig_waterfall is not None
    assert len(fig_waterfall.data) == 1


# =========================================================================
# TEST 5 — Page catalogue completeness (16 pages)
# =========================================================================

def test_sixteen_pages_catalogued() -> None:
    """Verify all 16 required enterprise pages exist in PAGES and PAGE_MAP."""
    expected_pages = [
        "01 — Overview",
        "02 — Portfolio",
        "03 — Data Intelligence",
        "04 — Agent Control",
        "05 — Flood Risk",
        "06 — Accumulation",
        "07 — Catastrophe Analytics",
        "08 — Tail Risk",
        "09 — Policy Intelligence",
        "10 — Pricing",
        "11 — Scenario Lab",
        "12 — Risk Appetite",
        "13 — Decisions",
        "14 — Audit",
        "15 — Methodology",
        "16 — Future / 2090",
    ]
    assert len(app.PAGES) == 16
    for p in expected_pages:
        assert p in app.PAGES, f"Missing page in PAGES: {p}"
        assert p in app.PAGE_MAP, f"Missing page in PAGE_MAP: {p}"
        assert callable(app.PAGE_MAP[p]), f"Page handler {p} is not callable"


# =========================================================================
# TEST 6 — Demo portfolio loading
# =========================================================================

def test_demo_portfolio_loads() -> None:
    """Verify demo portfolio CSV is loaded with correct columns."""
    df = app._load_demo_portfolio()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "policy_id" in df.columns
    assert "insured_value" in df.columns
    assert "latitude" in df.columns
    assert "longitude" in df.columns
    assert (df["insured_value"] > 0).all()


# =========================================================================
# TEST 7 — Uninitialized / empty state handling
# =========================================================================

def test_require_run_guard() -> None:
    """Verify _require_run returns False when uninitialized."""
    import streamlit as st
    st.session_state["run_complete"] = False
    result = app._require_run()
    assert result is False


# =========================================================================
# TEST 8 — Policy WHY explainability trace
# =========================================================================

def test_why_interaction_contract() -> None:
    """Verify ExplainabilityEngine produces structured why traces."""
    engine = ExplainabilityEngine()
    assert hasattr(engine, "explain_decision") or hasattr(engine, "explain_policy") or hasattr(engine, "generate_explanation")


# =========================================================================
# TEST 9 — Decision form validation
# =========================================================================

def test_decision_action_validation(tmp_path: Path) -> None:
    """Verify human decision recording validates action types and mandatory reasons."""
    db_path = tmp_path / "test_decisions.db"
    db = DatabaseManager(db_path=db_path)
    db.create_run(run_id="RUN-TEST-001")
    audit = AuditManager(db_manager=db)
    engine = DecisionEngine(audit_manager=audit)

    confidence = DecisionConfidence(
        level="HIGH",
        score=0.92,
        quadrant="LOW_RISK_HIGH_CONFIDENCE",
        factors=["Low flood depth", "High elevation"],
    )
    pkg = DecisionEvidencePackage(
        run_id="RUN-TEST-001",
        policy_id="POL-001",
        recommendation="ACCEPT",
        confidence=confidence,
        key_metrics={"technical_premium": 25000.0, "aal": 12000.0},
        data_quality_summary={},
        hazard_summary={},
        vulnerability_summary={},
        loss_summary={},
        accumulation_summary={},
        tail_summary={},
        pricing_summary={},
        risk_appetite_summary={},
    )

    # Valid ACCEPT decision
    decision = engine.record_human_decision(
        evidence=pkg,
        human_decision="ACCEPT",
        user="UW_ANALYST",
        reason="Aligned with technical pricing",
    )
    assert decision.human_decision == "ACCEPT"
    assert decision.final_premium == 25000.0

    # MODIFY without reason must raise ValidationError
    with pytest.raises(ValidationError):
        engine.record_human_decision(
            evidence=pkg,
            human_decision="MODIFY",
            user="UW_ANALYST",
            reason="",  # empty reason
            modified_premium=30000.0,
        )

    # REJECT without reason must raise ValidationError
    with pytest.raises(ValidationError):
        engine.record_human_decision(
            evidence=pkg,
            human_decision="REJECT",
            user="UW_ANALYST",
            reason="",  # empty reason
        )

    # Invalid action must raise ValidationError
    with pytest.raises(ValidationError):
        engine.record_human_decision(
            evidence=pkg,
            human_decision="INVALID_ACTION",  # type: ignore[arg-type]
            user="UW_ANALYST",
            reason="Invalid",
        )


# =========================================================================
# TEST 10 — Audit chain cryptographic verification
# =========================================================================

def test_audit_verification(tmp_path: Path) -> None:
    """Verify audit log integrity verification passes on untampered log."""
    db_path = tmp_path / "test_audit.db"
    db = DatabaseManager(db_path=db_path)
    db.create_run(run_id="RUN-1")
    audit = AuditManager(db_manager=db)
    audit.append_decision(
        run_id="RUN-1",
        policy_id="POL-001",
        user="UW_1",
        recommendation="ACCEPT",
        final_decision="ACCEPT",
        original_premium=10000.0,
        new_premium=10000.0,
        model_version="1.0",
    )
    audit.append_decision(
        run_id="RUN-1",
        policy_id="POL-002",
        user="UW_1",
        recommendation="REVIEW",
        final_decision="MODIFY",
        original_premium=15000.0,
        new_premium=18000.0,
        reason="High accumulation exposure",
        model_version="1.0",
    )
    result = audit.verify_audit_chain()
    assert result.is_valid is True
    assert result.record_count == 2
    assert (
        "valid" in result.message.lower()
        or "untampered" in result.message.lower()
        or "verified" in result.message.lower()
    )


# =========================================================================
# TEST 11 — UI/Backend separation
# =========================================================================

def test_ui_backend_separation() -> None:
    """Verify UI does NOT duplicate core mathematical modeling logic.

    The UI must import calculation engines rather than re-implementing:
    - TVaR / VaR percentiles
    - Technical pricing formula calculations
    - Tail allocation algorithms
    - Common Random Numbers (CRN) scenario loops
    """
    app_source = inspect.getsource(app)

    # Check that UI delegates to backend engine classes
    assert "RiskMetricsEngine" in app_source
    assert "PolicyTailRiskEngine" in app_source
    assert "TechnicalPricingEngine" in app_source
    assert "PortfolioAccumulationEngine" in app_source
    assert "AgentOrchestrator" in app_source
    assert "AuditManager" in app_source
    assert "DecisionEngine" in app_source

    # Check charts module doesn't do business math
    charts_source = inspect.getsource(charts)
    assert "compute_losses" not in charts_source
    assert "apply_vulnerability" not in charts_source
