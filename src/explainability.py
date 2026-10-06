"""FLOODTAIL — Explainable AI & Actuarial Attribution Engine.

Generates deterministic, structured, and auditable natural language explanations
and mathematical step-by-step traces grounded entirely in empirical model evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from src.decision import DecisionEvidencePackage
from src.exceptions import ValidationError
from src.logging_config import get_logger

logger = get_logger("explainability")


@dataclass
class PolicyExplanation:
    """Structured explanation for a policy's overall risk profile."""

    policy_id: str
    summary_text: str
    risk_level: str
    drivers: list[str]
    co_hit_context: str
    top_events: list[dict[str, Any]]
    recommendation_rationale: str


@dataclass
class PriceExplanation:
    """Structured explanation for a policy's technical premium breakdown."""

    policy_id: str
    summary_text: str
    technical_premium: float
    expected_loss: float
    tail_risk_charge: float
    expense_charge: float
    rate_on_line_bps: float
    premium_drivers: list[str]
    formula_decomposition: str


@dataclass
class TVaRExplanation:
    """Structured explanation for portfolio-level tail risk (TVaR)."""

    summary_text: str
    portfolio_tvar: float
    portfolio_aal: float
    tail_years_count: int
    top_contributing_regions: list[dict[str, Any]]
    top_contributing_policies: list[dict[str, Any]]
    systemic_drivers: list[str]


@dataclass
class AccumulationExplanation:
    """Structured explanation for regional accumulation and spatial concentration."""

    region: str
    summary_text: str
    total_tiv: float
    tiv_share_pct: float
    total_aal: float
    aal_share_pct: float
    tail_contribution: float
    tail_share_pct: float
    co_hit_density: str
    drivers: list[str]


@dataclass
class RecommendationExplanation:
    """Structured explanation for an automated underwriting recommendation."""

    policy_id: str
    recommendation: str
    confidence_level: str
    confidence_quadrant: str
    summary_text: str
    primary_reasons: list[str]
    risk_appetite_flags: list[str]
    model_warnings: list[str]
    action_guidance: str


@dataclass
class MathematicalTraceStep:
    """Single step in the end-to-end actuarial mathematical derivation."""

    step_number: int
    step_name: str
    formula: str
    inputs: dict[str, Any]
    output_name: str
    output_value: Any
    interpretation: str


@dataclass
class MathematicalTrace:
    """End-to-end mathematical derivation from physical exposure to technical price."""

    policy_id: str
    steps: list[MathematicalTraceStep]
    final_premium: float


class ExplainabilityEngine:
    """Engine providing grounded, reproducible risk interpretations and traces."""

    @staticmethod
    def explain_policy(policy_id: str, evidence: DecisionEvidencePackage) -> PolicyExplanation:
        """Generate a structured explanation of a policy's physical and systemic risk."""
        if evidence.policy_id != policy_id:
            raise ValidationError(f"Evidence package is for policy '{evidence.policy_id}', not '{policy_id}'.")

        m = evidence.key_metrics
        tiv = m.get("insured_value", 0.0)
        aal = m.get("aal", 0.0)
        tail_contrib = m.get("tail_contribution", 0.0)
        tail_share = m.get("tail_share_pct", 0.0)
        co_hit_rate = m.get("co_hit_rate", 0.0)
        prem = m.get("technical_premium", 0.0)
        rec = evidence.recommendation

        drivers = []
        if tail_share > 5.0:
            drivers.append(f"Significant portfolio tail contribution ({tail_share:.2f}% of portfolio TVaR).")
        if co_hit_rate > 0.5:
            drivers.append(f"High spatial co-occurrence ({co_hit_rate * 100:.1f}% of flood events affect multiple policies).")
        if aal / max(tiv, 1.0) > 0.05:
            drivers.append(f"Elevated expected loss ratio ({(aal / tiv) * 100:.2f}% of TIV).")

        summary = (
            f"Policy {policy_id} (TIV: ${tiv:,.2f}) has an Average Annual Loss of ${aal:,.2f} "
            f"and contributes ${tail_contrib:,.2f} ({tail_share:.2f}%) to portfolio tail risk (TVaR). "
            f"The policy has a spatial co-hit rate of {co_hit_rate * 100:.1f}%, leading to an AI recommendation of {rec}."
        )

        top_events = evidence.hazard_summary.get("top_events", [])

        return PolicyExplanation(
            policy_id=policy_id,
            summary_text=summary,
            risk_level="HIGH" if rec in ("REVIEW", "ESCALATE") else "NORMAL",
            drivers=drivers if drivers else ["Standalone expected loss is consistent with baseline exposure."],
            co_hit_context=f"{co_hit_rate * 100:.1f}% of flood occurrences co-impact other insured assets.",
            top_events=top_events,
            recommendation_rationale=f"Recommended {rec} due to: {'; '.join(evidence.reasons) if evidence.reasons else 'Risk within standard appetite'}.",
        )

    @staticmethod
    def explain_price(policy_id: str, evidence: DecisionEvidencePackage) -> PriceExplanation:
        """Explain the technical pricing waterfall and capital loading drivers."""
        if evidence.policy_id != policy_id:
            raise ValidationError(f"Evidence package is for policy '{evidence.policy_id}', not '{policy_id}'.")

        m = evidence.key_metrics
        aal = m.get("aal", 0.0)
        tail_charge = m.get("tail_risk_charge", 0.0)
        expense = m.get("expense_charge", 0.0)
        premium = m.get("technical_premium", 0.0)
        rol_bps = m.get("rate_on_line_bps", 0.0)
        tiv = m.get("insured_value", 0.0)

        drivers = [
            f"Baseline Expected Loss (AAL): ${aal:,.2f} ({(aal / max(premium, 1e-9)) * 100:.1f}% of premium)",
            f"Tail Risk Capital Charge: ${tail_charge:,.2f} ({(tail_charge / max(premium, 1e-9)) * 100:.1f}% of premium)",
            f"Expense Loading: ${expense:,.2f} ({(expense / max(premium, 1e-9)) * 100:.1f}% of premium)",
        ]

        summary = (
            f"Technical Premium for {policy_id} is ${premium:,.2f} (Rate-on-Line: {rol_bps:.1f} bps). "
            f"The premium is composed of ${aal:,.2f} Expected Loss + ${tail_charge:,.2f} Tail Capital Charge "
            f"+ ${expense:,.2f} Expense Allowance."
        )

        decomposition = (
            f"${premium:,.2f} = ${aal:,.2f} (AAL) + ${tail_charge:,.2f} (10% Cost of Capital × (${m.get('tail_contribution', 0.0):,.2f} - ${aal:,.2f})) "
            f"+ ${expense:,.2f} (10% Expense Loading)"
        )

        return PriceExplanation(
            policy_id=policy_id,
            summary_text=summary,
            technical_premium=round(premium, 2),
            expected_loss=round(aal, 2),
            tail_risk_charge=round(tail_charge, 2),
            expense_charge=round(expense, 2),
            rate_on_line_bps=round(rol_bps, 2),
            premium_drivers=drivers,
            formula_decomposition=decomposition,
        )

    @staticmethod
    def explain_tvar(evidence: DecisionEvidencePackage) -> TVaRExplanation:
        """Explain the systemic drivers of portfolio-level TVaR."""
        tail = evidence.tail_summary
        tvar = float(tail.get("portfolio_tvar", 0.0))
        aal = float(tail.get("portfolio_aal", 0.0))
        tail_years = int(tail.get("tail_year_count", 4))
        top_pols = tail.get("top_policy_contributors", [])
        top_regs = evidence.accumulation_summary.get("regional_breakdown", [])

        summary = (
            f"Portfolio TVaR(99.6%) is ${tvar:,.2f} across {tail_years} simulated tail years, "
            f"representing a ${tvar - aal:,.2f} tail risk margin above Portfolio AAL (${aal:,.2f})."
        )

        drivers = [
            f"Tail loss is driven by extreme annual aggregate events exceeding the 1-in-250 year threshold.",
            f"Top regional concentration: {top_regs[0]['region'] if top_regs else 'N/A'} generates {top_regs[0]['tail_share_pct'] if top_regs else 0.0:.1f}% of tail risk.",
        ]

        return TVaRExplanation(
            summary_text=summary,
            portfolio_tvar=round(tvar, 2),
            portfolio_aal=round(aal, 2),
            tail_years_count=tail_years,
            top_contributing_regions=top_regs[:5],
            top_contributing_policies=top_pols[:5],
            systemic_drivers=drivers,
        )

    @staticmethod
    def explain_accumulation(region: str, evidence: DecisionEvidencePackage) -> AccumulationExplanation:
        """Explain regional accumulation and spatial risk concentration."""
        regs = evidence.accumulation_summary.get("regional_breakdown", [])
        matched = next((r for r in regs if r["region"].lower() == region.lower()), None)
        if not matched:
            raise ValidationError(f"Region '{region}' not found in portfolio accumulation summary.")

        tiv = float(matched["total_tiv"])
        tiv_share = float(matched["tiv_share_pct"])
        aal = float(matched["total_aal"])
        aal_share = float(matched["aal_share_pct"])
        tail = float(matched["total_tail_contribution"])
        tail_share = float(matched["tail_share_pct"])

        summary = (
            f"Region '{region}' holds ${tiv:,.2f} in Total Insured Value ({tiv_share:.1f}% of portfolio TIV), "
            f"generating ${aal:,.2f} AAL ({aal_share:.1f}% share) and ${tail:,.2f} TVaR contribution ({tail_share:.1f}% tail share)."
        )

        drivers = []
        if tail_share > tiv_share:
            drivers.append(f"Tail risk share ({tail_share:.1f}%) exceeds TIV share ({tiv_share:.1f}%), indicating hazard vulnerability concentration.")
        else:
            drivers.append(f"Tail risk share ({tail_share:.1f}%) is aligned with or below TIV share ({tiv_share:.1f}%).")

        return AccumulationExplanation(
            region=region,
            summary_text=summary,
            total_tiv=round(tiv, 2),
            tiv_share_pct=round(tiv_share, 2),
            total_aal=round(aal, 2),
            aal_share_pct=round(aal_share, 2),
            tail_contribution=round(tail, 2),
            tail_share_pct=round(tail_share, 2),
            co_hit_density="HIGH" if tail_share > 30.0 else "MODERATE",
            drivers=drivers,
        )

    @staticmethod
    def explain_recommendation(policy_id: str, evidence: DecisionEvidencePackage) -> RecommendationExplanation:
        """Explain the rationale and governance checks behind an underwriting recommendation."""
        if evidence.policy_id != policy_id:
            raise ValidationError(f"Evidence package is for policy '{evidence.policy_id}', not '{policy_id}'.")

        rec = evidence.recommendation
        conf = evidence.confidence
        m = evidence.key_metrics

        summary = (
            f"Policy {policy_id} is recommended for {rec} with {conf.level} decision confidence "
            f"(Confidence Score: {conf.score:.2f}, Quadrant: {conf.quadrant}). "
            f"Primary reasons: {', '.join(evidence.reasons) if evidence.reasons else 'Standard appetite criteria met'}."
        )

        guidance = {
            "ACCEPT": "Policy meets standard risk appetite and pricing criteria. Proceed with standard acceptance.",
            "REVIEW": "Policy exhibits elevated tail contribution or co-hit rate. Review local flood mitigation and deductible terms.",
            "ESCALATE": "Policy exceeds risk appetite thresholds (extreme tail or concentration impact). Senior underwriter sign-off required.",
        }.get(rec, "Review underwriter guidelines.")

        return RecommendationExplanation(
            policy_id=policy_id,
            recommendation=rec,
            confidence_level=conf.level,
            confidence_quadrant=conf.quadrant,
            summary_text=summary,
            primary_reasons=evidence.reasons,
            risk_appetite_flags=evidence.risk_appetite_summary.get("flags", []),
            model_warnings=evidence.warnings,
            action_guidance=guidance,
        )

    @staticmethod
    def generate_mathematical_trace(policy_id: str, evidence: DecisionEvidencePackage) -> MathematicalTrace:
        """Generate a complete mathematical derivation trace from physical exposure to price."""
        if evidence.policy_id != policy_id:
            raise ValidationError(f"Evidence package is for policy '{evidence.policy_id}', not '{policy_id}'.")

        m = evidence.key_metrics
        tiv = m.get("insured_value", 0.0)
        aal = m.get("aal", 0.0)
        tail_contrib = m.get("tail_contribution", 0.0)
        marginal_tvar = m.get("marginal_tvar", 0.0)
        tail_charge = m.get("tail_risk_charge", 0.0)
        expense = m.get("expense_charge", 0.0)
        premium = m.get("technical_premium", 0.0)

        steps = [
            MathematicalTraceStep(
                step_number=1,
                step_name="Physical Exposure Value",
                formula="TIV_i = Policy Insured Value",
                inputs={"policy_id": policy_id},
                output_name="Total Insured Value (TIV)",
                output_value=f"${tiv:,.2f}",
                interpretation="Baseline asset valuation subject to catastrophe flood hazard.",
            ),
            MathematicalTraceStep(
                step_number=2,
                step_name="Expected Annual Loss (AAL)",
                formula="AAL_i = (1/N) * sum_y(Loss_i,y)",
                inputs={"simulation_years": evidence.loss_summary.get("simulation_years", 1000)},
                output_name="Policy AAL",
                output_value=f"${aal:,.2f}",
                interpretation="Mean annual ground-up and net flood loss across simulated stochastic event set.",
            ),
            MathematicalTraceStep(
                step_number=3,
                step_name="Tail Risk Contribution (TVaR Allocation)",
                formula="TailContribution_i = sum_(y in Tail)(w_y * Loss_i,y)",
                inputs={"confidence_level": 0.996, "tail_years": evidence.tail_summary.get("tail_year_count", 4)},
                output_name="Tail Contribution",
                output_value=f"${tail_contrib:,.2f}",
                interpretation="Policy's exact weighted loss during the portfolio's top 1-in-250 year tail events.",
            ),
            MathematicalTraceStep(
                step_number=4,
                step_name="Marginal TVaR Impact (CRN)",
                formula="MarginalTVaR_i = TVaR(Portfolio) - TVaR(Portfolio \\ {i})",
                inputs={"method": "Common Random Numbers (CRN)"},
                output_name="Marginal TVaR",
                output_value=f"${marginal_tvar:,.2f}",
                interpretation="Independent systemic capital relief achieved if this policy is removed from portfolio.",
            ),
            MathematicalTraceStep(
                step_number=5,
                step_name="Tail Risk Capital Charge",
                formula="TailCharge_i = r * max(0, TailContribution_i - AAL_i)",
                inputs={"cost_of_capital_rate (r)": 0.10},
                output_name="Tail Risk Charge",
                output_value=f"${tail_charge:,.2f}",
                interpretation="Capital charge applied to cover the excess extreme tail volatility.",
            ),
            MathematicalTraceStep(
                step_number=6,
                step_name="Expense Allowance Loading",
                formula="Expense_i = e * (AAL_i + TailCharge_i)",
                inputs={"expense_rate (e)": 0.10},
                output_name="Expense Loading",
                output_value=f"${expense:,.2f}",
                interpretation="Administrative and underwriting operating expense allowance.",
            ),
            MathematicalTraceStep(
                step_number=7,
                step_name="Technical Reinsurance Premium",
                formula="Premium_i = AAL_i + TailCharge_i + Expense_i",
                inputs={"aal": aal, "tail_charge": tail_charge, "expense": expense},
                output_name="Technical Premium",
                output_value=f"${premium:,.2f}",
                interpretation="Actuarially reconciled technical price required to cover expected loss and capital risk.",
            ),
        ]

        return MathematicalTrace(
            policy_id=policy_id,
            steps=steps,
            final_premium=round(premium, 2),
        )
