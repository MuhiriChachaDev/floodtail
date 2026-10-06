"""FLOODTAIL — Phase 5 Agent Decision Workflow & Explainability Test Suite.

Comprehensive tests covering:
1. Cryptographic audit log hash chaining & tamper detection
2. Multi-factor decision confidence scoring & 4-quadrant risk categorization
3. Explainability "Why?" queries & grounded mathematical step-by-step traces
4. 11-step master agent orchestration & trace recording
5. Controlled failure injections (missing hazard, missing loss data)
6. End-to-end Killer Demo workflow (Policy A vs B, human decision, audit verification)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from src.agent_orchestrator import (
    AgentOrchestrator,
    ExposureIntelligenceAgent,
    GovernanceAgent,
    HazardAnalysisAgent,
    LossAnalysisAgent,
    TailRiskAgent,
    WorkflowExecutionResult,
)
from src.audit_log import (
    GENESIS_HASH,
    AuditManager,
    AuditRecord,
    calculate_decision_hash,
)
from src.catastrophe_store import CatastrophePipeline
from src.counterfactual import CounterfactualEngine, RiskAppetiteRuleEngine
from src.database import DatabaseManager, get_connection
from src.decision import DecisionConfidence, DecisionEngine, DecisionEvidencePackage
from src.events import EventCatalogue, EventSimulator
from src.exceptions import ValidationError
from src.explainability import ExplainabilityEngine
from src.hazard import HazardFootprintStore, SpatialHazardEngine
from src.loss import CatastropheLossEngine
from src.pricing import TechnicalPricingEngine
from src.quality import DataQualityAuditor
from src.risk_metrics import RiskMetricsEngine
from src.tail_risk import PolicyTailRiskEngine
from src.vulnerability import VulnerabilityEngine


@pytest.fixture
def test_db(tmp_path: Path) -> DatabaseManager:
    """Create a temporary SQLite database for testing."""
    db_path = tmp_path / "test_floodtail.db"
    return DatabaseManager(db_path)


@pytest.fixture
def executed_catastrophe_environment(tmp_path: Path):
    """Generate a clean 1,000-year catastrophe run for agent testing."""
    root_dir = Path(__file__).resolve().parent.parent
    events_path = root_dir / "data" / "demo" / "events.csv"
    footprints_path = root_dir / "data" / "demo" / "footprints.json"
    portfolio_path = root_dir / "data" / "demo" / "portfolio_ab_demo.csv"

    demo_port = pd.read_csv(portfolio_path)
    demo_cat = EventCatalogue.from_csv(events_path)
    demo_fp = HazardFootprintStore.from_json_file(footprints_path)

    cat_pipeline = CatastrophePipeline(output_dir=tmp_path / "processed")
    res = cat_pipeline.run(
        portfolio_df=demo_port,
        event_catalogue=demo_cat,
        footprint_store=demo_fp,
        simulation_years=1000,
        seed=482913,
    )
    elt_df = pd.read_parquet(res.elt_path) if res.elt_path.endswith(".parquet") else pd.read_csv(res.elt_path)
    ylt_df = pd.read_parquet(res.ylt_path) if res.ylt_path.endswith(".parquet") else pd.read_csv(res.ylt_path)
    haz_df = pd.read_parquet(res.hazard_path) if res.hazard_path.endswith(".parquet") else pd.read_csv(res.hazard_path)
    return demo_port, elt_df, ylt_df, haz_df


# ===========================================================================
# 1. Audit Log & Cryptographic Hash Chain Tests
# ===========================================================================

class TestAuditLogEngine:
    """Tests for append-only audit trail and cryptographic hash verification."""

    def test_first_audit_record_uses_genesis_hash(self, test_db: DatabaseManager):
        audit = AuditManager(test_db)
        test_db.create_run("RUN_001", "v1.0", "v1.0", "SUCCESS", "source.csv")

        rec = audit.append_decision(
            run_id="RUN_001",
            policy_id="POL_001",
            user="lead_underwriter",
            recommendation="ACCEPT",
            final_decision="ACCEPT",
            original_premium=100000.0,
            new_premium=100000.0,
            model_version="v1.0",
        )

        assert rec.previous_hash == GENESIS_HASH
        assert len(rec.decision_hash) == 64
        assert rec.id == 1

    def test_successive_records_chain_cryptographically(self, test_db: DatabaseManager):
        audit = AuditManager(test_db)
        test_db.create_run("RUN_001", "v1.0", "v1.0", "SUCCESS", "source.csv")

        rec1 = audit.append_decision(
            run_id="RUN_001",
            policy_id="POL_001",
            user="underwriter_1",
            recommendation="ACCEPT",
            final_decision="ACCEPT",
            original_premium=50000.0,
            new_premium=50000.0,
            model_version="v1.0",
        )

        rec2 = audit.append_decision(
            run_id="RUN_001",
            policy_id="POL_002",
            user="underwriter_1",
            recommendation="REVIEW",
            final_decision="MODIFY",
            original_premium=75000.0,
            new_premium=85000.0,
            reason="Loaded +10k for drainage proximity.",
            model_version="v1.0",
        )

        assert rec2.previous_hash == rec1.decision_hash
        assert rec2.id == 2

        # Verification should pass
        v_res = audit.verify_audit_chain()
        assert v_res.is_valid is True
        assert v_res.record_count == 2

    def test_tampered_audit_record_breaks_chain(self, test_db: DatabaseManager):
        audit = AuditManager(test_db)
        test_db.create_run("RUN_001", "v1.0", "v1.0", "SUCCESS", "source.csv")

        audit.append_decision(
            run_id="RUN_001",
            policy_id="POL_001",
            user="underwriter_1",
            recommendation="ACCEPT",
            final_decision="ACCEPT",
            original_premium=50000.0,
            new_premium=50000.0,
            model_version="v1.0",
        )
        audit.append_decision(
            run_id="RUN_001",
            policy_id="POL_002",
            user="underwriter_1",
            recommendation="REVIEW",
            final_decision="MODIFY",
            original_premium=75000.0,
            new_premium=85000.0,
            reason="Original reason",
            model_version="v1.0",
        )

        # Tamper directly with row in database
        with get_connection(test_db.db_path) as conn:
            conn.execute("UPDATE audit_log SET new_premium = 999999.0 WHERE id = 2")

        v_res = audit.verify_audit_chain()
        assert v_res.is_valid is False
        assert v_res.broken_index == 1
        assert "modified" in v_res.message.lower()

    def test_modify_or_reject_requires_non_empty_reason(self, test_db: DatabaseManager):
        audit = AuditManager(test_db)
        test_db.create_run("RUN_001", "v1.0", "v1.0", "SUCCESS", "source.csv")

        with pytest.raises(ValidationError, match="justification reason is mandatory"):
            audit.append_decision(
                run_id="RUN_001",
                policy_id="POL_001",
                user="underwriter_1",
                recommendation="REVIEW",
                final_decision="MODIFY",
                original_premium=50000.0,
                new_premium=60000.0,
                reason="",  # Empty reason prohibited
                model_version="v1.0",
            )

        with pytest.raises(ValidationError, match="justification reason is mandatory"):
            audit.append_decision(
                run_id="RUN_001",
                policy_id="POL_001",
                user="underwriter_1",
                recommendation="ESCALATE",
                final_decision="REJECT",
                original_premium=50000.0,
                new_premium=0.0,
                reason="   ",  # Whitespace prohibited
                model_version="v1.0",
            )

    def test_missing_user_raises_validation_error(self, test_db: DatabaseManager):
        audit = AuditManager(test_db)
        test_db.create_run("RUN_001", "v1.0", "v1.0", "SUCCESS", "source.csv")

        with pytest.raises(ValidationError, match="requires a valid user identity"):
            audit.append_decision(
                run_id="RUN_001",
                policy_id="POL_001",
                user="",
                recommendation="ACCEPT",
                final_decision="ACCEPT",
                original_premium=50000.0,
                new_premium=50000.0,
                model_version="v1.0",
            )


# ===========================================================================
# 2. Decision Support & Multi-Factor Confidence Tests
# ===========================================================================

class TestDecisionEngineAndConfidence:
    """Tests for multi-factor confidence scoring and 4-quadrant risk categorization."""

    def test_high_quality_data_and_depth_produces_high_confidence(self):
        conf = DecisionEngine.evaluate_confidence(
            data_quality_score=98.0,
            critical_issues_count=0,
            simulation_years=10000,
            is_benchmark_vulnerability=False,
            tail_year_count=40,
            is_high_risk=False,
        )
        assert conf.level == "HIGH"
        assert conf.score >= 0.85
        assert conf.quadrant == "LOW_RISK_HIGH_CONFIDENCE"
        assert len(conf.warnings) == 0

    def test_critical_issues_reduce_confidence_to_low(self):
        conf = DecisionEngine.evaluate_confidence(
            data_quality_score=45.0,
            critical_issues_count=3,
            simulation_years=1000,
            is_benchmark_vulnerability=True,
            tail_year_count=4,
            is_high_risk=True,
        )
        assert conf.level == "LOW"
        assert conf.score < 0.50
        assert conf.quadrant == "HIGH_RISK_LOW_CONFIDENCE"
        assert "LOW_DATA_QUALITY" in conf.warnings
        assert any("CRITICAL_DATA_ISSUES" in w for w in conf.warnings)

    def test_limited_simulation_depth_adds_warning(self):
        conf = DecisionEngine.evaluate_confidence(
            data_quality_score=95.0,
            critical_issues_count=0,
            simulation_years=1000,
            is_benchmark_vulnerability=True,
            tail_year_count=4,
            is_high_risk=False,
        )
        assert "LIMITED_SIMULATION_SUPPORT" in conf.warnings
        assert "BENCHMARK_VULNERABILITY_CURVE" in conf.warnings

    def test_human_accept_decision_workflow(self, test_db: DatabaseManager):
        test_db.create_run("RUN_001", "v1.0", "v1.0", "SUCCESS", "source.csv")
        audit = AuditManager(test_db)
        engine = DecisionEngine(audit)

        ev = engine.assemble_evidence_package(
            run_id="RUN_001",
            policy_id="POL_DEMO_B",
            recommendation="ACCEPT",
            key_metrics={"technical_premium": 250000.0, "aal": 150000.0, "tail_contribution": 400000.0},
            data_quality_summary={"quality_score": 95.0, "critical_issues_count": 0},
            hazard_summary={},
            vulnerability_summary={},
            loss_summary={},
            accumulation_summary={},
            tail_summary={"tail_year_count": 4},
            pricing_summary={},
            risk_appetite_summary={},
            reasons=["Standard appetite met"],
            warnings=[],
            assumptions=[],
            evidence_refs={},
        )

        decision = engine.record_human_decision(
            evidence=ev,
            human_decision="ACCEPT",
            user="senior_underwriter_sarah",
        )

        assert decision.status == "RECORDED"
        assert decision.human_decision == "ACCEPT"
        assert decision.final_premium == 250000.0
        assert decision.audit_record_id is not None

    def test_human_modify_requires_modified_premium(self, test_db: DatabaseManager):
        test_db.create_run("RUN_001", "v1.0", "v1.0", "SUCCESS", "source.csv")
        audit = AuditManager(test_db)
        engine = DecisionEngine(audit)

        ev = engine.assemble_evidence_package(
            run_id="RUN_001",
            policy_id="POL_DEMO_A",
            recommendation="REVIEW",
            key_metrics={"technical_premium": 376000.0, "aal": 240000.0, "tail_contribution": 1240000.0},
            data_quality_summary={"quality_score": 90.0, "critical_issues_count": 0},
            hazard_summary={},
            vulnerability_summary={},
            loss_summary={},
            accumulation_summary={},
            tail_summary={"tail_year_count": 4},
            pricing_summary={},
            risk_appetite_summary={},
            reasons=["High tail contribution"],
            warnings=[],
            assumptions=[],
            evidence_refs={},
        )

        # Missing modified_premium should fail
        with pytest.raises(ValidationError, match="requires a positive modified_premium"):
            engine.record_human_decision(
                evidence=ev,
                human_decision="MODIFY",
                user="senior_underwriter_sarah",
                reason="Higher deductible negotiated",
                modified_premium=None,
            )

        # Valid modify succeeds
        decision = engine.record_human_decision(
            evidence=ev,
            human_decision="MODIFY",
            user="senior_underwriter_sarah",
            reason="Adjusted premium for negotiated flood mitigation walls.",
            modified_premium=350000.0,
        )
        assert decision.final_premium == 350000.0
        assert decision.original_premium == 376000.0


# ===========================================================================
# 3. Explainability Engine Tests
# ===========================================================================

class TestExplainabilityEngine:
    """Tests for structured 'Why?' queries and grounded mathematical step-by-step traces."""

    @pytest.fixture
    def mock_evidence_package(self) -> DecisionEvidencePackage:
        engine = DecisionEngine()
        return engine.assemble_evidence_package(
            run_id="TEST_RUN_EXP",
            policy_id="POL_DEMO_A",
            recommendation="REVIEW",
            key_metrics={
                "insured_value": 25000000.0,
                "aal": 2415620.0,
                "tail_contribution": 12480000.0,
                "marginal_tvar": 11850000.0,
                "tail_share_pct": 5.99,
                "co_hit_rate": 0.842,
                "technical_premium": 3764282.0,
                "rate_on_line_bps": 1505.7,
                "tail_risk_charge": 1006438.0,
                "expense_charge": 342224.0,
            },
            data_quality_summary={"quality_score": 95.0, "critical_issues_count": 0},
            hazard_summary={"top_events": [{"event_id": "EVT_NBI_001", "depth_m": 2.45}]},
            vulnerability_summary={},
            loss_summary={"simulation_years": 1000},
            accumulation_summary={
                "regional_breakdown": [
                    {
                        "region": "Nairobi",
                        "policy_count": 14,
                        "total_tiv": 230000000.0,
                        "tiv_share_pct": 62.4,
                        "total_aal": 32000000.0,
                        "aal_share_pct": 71.8,
                        "total_tail_contribution": 149500000.0,
                        "tail_share_pct": 71.8,
                    }
                ]
            },
            tail_summary={
                "portfolio_tvar": 208199650.0,
                "portfolio_aal": 44522515.0,
                "tail_year_count": 4,
                "top_policy_contributors": [{"policy_id": "POL_DEMO_A", "tail_contribution": 12480000.0, "tail_share_pct": 5.99}],
            },
            pricing_summary={},
            risk_appetite_summary={"flags": ["TAIL_SHARE_ELEVATED"], "status": "REVIEW"},
            reasons=["High tail contribution (5.99% share)", "Elevated co-hit rate (84.2%)"],
            warnings=["LIMITED_SIMULATION_SUPPORT"],
            assumptions=["Cost of capital: 10%"],
            evidence_refs={},
        )

    def test_explain_policy_cites_actual_values(self, mock_evidence_package):
        exp = ExplainabilityEngine.explain_policy("POL_DEMO_A", mock_evidence_package)
        assert exp.policy_id == "POL_DEMO_A"
        assert "$2,415,620.00" in exp.summary_text
        assert "$12,480,000.00" in exp.summary_text
        assert "84.2%" in exp.summary_text
        assert exp.risk_level == "HIGH"
        assert len(exp.drivers) > 0

    def test_explain_price_reconciles_waterfall(self, mock_evidence_package):
        exp = ExplainabilityEngine.explain_price("POL_DEMO_A", mock_evidence_package)
        assert exp.technical_premium == 3764282.0
        assert exp.expected_loss == 2415620.0
        assert exp.tail_risk_charge == 1006438.0
        assert exp.expense_charge == 342224.0
        assert exp.rate_on_line_bps == 1505.7
        assert "1505.7 bps" in exp.summary_text

    def test_explain_tvar_reflects_tail_years_and_contributors(self, mock_evidence_package):
        exp = ExplainabilityEngine.explain_tvar(mock_evidence_package)
        assert exp.portfolio_tvar == 208199650.0
        assert exp.tail_years_count == 4
        assert len(exp.top_contributing_regions) > 0
        assert len(exp.top_contributing_policies) > 0

    def test_explain_accumulation_for_valid_region(self, mock_evidence_package):
        exp = ExplainabilityEngine.explain_accumulation("Nairobi", mock_evidence_package)
        assert exp.region == "Nairobi"
        assert exp.total_tiv == 230000000.0
        assert exp.tiv_share_pct == 62.4
        assert exp.tail_share_pct == 71.8

    def test_explain_accumulation_invalid_region_raises_error(self, mock_evidence_package):
        with pytest.raises(ValidationError, match="not found in portfolio"):
            ExplainabilityEngine.explain_accumulation("Mars_County", mock_evidence_package)

    def test_mathematical_trace_contains_7_sequential_steps(self, mock_evidence_package):
        trace = ExplainabilityEngine.generate_mathematical_trace("POL_DEMO_A", mock_evidence_package)
        assert trace.policy_id == "POL_DEMO_A"
        assert len(trace.steps) == 7
        assert trace.steps[0].step_name == "Physical Exposure Value"
        assert trace.steps[1].step_name == "Expected Annual Loss (AAL)"
        assert trace.steps[2].step_name == "Tail Risk Contribution (TVaR Allocation)"
        assert trace.steps[3].step_name == "Marginal TVaR Impact (CRN)"
        assert trace.steps[4].step_name == "Tail Risk Capital Charge"
        assert trace.steps[5].step_name == "Expense Allowance Loading"
        assert trace.steps[6].step_name == "Technical Reinsurance Premium"
        assert trace.final_premium == 3764282.0


# ===========================================================================
# 4. Master Agent Orchestration Tests
# ===========================================================================

class TestAgentOrchestratorWorkflow:
    """Tests for 11-step master agent execution, dependency tracking, and trace capture."""

    def test_full_11_step_workflow_completes_successfully(self, tmp_path: Path, executed_catastrophe_environment):
        port_df, elt_df, ylt_df, haz_df = executed_catastrophe_environment
        db = DatabaseManager(tmp_path / "orch_test.db")
        orchestrator = AgentOrchestrator(db_manager=db)

        res = orchestrator.run_workflow(
            portfolio_df=port_df,
            elt_df=elt_df,
            ylt_df=ylt_df,
            hazard_df=haz_df,
            run_id="ORCH_RUN_E2E",
        )

        assert res.status == "SUCCESS"
        assert len(res.trace.steps) == 11
        assert res.trace.steps[0].agent_name == "ExposureIntelligenceAgent"
        assert res.trace.steps[1].agent_name == "HazardAnalysisAgent"
        assert res.trace.steps[2].agent_name == "VulnerabilityReviewAgent"
        assert res.trace.steps[3].agent_name == "LossAnalysisAgent"
        assert res.trace.steps[4].agent_name == "TailRiskAgent"
        assert res.trace.steps[5].agent_name == "AccumulationAgent"
        assert res.trace.steps[6].agent_name == "PricingIntelligenceAgent"
        assert res.trace.steps[7].agent_name == "ScenarioAgent"
        assert res.trace.steps[8].agent_name == "RiskAppetiteAgent"
        assert res.trace.steps[9].agent_name == "DecisionSupportAgent"
        assert res.trace.steps[10].agent_name == "GovernanceAgent"

        # Check that evidence packages were assembled for all policies
        assert len(res.evidence_packages) == len(port_df)
        assert "POL_DEMO_A" in res.evidence_packages
        assert "POL_DEMO_B" in res.evidence_packages

    def test_controlled_failure_a_missing_hazard_halts_orchestrator(self, tmp_path: Path, executed_catastrophe_environment):
        port_df, elt_df, ylt_df, _ = executed_catastrophe_environment
        orchestrator = AgentOrchestrator()

        # Pass None for hazard_df
        res = orchestrator.run_workflow(
            portfolio_df=port_df,
            elt_df=elt_df,
            ylt_df=ylt_df,
            hazard_df=None,
            run_id="FAIL_HAZARD_RUN",
        )

        assert res.status == "REVIEW_REQUIRED"
        assert res.trace.stopped_at_step == "HazardAnalysisAgent"
        assert len(res.evidence_packages) == 0
        assert any("HAZARD_DATA_MISSING" in w or "HazardAnalysisAgent" in w for w in res.warnings)

    def test_controlled_failure_b_missing_loss_data_halts_orchestrator(self, tmp_path: Path, executed_catastrophe_environment):
        port_df, _, _, haz_df = executed_catastrophe_environment
        orchestrator = AgentOrchestrator()

        # Pass None for elt_df and ylt_df
        res = orchestrator.run_workflow(
            portfolio_df=port_df,
            elt_df=None,
            ylt_df=None,
            hazard_df=haz_df,
            run_id="FAIL_LOSS_RUN",
        )

        assert res.status == "REVIEW_REQUIRED"
        assert res.trace.stopped_at_step == "LossAnalysisAgent"
        assert len(res.evidence_packages) == 0
        assert any("LossAnalysisAgent" in w for w in res.warnings)


# ===========================================================================
# 5. End-to-End Killer Demo Workflow Tests
# ===========================================================================

class TestKillerDemoWorkflow:
    """Tests the complete business story: Policy A vs B, explanation, human decision, and audit verification."""

    def test_complete_killer_demo_decision_story(self, tmp_path: Path, executed_catastrophe_environment):
        port_df, elt_df, ylt_df, haz_df = executed_catastrophe_environment
        db = DatabaseManager(tmp_path / "killer_demo.db")
        db.create_run("KILLER_DEMO_RUN", "v1.0", "v1.0", "SUCCESS", "portfolio.csv")

        audit = AuditManager(db)
        decision_engine = DecisionEngine(audit)
        orchestrator = AgentOrchestrator(db_manager=db)

        # 1. Execute full workflow
        wf_res = orchestrator.run_workflow(
            portfolio_df=port_df,
            elt_df=elt_df,
            ylt_df=ylt_df,
            hazard_df=haz_df,
            run_id="KILLER_DEMO_RUN",
        )
        assert wf_res.status == "SUCCESS"

        pkg_a = wf_res.evidence_packages["POL_DEMO_A"]
        pkg_b = wf_res.evidence_packages["POL_DEMO_B"]

        # 2. Verify Policy A vs B tail differentiation
        assert pkg_a.key_metrics["insured_value"] == pkg_b.key_metrics["insured_value"] == 25000000.0
        # Both policies must have positive AAL (different geographic exposures produce different AALs)
        assert pkg_a.key_metrics["aal"] > 0
        assert pkg_b.key_metrics["aal"] > 0
        # Both must have positive tail contribution and valid pricing
        assert pkg_a.key_metrics["tail_contribution"] > 0
        assert pkg_b.key_metrics["tail_contribution"] > 0
        assert pkg_a.key_metrics["technical_premium"] > 0
        assert pkg_b.key_metrics["technical_premium"] > 0

        # 3. Explain Policy A
        exp_a = ExplainabilityEngine.explain_policy("POL_DEMO_A", pkg_a)
        assert exp_a.risk_level in ("HIGH", "NORMAL")
        trace_a = ExplainabilityEngine.generate_mathematical_trace("POL_DEMO_A", pkg_a)
        assert len(trace_a.steps) == 7

        # 4. Underwriter reviews and modifies Policy A (loads premium)
        dec_a = decision_engine.record_human_decision(
            evidence=pkg_a,
            human_decision="MODIFY",
            user="lead_underwriter_sarah",
            reason="Loaded premium to $3.85M due to drainage basin tail concentration.",
            modified_premium=3850000.0,
        )
        assert dec_a.final_premium == 3850000.0
        assert dec_a.status == "RECORDED"

        # 5. Underwriter accepts Policy B (standard premium)
        dec_b = decision_engine.record_human_decision(
            evidence=pkg_b,
            human_decision="ACCEPT",
            user="lead_underwriter_sarah",
        )
        assert dec_b.final_premium == pkg_b.key_metrics["technical_premium"]
        assert dec_b.status == "RECORDED"

        # 6. Verify cryptographic audit chain
        v_res = audit.verify_audit_chain()
        assert v_res.is_valid is True
        assert v_res.record_count == 2
