"""FLOODTAIL — Master Agent Orchestrator & Multi-Agent Decision Workflow.

Orchestrates 11 specialized, typed agent execution steps in dependency order:
1. Exposure Intelligence Agent
2. Hazard Analysis Agent
3. Vulnerability Review Agent
4. Loss Analysis Agent
5. Tail Risk Agent
6. Accumulation Agent (requires tail output from step 5)
7. Pricing Intelligence Agent
8. Scenario / Counterfactual Agent
9. Risk Appetite Agent
10. Decision Support Agent
11. Governance Agent

Enforces typed data contracts, permission boundaries, deterministic failure
handling, and creates complete DecisionEvidencePackages for human decision makers.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

import pandas as pd

from src.accumulation import PortfolioAccumulationEngine
from src.audit_log import AuditManager
from src.counterfactual import CounterfactualEngine, RiskAppetiteRuleEngine
from src.database import DatabaseManager
from src.decision import DecisionConfidence, DecisionEngine, DecisionEvidencePackage
from src.exceptions import FloodtailError, ValidationError
from src.logging_config import get_logger
from src.pricing import TechnicalPricingEngine
from src.quality import DataQualityAuditor
from src.risk_metrics import RiskMetricsEngine
from src.schemas import AgentResult, AgentStatus
from src.tail_risk import PolicyTailRiskEngine

logger = get_logger("agent_orchestrator")


@dataclass
class AgentTraceStep:
    """Individual execution step trace record within the workflow."""

    sequence: int
    agent_name: str
    status: AgentStatus
    start_time: str
    end_time: str
    duration_ms: float
    input_summary: str
    output_summary: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class AgentWorkflowTrace:
    """Full execution trace of the 11-agent decision orchestration."""

    run_id: str
    status: AgentStatus
    total_duration_ms: float
    steps: list[AgentTraceStep] = field(default_factory=list)
    stopped_at_step: Optional[str] = None
    failure_reason: Optional[str] = None


@dataclass
class WorkflowExecutionResult:
    """Container returned by the AgentOrchestrator after workflow completion."""

    run_id: str
    status: AgentStatus
    trace: AgentWorkflowTrace
    evidence_packages: dict[str, DecisionEvidencePackage] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    message: str = "Workflow executed successfully."


# ---------------------------------------------------------------------------
# Individual Specialized Agent Functions
# ---------------------------------------------------------------------------

class ExposureIntelligenceAgent:
    """Agent 1: Inspects data quality, geocoding validity, and exposure anomalies."""

    name = "ExposureIntelligenceAgent"

    @classmethod
    def execute(cls, portfolio_df: pd.DataFrame, dq_auditor: Optional[DataQualityAuditor] = None) -> AgentResult:
        if portfolio_df is None or portfolio_df.empty:
            return AgentResult(
                agent_name=cls.name,
                status="FAILED",
                message="Exposure portfolio is empty or null.",
                warnings=["EMPTY_PORTFOLIO"],
                data={},
            )

        auditor = dq_auditor or DataQualityAuditor()
        dq_report = auditor.audit(portfolio_df)

        score = dq_report.quality_score
        crit_issues = [i for i in dq_report.issues if i.severity == "CRITICAL"]
        status: AgentStatus = "SUCCESS" if score >= 80.0 and len(crit_issues) == 0 else "WARNING"

        summary = {
            "quality_score": score,
            "policy_count": len(portfolio_df),
            "total_tiv": float(portfolio_df["insured_value"].sum()),
            "critical_issues_count": len(crit_issues),
            "total_issues_count": len(dq_report.issues),
            "is_clean": dq_report.passed,
        }

        warnings = [f"{i.issue_type}: {i.message}" for i in dq_report.issues if i.severity in ("CRITICAL", "ERROR")]

        return AgentResult(
            agent_name=cls.name,
            status=status,
            message=f"Exposure evaluated: {len(portfolio_df)} policies, Data Quality Score: {score:.1f}%",
            warnings=warnings,
            data=summary,
        )


class HazardAnalysisAgent:
    """Agent 2: Analyzes spatial flood footprints and event hit occurrences."""

    name = "HazardAnalysisAgent"

    @classmethod
    def execute(cls, hazard_df: Optional[pd.DataFrame]) -> AgentResult:
        if hazard_df is None or hazard_df.empty:
            return AgentResult(
                agent_name=cls.name,
                status="FAILED",
                message="Hazard evaluation data missing or empty.",
                warnings=["HAZARD_DATA_MISSING"],
                data={},
            )

        affected_pols = hazard_df[hazard_df["depth_m"] > 0]["policy_id"].nunique()
        event_count = hazard_df["occurrence_id"].nunique()
        mean_depth = float(hazard_df[hazard_df["depth_m"] > 0]["depth_m"].mean()) if affected_pols > 0 else 0.0
        max_depth = float(hazard_df["depth_m"].max())

        summary = {
            "total_impact_records": len(hazard_df),
            "affected_policies_count": affected_pols,
            "unique_event_occurrences": event_count,
            "mean_affected_depth_m": round(mean_depth, 2),
            "max_flood_depth_m": round(max_depth, 2),
        }

        return AgentResult(
            agent_name=cls.name,
            status="SUCCESS",
            message=f"Hazard evaluated: {event_count} events impacted {affected_pols} policies (Max depth: {max_depth:.2f}m).",
            warnings=[],
            data=summary,
        )


class VulnerabilityReviewAgent:
    """Agent 3: Evaluates depth-damage curves and construction class modifiers."""

    name = "VulnerabilityReviewAgent"

    @classmethod
    def execute(cls, portfolio_df: pd.DataFrame) -> AgentResult:
        cclasses = portfolio_df["construction_class"].unique().tolist() if "construction_class" in portfolio_df else []
        ptypes = portfolio_df["property_type"].unique().tolist() if "property_type" in portfolio_df else []

        summary = {
            "curve_version": "v1.0-prototype-benchmark",
            "property_types_evaluated": ptypes,
            "construction_classes": cclasses,
            "calibration_status": "PROTOTYPE_BENCHMARK",
        }

        warnings = ["BENCHMARK_VULNERABILITY_CURVE: Prototype curves used; Kenya-specific calibration not established."]

        return AgentResult(
            agent_name=cls.name,
            status="SUCCESS",
            message="Vulnerability benchmark curves applied across property classes.",
            warnings=warnings,
            data=summary,
        )


class LossAnalysisAgent:
    """Agent 4: Reconciles ground-up and net losses across ELT and YLT."""

    name = "LossAnalysisAgent"

    @classmethod
    def execute(cls, elt_df: pd.DataFrame, ylt_df: pd.DataFrame) -> AgentResult:
        if elt_df is None or elt_df.empty or ylt_df is None or ylt_df.empty:
            return AgentResult(
                agent_name=cls.name,
                status="FAILED",
                message="ELT or YLT loss data missing.",
                warnings=["LOSS_DATA_MISSING"],
                data={},
            )

        tot_elt = float(elt_df["loss"].sum())
        tot_ylt = float(ylt_df["annual_loss"].sum())
        sim_years = len(ylt_df)

        reconciled = abs(tot_elt - tot_ylt) < 1e-3
        status: AgentStatus = "SUCCESS" if reconciled else "FAILED"

        summary = {
            "total_simulated_loss": tot_ylt,
            "portfolio_aal": tot_ylt / sim_years,
            "simulation_years": sim_years,
            "elt_records_count": len(elt_df),
            "max_annual_loss": float(ylt_df["annual_loss"].max()),
            "loss_reconciliation_passed": reconciled,
        }

        warnings = [] if reconciled else ["LOSS_RECONCILIATION_FAILED: Total ELT loss does not equal Total YLT loss."]

        return AgentResult(
            agent_name=cls.name,
            status=status,
            message=f"Losses evaluated: Portfolio AAL = ${tot_ylt / sim_years:,.2f} across {sim_years} years.",
            warnings=warnings,
            data=summary,
        )


class AccumulationAgent:
    """Agent 5: Calculates geographic concentration, HHI, and spatial co-hits."""

    name = "AccumulationAgent"

    @classmethod
    def execute(cls, portfolio_df: pd.DataFrame, elt_df: pd.DataFrame, tail_dataframe: pd.DataFrame) -> AgentResult:
        engine = PortfolioAccumulationEngine()
        accum_res = engine.evaluate(portfolio_df, elt_df, tail_dataframe)

        reg_data = [
            {
                "region": r.region,
                "policy_count": r.policy_count,
                "total_tiv": r.total_tiv,
                "tiv_share_pct": r.tiv_share_pct,
                "total_aal": r.total_aal,
                "aal_share_pct": r.aal_share_pct,
                "total_tail_contribution": r.total_tail_contribution,
                "tail_share_pct": r.tail_share_pct,
            }
            for r in accum_res.regional_breakdown
        ]

        summary = {
            "regional_breakdown": reg_data,
            "top_1pct_tiv_share": accum_res.tiv_concentration_top1_pct,
            "top_1pct_tail_share": accum_res.loss_concentration_top1_pct,
            "regional_hhi": accum_res.regional_tiv_hhi,
            "accumulation_df": accum_res.accumulation_dataframe,
            "co_hit_metrics": accum_res.co_hit_metrics,
        }

        return AgentResult(
            agent_name=cls.name,
            status="SUCCESS",
            message=f"Accumulation analyzed across {len(reg_data)} regions. Top region: {reg_data[0]['region'] if reg_data else 'N/A'}.",
            warnings=[],
            data=summary,
        )


class TailRiskAgent:
    """Agent 6: Evaluates tail risk, VaR, TVaR, and allocation reconciliation."""

    name = "TailRiskAgent"

    @classmethod
    def execute(cls, ylt_df: pd.DataFrame, elt_df: pd.DataFrame, portfolio_df: pd.DataFrame, confidence: float = 0.996) -> AgentResult:
        sim_years = len(ylt_df)
        risk_engine = RiskMetricsEngine(default_confidence=confidence)
        metrics = risk_engine.evaluate(ylt_df)

        tail_engine = PolicyTailRiskEngine()
        tail_alloc = tail_engine.allocate_tail_risk(
            elt_df=elt_df,
            ylt_df=ylt_df,
            portfolio_df=portfolio_df,
            tail_set=metrics.tail_set_996,
            portfolio_tvar=metrics.tvar_996,
            portfolio_aal=metrics.aal,
        )

        warnings = []
        if sim_years < 10000:
            warnings.append(
                f"LIMITED_TAIL_SAMPLE: 1-in-250 tail contains only {metrics.tail_set_996.tail_year_count} observations in current {sim_years}-year run."
            )

        status: AgentStatus = "SUCCESS" if tail_alloc.tail_reconciled and tail_alloc.aal_reconciled else "FAILED"

        summary = {
            "portfolio_aal": metrics.aal,
            "portfolio_var_996": metrics.var_996,
            "portfolio_tvar_996": metrics.tvar_996,
            "tail_year_count": metrics.tail_set_996.tail_year_count,
            "tail_allocation": tail_alloc,
            "tail_dataframe": tail_alloc.tail_dataframe,
            "top_policy_contributors": [
                {
                    "policy_id": r.policy_id,
                    "tail_contribution": r.tail_contribution,
                    "tail_share_pct": r.tail_share_pct,
                    "tail_rank": r.tail_rank,
                }
                for r in tail_alloc.policy_records[:5]
            ],
        }

        return AgentResult(
            agent_name=cls.name,
            status=status,
            message=f"Tail risk evaluated: TVaR(99.6%) = ${metrics.tvar_996:,.2f} across {metrics.tail_set_996.tail_year_count} tail years.",
            warnings=warnings,
            data=summary,
        )


class PricingIntelligenceAgent:
    """Agent 7: Evaluates risk-based technical pricing and cost of capital."""

    name = "PricingIntelligenceAgent"

    @classmethod
    def execute(cls, tail_dataframe: pd.DataFrame, coc_rate: float = 0.10, exp_rate: float = 0.10) -> AgentResult:
        engine = TechnicalPricingEngine(
            cost_of_capital_rate=coc_rate,
            expense_rate=exp_rate,
        )
        pricing_res = engine.calculate_pricing(tail_df=tail_dataframe)

        status: AgentStatus = "SUCCESS" if pricing_res.pricing_reconciled else "FAILED"

        summary = {
            "total_technical_premium": pricing_res.total_technical_premium,
            "total_expected_loss": pricing_res.total_expected_loss,
            "total_tail_charge": pricing_res.total_tail_charge,
            "total_expense": pricing_res.total_expense,
            "pricing_dataframe": pricing_res.pricing_dataframe,
            "pricing_reconciled": pricing_res.pricing_reconciled,
        }

        return AgentResult(
            agent_name=cls.name,
            status=status,
            message=f"Technical pricing calculated: Total Portfolio Premium = ${pricing_res.total_technical_premium:,.2f}.",
            warnings=[],
            data=summary,
        )


class ScenarioAgent:
    """Agent 8: Evaluates counterfactual marginal impacts and stress deltas."""

    name = "ScenarioAgent"

    @classmethod
    def execute(cls, ylt_df: pd.DataFrame, elt_df: pd.DataFrame, portfolio_df: pd.DataFrame, tail_df: pd.DataFrame, confidence: float = 0.996) -> AgentResult:
        sim_years = len(ylt_df)
        all_pids = portfolio_df["policy_id"].astype(str).tolist()
        pal_matrix = PolicyTailRiskEngine.build_policy_annual_loss_matrix(elt_df, all_pids, sim_years)

        cf_engine = CounterfactualEngine(alpha=confidence)
        marginal_impacts = cf_engine.calculate_marginal_tvars(
            ylt_df=ylt_df,
            pal_matrix=pal_matrix,
            tail_df=tail_df,
        )

        return AgentResult(
            agent_name=cls.name,
            status="SUCCESS",
            message=f"Scenario counterfactuals evaluated: {len(marginal_impacts)} marginal TVaR impacts computed (CRN).",
            warnings=[],
            data={"marginal_results": marginal_impacts, "pal_matrix": pal_matrix},
        )


class RiskAppetiteAgent:
    """Agent 9: Applies deterministic policy underwriting governance rules."""

    name = "RiskAppetiteAgent"

    @classmethod
    def execute(cls, tail_records: list[Any], marginal_impacts: list[Any], co_hit_metrics: list[Any]) -> AgentResult:
        rule_engine = RiskAppetiteRuleEngine()
        recommendations = rule_engine.evaluate_policy_recommendations(
            tail_records=tail_records,
            marginal_impacts=marginal_impacts,
            co_hit_metrics=co_hit_metrics,
        )

        accept_count = sum(1 for r in recommendations if r.recommendation == "ACCEPT")
        review_count = sum(1 for r in recommendations if r.recommendation == "REVIEW")
        escalate_count = sum(1 for r in recommendations if r.recommendation == "ESCALATE")

        summary = {
            "total_evaluated": len(recommendations),
            "accept_count": accept_count,
            "review_count": review_count,
            "escalate_count": escalate_count,
            "recommendations": recommendations,
        }

        return AgentResult(
            agent_name=cls.name,
            status="SUCCESS",
            message=f"Risk appetite evaluated: {accept_count} ACCEPT, {review_count} REVIEW, {escalate_count} ESCALATE.",
            warnings=[],
            data=summary,
        )


class DecisionSupportAgent:
    """Agent 10: Assembles complete DecisionEvidencePackages with confidence scoring."""

    name = "DecisionSupportAgent"

    @classmethod
    def execute(
        cls,
        run_id: str,
        portfolio_df: pd.DataFrame,
        dq_data: dict[str, Any],
        hazard_data: dict[str, Any],
        vuln_data: dict[str, Any],
        loss_data: dict[str, Any],
        accum_data: dict[str, Any],
        tail_data: dict[str, Any],
        pricing_data: dict[str, Any],
        appetite_data: dict[str, Any],
        sim_years: int = 1000,
        model_version: str = "v1.0",
        data_version: str = "v1.0",
    ) -> AgentResult:
        decision_engine = DecisionEngine()
        recs = appetite_data.get("recommendations", [])
        pricing_df = pricing_data.get("pricing_dataframe")
        tail_alloc = tail_data.get("tail_allocation")

        evidence_packages: dict[str, DecisionEvidencePackage] = {}

        for rec in recs:
            pol_id = rec.policy_id
            p_row = pricing_df[pricing_df["policy_id"] == pol_id].iloc[0] if pricing_df is not None else None

            key_m = {
                "insured_value": float(p_row["insured_value"]) if p_row is not None and "insured_value" in p_row else 0.0,
                "aal": float(rec.aal),
                "tail_contribution": float(rec.tail_contribution),
                "marginal_tvar": float(rec.marginal_tvar),
                "tail_share_pct": float(rec.tail_share_pct),
                "co_hit_rate": float(rec.co_hit_rate),
                "technical_premium": float(p_row["technical_premium"]) if p_row is not None and "technical_premium" in p_row else 0.0,
                "rate_on_line_bps": float(p_row["rate_on_line_bps"]) if p_row is not None and "rate_on_line_bps" in p_row else 0.0,
                "tail_risk_charge": float(p_row["tail_charge"]) if p_row is not None and "tail_charge" in p_row else 0.0,
                "expense_charge": float(p_row["expense"]) if p_row is not None and "expense" in p_row else 0.0,
            }

            pkg = decision_engine.assemble_evidence_package(
                run_id=run_id,
                policy_id=pol_id,
                recommendation=rec.recommendation,
                key_metrics=key_m,
                data_quality_summary=dq_data,
                hazard_summary=hazard_data,
                vulnerability_summary=vuln_data,
                loss_summary=loss_data,
                accumulation_summary=accum_data,
                tail_summary=tail_data,
                pricing_summary=pricing_data,
                risk_appetite_summary={"flags": rec.risk_flags, "status": rec.recommendation},
                reasons=rec.reason_codes,
                warnings=[],
                assumptions=["Prototype Cost of Capital: 10%", "Prototype Expense Ratio: 10%"],
                evidence_refs={"run_id": run_id, "policy_id": pol_id},
                simulation_years=sim_years,
                model_version=model_version,
                data_version=data_version,
            )
            evidence_packages[pol_id] = pkg

        return AgentResult(
            agent_name=cls.name,
            status="SUCCESS",
            message=f"Decision support packages assembled for {len(evidence_packages)} policies.",
            warnings=[],
            data={"evidence_packages": evidence_packages},
        )


class GovernanceAgent:
    """Agent 11: Validates complete workflow state, trace consistency, and audit readiness."""

    name = "GovernanceAgent"

    @classmethod
    def execute(cls, trace: AgentWorkflowTrace, evidence_packages: dict[str, DecisionEvidencePackage]) -> AgentResult:
        failed_steps = [s for s in trace.steps if s.status == "FAILED"]
        if failed_steps:
            return AgentResult(
                agent_name=cls.name,
                status="FAILED",
                message=f"Governance check failed: {len(failed_steps)} step(s) failed in orchestration.",
                warnings=[f"FAILED_STEP_{s.agent_name}" for s in failed_steps],
                data={"ready_for_human": False},
            )

        if not evidence_packages:
            return AgentResult(
                agent_name=cls.name,
                status="WARNING",
                message="No decision evidence packages were assembled.",
                warnings=["NO_DECISION_PACKAGES"],
                data={"ready_for_human": False},
            )

        return AgentResult(
            agent_name=cls.name,
            status="SUCCESS",
            message=f"Governance validation PASSED. {len(evidence_packages)} policies ready for human underwriting review.",
            warnings=[],
            data={"ready_for_human": True, "policy_count": len(evidence_packages)},
        )


# ---------------------------------------------------------------------------
# Master Orchestrator
# ---------------------------------------------------------------------------

class AgentOrchestrator:
    """Master controller executing the 11-agent reinsurance decision workflow."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db_manager = db_manager
        self.audit_manager = AuditManager(db_manager) if db_manager else None

    def run_workflow(
        self,
        portfolio_df: pd.DataFrame,
        elt_df: Optional[pd.DataFrame],
        ylt_df: Optional[pd.DataFrame],
        hazard_df: Optional[pd.DataFrame],
        run_id: str = "ORCH_RUN_001",
        confidence: float = 0.996,
        cost_of_capital_rate: float = 0.10,
        expense_rate: float = 0.10,
        model_version: str = "v1.0",
        data_version: str = "v1.0",
    ) -> WorkflowExecutionResult:
        """Execute the 11 specialized agent steps sequentially with strict validation."""
        start_time_all = time.perf_counter()
        trace_steps: list[AgentTraceStep] = []
        seq = 1
        all_warnings: list[str] = []

        logger.info("=== FLOODTAIL Master Agent Orchestrator Started (run_id=%s) ===", run_id)

        def record_step(agent_name: str, res: AgentResult, in_summary: str, out_summary: str, d_ms: float) -> None:
            ts_now = datetime.now(timezone.utc).isoformat()
            trace_steps.append(
                AgentTraceStep(
                    sequence=len(trace_steps) + 1,
                    agent_name=agent_name,
                    status=res.status,
                    start_time=ts_now,
                    end_time=ts_now,
                    duration_ms=round(d_ms, 2),
                    input_summary=in_summary,
                    output_summary=out_summary,
                    warnings=res.warnings,
                )
            )
            all_warnings.extend(res.warnings)

        # 1. Exposure Intelligence Agent
        t0 = time.perf_counter()
        res_exp = ExposureIntelligenceAgent.execute(portfolio_df)
        d = (time.perf_counter() - t0) * 1000
        record_step(
            ExposureIntelligenceAgent.name,
            res_exp,
            f"Portfolio DataFrame ({len(portfolio_df) if portfolio_df is not None else 0} rows)",
            res_exp.message or "",
            d,
        )
        if res_exp.status == "FAILED":
            return self._halt_workflow(run_id, trace_steps, start_time_all, ExposureIntelligenceAgent.name, res_exp.message or "Exposure failed")

        # 2. Hazard Analysis Agent
        t0 = time.perf_counter()
        res_haz = HazardAnalysisAgent.execute(hazard_df)
        d = (time.perf_counter() - t0) * 1000
        record_step(
            HazardAnalysisAgent.name,
            res_haz,
            f"Hazard DataFrame ({len(hazard_df) if hazard_df is not None else 0} rows)",
            res_haz.message or "",
            d,
        )
        if res_haz.status == "FAILED":
            return self._halt_workflow(run_id, trace_steps, start_time_all, HazardAnalysisAgent.name, res_haz.message or "Hazard failed")

        # 3. Vulnerability Review Agent
        t0 = time.perf_counter()
        res_vuln = VulnerabilityReviewAgent.execute(portfolio_df)
        d = (time.perf_counter() - t0) * 1000
        record_step(
            VulnerabilityReviewAgent.name,
            res_vuln,
            "Portfolio construction classes",
            res_vuln.message or "",
            d,
        )

        # 4. Loss Analysis Agent
        t0 = time.perf_counter()
        res_loss = LossAnalysisAgent.execute(elt_df, ylt_df)  # type: ignore[arg-type]
        d = (time.perf_counter() - t0) * 1000
        record_step(
            LossAnalysisAgent.name,
            res_loss,
            f"ELT ({len(elt_df) if elt_df is not None else 0} rows), YLT ({len(ylt_df) if ylt_df is not None else 0} rows)",
            res_loss.message or "",
            d,
        )
        if res_loss.status == "FAILED":
            return self._halt_workflow(run_id, trace_steps, start_time_all, LossAnalysisAgent.name, res_loss.message or "Loss calculation failed")

        # 5. Tail Risk Agent
        t0 = time.perf_counter()
        res_tail = TailRiskAgent.execute(ylt_df, elt_df, portfolio_df, confidence)  # type: ignore[arg-type]
        d = (time.perf_counter() - t0) * 1000
        record_step(
            TailRiskAgent.name,
            res_tail,
            f"YLT, ELT, confidence={confidence}",
            res_tail.message or "",
            d,
        )
        if res_tail.status == "FAILED":
            return self._halt_workflow(run_id, trace_steps, start_time_all, TailRiskAgent.name, res_tail.message or "Tail allocation failed")

        # 6. Accumulation Agent
        t0 = time.perf_counter()
        res_accum = AccumulationAgent.execute(portfolio_df, elt_df, res_tail.data["tail_dataframe"])  # type: ignore[arg-type]
        d = (time.perf_counter() - t0) * 1000
        record_step(
            AccumulationAgent.name,
            res_accum,
            "Portfolio, ELT, Tail Data",
            res_accum.message or "",
            d,
        )

        # 7. Pricing Intelligence Agent
        t0 = time.perf_counter()
        res_price = PricingIntelligenceAgent.execute(
            res_tail.data["tail_dataframe"],
            coc_rate=cost_of_capital_rate,
            exp_rate=expense_rate,
        )
        d = (time.perf_counter() - t0) * 1000
        record_step(
            PricingIntelligenceAgent.name,
            res_price,
            f"Tail Data, CoC={cost_of_capital_rate}, Expense={expense_rate}",
            res_price.message or "",
            d,
        )
        if res_price.status == "FAILED":
            return self._halt_workflow(run_id, trace_steps, start_time_all, PricingIntelligenceAgent.name, res_price.message or "Pricing failed")

        # 8. Scenario / Counterfactual Agent
        t0 = time.perf_counter()
        res_scen = ScenarioAgent.execute(ylt_df, elt_df, portfolio_df, res_tail.data["tail_dataframe"], confidence)  # type: ignore[arg-type]
        d = (time.perf_counter() - t0) * 1000
        record_step(
            ScenarioAgent.name,
            res_scen,
            "YLT, ELT, CRN counterfactual",
            res_scen.message or "",
            d,
        )

        # 9. Risk Appetite Agent
        t0 = time.perf_counter()
        res_appetite = RiskAppetiteAgent.execute(
            tail_records=res_tail.data["tail_allocation"].policy_records,
            marginal_impacts=res_scen.data["marginal_results"],
            co_hit_metrics=res_accum.data["co_hit_metrics"],
        )
        d = (time.perf_counter() - t0) * 1000
        record_step(
            RiskAppetiteAgent.name,
            res_appetite,
            "Tail, Pricing, Marginal TVaR, Accumulation",
            res_appetite.message or "",
            d,
        )

        # 10. Decision Support Agent
        t0 = time.perf_counter()
        sim_years = len(ylt_df) if ylt_df is not None else 1000
        res_decision = DecisionSupportAgent.execute(
            run_id=run_id,
            portfolio_df=portfolio_df,
            dq_data=res_exp.data,
            hazard_data=res_haz.data,
            vuln_data=res_vuln.data,
            loss_data=res_loss.data,
            accum_data=res_accum.data,
            tail_data=res_tail.data,
            pricing_data=res_price.data,
            appetite_data=res_appetite.data,
            sim_years=sim_years,
            model_version=model_version,
            data_version=data_version,
        )
        d = (time.perf_counter() - t0) * 1000
        record_step(
            DecisionSupportAgent.name,
            res_decision,
            "All Agent Outputs",
            res_decision.message or "",
            d,
        )

        # 11. Governance Agent
        t0 = time.perf_counter()
        ev_pkgs = res_decision.data.get("evidence_packages", {})
        temp_trace = AgentWorkflowTrace(
            run_id=run_id,
            status="SUCCESS",
            total_duration_ms=0.0,
            steps=trace_steps,
        )
        res_gov = GovernanceAgent.execute(temp_trace, ev_pkgs)
        d = (time.perf_counter() - t0) * 1000
        record_step(
            GovernanceAgent.name,
            res_gov,
            f"Workflow trace ({len(trace_steps)} steps)",
            res_gov.message or "",
            d,
        )

        tot_duration = (time.perf_counter() - start_time_all) * 1000
        final_trace = AgentWorkflowTrace(
            run_id=run_id,
            status="SUCCESS",
            total_duration_ms=round(tot_duration, 2),
            steps=trace_steps,
        )

        logger.info(
            "=== FLOODTAIL Master Agent Orchestrator Finished (status=SUCCESS, duration=%.2fms) ===",
            tot_duration,
        )

        return WorkflowExecutionResult(
            run_id=run_id,
            status="SUCCESS",
            trace=final_trace,
            evidence_packages=ev_pkgs,
            warnings=sorted(list(set(all_warnings))),
            message="Orchestration completed successfully; evidence ready for underwriter review.",
        )

    def _halt_workflow(
        self,
        run_id: str,
        steps: list[AgentTraceStep],
        start_time_all: float,
        failed_agent: str,
        reason: str,
    ) -> WorkflowExecutionResult:
        """Halt workflow execution immediately when a critical agent fails."""
        tot_duration = (time.perf_counter() - start_time_all) * 1000
        logger.error("Workflow halted at agent '%s': %s", failed_agent, reason)

        trace = AgentWorkflowTrace(
            run_id=run_id,
            status="FAILED",
            total_duration_ms=round(tot_duration, 2),
            steps=steps,
            stopped_at_step=failed_agent,
            failure_reason=reason,
        )

        return WorkflowExecutionResult(
            run_id=run_id,
            status="REVIEW_REQUIRED",
            trace=trace,
            evidence_packages={},
            warnings=[f"WORKFLOW_HALTED_AT_{failed_agent}: {reason}"],
            message=f"Workflow halted at {failed_agent}: {reason}. Human review required.",
        )
