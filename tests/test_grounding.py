"""Tests for FLOODTAIL Numeric Grounding Guard."""

import pytest
from src.grounding import GroundingGuard, GroundingEntry


def test_grounding_guard_registration_and_verification():
    """Validates registration and matching of quantitative claims."""
    guard = GroundingGuard()
    run_id = "RUN-TEST-001"
    
    guard.register_output(
        run_id=run_id,
        field_name="portfolio_aal",
        value=18450000.0,
        source_agent="LossAnalysisAgent",
        metric_category="LOSS",
        unit="KES",
    )
    guard.register_output(
        run_id=run_id,
        field_name="total_technical_premium",
        value=53820000.0,
        source_agent="PricingIntelligenceAgent",
        metric_category="PRICING",
        unit="KES",
    )
    
    # Valid claims within tolerance
    valid, entry = guard.verify_numeric_claim(run_id, 18450000.0)
    assert valid is True
    assert entry.source_agent == "LossAnalysisAgent"
    
    # 0.5% variation should pass 1% tolerance
    valid, _ = guard.verify_numeric_claim(run_id, 18455000.0)
    assert valid is True
    
    # Hallucinated number should fail
    valid, entry = guard.verify_numeric_claim(run_id, 99999999.0)
    assert valid is False
    assert entry is None


def test_grounding_guard_audit_text():
    """Validates auditing text containing grounded and ungrounded figures."""
    guard = GroundingGuard()
    run_id = "RUN-TEST-002"
    
    guard.register_output(
        run_id=run_id,
        field_name="tvar_996",
        value=372400000.0,
        source_agent="TailRiskAgent",
        metric_category="TAIL",
    )
    
    text_grounded = "The 1-in-250 TVaR is KES 372,400,000 as calculated by the tail risk agent."
    audit_res = guard.audit_dialogue_claim(run_id, text_grounded)
    assert audit_res["is_grounded"] is True
    assert audit_res["verified_count"] >= 1
    assert len(audit_res["unverified_numbers"]) == 0
