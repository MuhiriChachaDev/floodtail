"""FLOODTAIL — Counterfactual Analysis, Marginal TVaR & Risk Appetite Rule Engine.

Evaluates marginal risk impact using Common Random Numbers (CRN), conducts what-if
sensitivity experiments, and executes deterministic risk-appetite rule governance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Optional

import numpy as np
import pandas as pd

from src.logging_config import get_logger
from src.risk_metrics import RiskMetricsEngine

logger = get_logger("counterfactual")

RecommendationAction = Literal["ACCEPT", "REVIEW", "ESCALATE"]


@dataclass
class MarginalRiskImpact:
    """Marginal impact of a policy on portfolio tail risk."""

    policy_id: str
    portfolio_tvar_base: float
    portfolio_tvar_without: float
    marginal_tvar_impact: float  # base - without
    tail_contribution: float  # Allocated TVaR share
    aal: float


@dataclass
class WhatIfSensitivityResult:
    """What-if sensitivity outcome for a modified policy parameter."""

    policy_id: str
    parameter_changed: str
    baseline_value: float
    modified_value: float
    baseline_aal: float
    new_aal: float
    aal_delta_pct: float
    baseline_tail_contribution: float
    new_tail_contribution: float
    tail_delta_pct: float
    baseline_marginal_tvar: float
    new_marginal_tvar: float


@dataclass
class RiskRecommendation:
    """Standardized decision support envelope for underwriting governance."""

    policy_id: str
    recommendation: RecommendationAction
    risk_appetite_status: str  # 'WITHIN_APPETITE', 'REVIEW_REQUIRED', 'APPETITE_BREACH'
    aal: float
    tail_contribution: float
    marginal_tvar: float
    tail_share_pct: float
    co_hit_rate: float
    risk_flags: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)


@dataclass
class RiskAppetiteConfig:
    """Configurable governance and underwriting risk thresholds."""

    max_portfolio_tvar: float = 500_000_000.0
    max_pml_250: float = 400_000_000.0
    max_regional_concentration_pct: float = 45.0
    max_policy_marginal_tvar: float = 15_000_000.0
    max_policy_tail_share_pct: float = 12.0
    high_co_hit_rate_threshold: float = 0.60


class CounterfactualEngine:
    """Calculates non-additive marginal TVaR impacts and executes what-if analyses."""

    def __init__(self, alpha: float = 0.996) -> None:
        self.alpha = alpha

    def calculate_marginal_tvars(
        self,
        ylt_df: pd.DataFrame,
        pal_matrix: pd.DataFrame,
        tail_df: pd.DataFrame,
    ) -> list[MarginalRiskImpact]:
        """Compute Marginal TVaR impact for all policies using Common Random Numbers.

        Marginal TVaR_k = TVaR(Portfolio) - TVaR(Portfolio without policy k)
        """
        base_annual_losses = ylt_df["annual_loss"].astype(float).values
        base_tvar = RiskMetricsEngine.calculate_tvar(ylt_df, alpha=self.alpha)
        n_years = len(base_annual_losses)

        tail_dict = tail_df.set_index("policy_id").to_dict(orient="index")
        marginal_results: list[MarginalRiskImpact] = []

        logger.info("Computing marginal TVaR impacts for %d policies (CRN)...", len(pal_matrix))

        for pid, p_losses in pal_matrix.iterrows():
            p_loss_arr = p_losses.values
            # Counterfactual annual loss without policy k
            without_annual_losses = np.maximum(0.0, base_annual_losses - p_loss_arr)

            without_ylt = pd.DataFrame({
                "simulation_year": range(1, n_years + 1),
                "annual_loss": without_annual_losses,
            })
            without_tvar = RiskMetricsEngine.calculate_tvar(without_ylt, alpha=self.alpha)
            marginal_impact = max(0.0, base_tvar - without_tvar)

            t_info = tail_dict.get(str(pid), {})
            marginal_results.append(
                MarginalRiskImpact(
                    policy_id=str(pid),
                    portfolio_tvar_base=round(base_tvar, 2),
                    portfolio_tvar_without=round(without_tvar, 2),
                    marginal_tvar_impact=round(marginal_impact, 2),
                    tail_contribution=float(t_info.get("tail_contribution", 0.0)),
                    aal=float(t_info.get("aal", 0.0)),
                )
            )

        return marginal_results

    def evaluate_what_if_tiv(
        self,
        policy_id: str,
        new_tiv: float,
        portfolio_df: pd.DataFrame,
        ylt_df: pd.DataFrame,
        pal_matrix: pd.DataFrame,
        tail_df: pd.DataFrame,
    ) -> WhatIfSensitivityResult:
        """Evaluate sensitivity of portfolio metrics when a policy's TIV is adjusted."""
        port_meta = portfolio_df.set_index("policy_id")
        orig_tiv = float(port_meta.loc[policy_id, "insured_value"]) if policy_id in port_meta.index else 1.0
        scale = new_tiv / max(1e-9, orig_tiv)

        tail_meta = tail_df.set_index("policy_id")
        orig_aal = float(tail_meta.loc[policy_id, "aal"]) if policy_id in tail_meta.index else 0.0
        orig_tail = float(tail_meta.loc[policy_id, "tail_contribution"]) if policy_id in tail_meta.index else 0.0

        # Scaled losses for policy
        p_losses = pal_matrix.loc[policy_id].values if policy_id in pal_matrix.index else np.zeros(len(ylt_df))
        delta_p_losses = p_losses * (scale - 1.0)

        # Counterfactual annual losses
        base_ann = ylt_df["annual_loss"].astype(float).values
        new_ann = np.maximum(0.0, base_ann + delta_p_losses)

        new_ylt = pd.DataFrame({"simulation_year": range(1, len(base_ann) + 1), "annual_loss": new_ann})
        new_port_tvar = RiskMetricsEngine.calculate_tvar(new_ylt, alpha=self.alpha)
        base_port_tvar = RiskMetricsEngine.calculate_tvar(ylt_df, alpha=self.alpha)

        new_aal = orig_aal * scale
        new_tail = orig_tail * scale
        marginal_delta = max(0.0, new_port_tvar - (base_port_tvar - orig_tail))

        return WhatIfSensitivityResult(
            policy_id=policy_id,
            parameter_changed="insured_value",
            baseline_value=orig_tiv,
            modified_value=new_tiv,
            baseline_aal=round(orig_aal, 2),
            new_aal=round(new_aal, 2),
            aal_delta_pct=round(((new_aal - orig_aal) / max(orig_aal, 1e-9)) * 100.0, 2),
            baseline_tail_contribution=round(orig_tail, 2),
            new_tail_contribution=round(new_tail, 2),
            tail_delta_pct=round(((new_tail - orig_tail) / max(orig_tail, 1e-9)) * 100.0, 2),
            baseline_marginal_tvar=round(orig_tail, 2),
            new_marginal_tvar=round(marginal_delta, 2),
        )


class RiskAppetiteRuleEngine:
    """Evaluates portfolio and policy risk metrics against underwriting appetite limits."""

    def __init__(self, appetite_config: Optional[RiskAppetiteConfig] = None) -> None:
        self.appetite = appetite_config or RiskAppetiteConfig()

    def evaluate_policy_recommendations(
        self,
        tail_records: list[Any],
        marginal_impacts: list[MarginalRiskImpact],
        co_hit_metrics: list[Any],
    ) -> list[RiskRecommendation]:
        """Generate deterministic decision recommendations for all policies."""
        marginal_dict = {m.policy_id: m.marginal_tvar_impact for m in marginal_impacts}
        co_hit_dict = {c.policy_id: c for c in co_hit_metrics}

        recommendations: list[RiskRecommendation] = []

        for r in tail_records:
            pid = r.policy_id
            aal = r.aal
            t_contrib = r.tail_contribution
            t_share = r.tail_share_pct
            m_tvar = marginal_dict.get(pid, t_contrib)

            co_m = co_hit_dict.get(pid)
            co_rate = co_m.co_hit_rate if co_m else 0.0

            flags: list[str] = []
            reasons: list[str] = []

            # Rule 1: High Marginal TVaR impact
            if m_tvar > self.appetite.max_policy_marginal_tvar:
                flags.append("ELEVATED_MARGINAL_TAIL_RISK")
                reasons.append(
                    f"Policy marginal TVaR (${m_tvar:,.2f}) exceeds threshold (${self.appetite.max_policy_marginal_tvar:,.2f})."
                )

            # Rule 2: High Tail Share
            if t_share > self.appetite.max_policy_tail_share_pct:
                flags.append("HIGH_PORTFOLIO_TAIL_SHARE")
                reasons.append(f"Policy accounts for {t_share:.1f}% of total portfolio TVaR.")

            # Rule 3: Elevated Co-Hit Correlation
            if co_rate > self.appetite.high_co_hit_rate_threshold:
                flags.append("HIGH_SPATIAL_CO_HIT_ACCUMULATION")
                reasons.append(f"Policy experiences concurrent multi-exposure flooding in {co_rate*100:.1f}% of hits.")

            # Determine Governance Action
            if len(flags) >= 2 or ("ELEVATED_MARGINAL_TAIL_RISK" in flags and t_share > 15.0):
                action = "ESCALATE"
                status = "APPETITE_BREACH"
            elif len(flags) == 1:
                action = "REVIEW"
                status = "REVIEW_REQUIRED"
            else:
                action = "ACCEPT"
                status = "WITHIN_APPETITE"
                reasons.append("Exposure within standard risk-appetite tolerance.")

            recommendations.append(
                RiskRecommendation(
                    policy_id=pid,
                    recommendation=action,
                    risk_appetite_status=status,
                    aal=aal,
                    tail_contribution=t_contrib,
                    marginal_tvar=m_tvar,
                    tail_share_pct=t_share,
                    co_hit_rate=co_rate,
                    risk_flags=flags,
                    reason_codes=reasons,
                )
            )

        return recommendations
