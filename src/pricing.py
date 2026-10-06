"""FLOODTAIL — Technical Reinsurance Pricing and Capital Loading Engine.

Implements the portfolio-aware technical pricing formula:
    Technical Premium = Expected Loss (AAL) + Tail Risk Charge (Cost of Capital on Tail) + Expense Loading.
Produces policy-level pricing waterfalls, Rate-on-Line (ROL) metrics, and validates pricing reconciliation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd

from src.exceptions import ModelCalculationError, ReconciliationError
from src.logging_config import get_logger
from src.schemas import PricingResult

logger = get_logger("pricing")


@dataclass
class PolicyPriceBreakdown:
    """Detailed pricing waterfall breakdown for a single policy."""

    policy_id: str
    insured_value: float
    expected_loss: float  # AAL
    tail_contribution: float
    net_tail_exposure: float  # max(0, tail_contribution - expected_loss)
    tail_charge: float  # r * net_tail_exposure
    expense: float  # e * (expected_loss + tail_charge)
    technical_premium: float  # expected_loss + tail_charge + expense
    rate_on_line_bps: float  # (premium / TIV) * 10,000


@dataclass
class PortfolioPricingResult:
    """Portfolio-wide technical pricing output and reconciliation summary."""

    run_id: str
    policy_count: int
    portfolio_aal: float
    portfolio_tvar: float
    cost_of_capital_rate: float
    expense_rate: float
    total_expected_loss: float
    total_tail_charge: float
    total_expense: float
    total_technical_premium: float
    pricing_reconciled: bool
    policy_pricing: list[PolicyPriceBreakdown]
    pricing_dataframe: pd.DataFrame
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TechnicalPricingEngine:
    """Calculates actuarial technical premium incorporating tail risk capital loading."""

    def __init__(
        self,
        cost_of_capital_rate: float = 0.10,
        expense_rate: float = 0.10,
        tolerance: float = 1e-3,
    ) -> None:
        self.cost_of_capital_rate = cost_of_capital_rate
        self.expense_rate = expense_rate
        self.tolerance = tolerance

    def calculate_pricing(
        self,
        tail_df: pd.DataFrame,
        run_id: str = "PRICING_RUN",
        cost_of_capital_override: Optional[float] = None,
        expense_rate_override: Optional[float] = None,
    ) -> PortfolioPricingResult:
        """Compute technical pricing waterfalls for all policies in the portfolio."""
        r = cost_of_capital_override if cost_of_capital_override is not None else self.cost_of_capital_rate
        e = expense_rate_override if expense_rate_override is not None else self.expense_rate

        logger.info(
            "Calculating technical pricing for %d policies (CoC=%.1f%%, Expense=%.1f%%)...",
            len(tail_df),
            r * 100.0,
            e * 100.0,
        )

        records: list[PolicyPriceBreakdown] = []
        tot_exp_loss = 0.0
        tot_tail_charge = 0.0
        tot_expense = 0.0
        tot_premium = 0.0

        for _, row in tail_df.iterrows():
            pid = str(row["policy_id"])
            tiv = float(row.get("insured_value", 0.0))
            aal = float(row.get("aal", 0.0))
            t_contrib = float(row.get("tail_contribution", 0.0))

            # 1. Expected Loss = AAL
            exp_loss = round(aal, 2)

            # 2. Net Tail Exposure = max(0, TailContribution - AAL)
            net_tail = max(0.0, t_contrib - aal)

            # 3. Tail Risk Charge = r * net_tail
            tail_charge = round(r * net_tail, 2)

            # 4. Expense = e * (ExpectedLoss + TailCharge)
            expense = round(e * (exp_loss + tail_charge), 2)

            # 5. Technical Premium = ExpectedLoss + TailCharge + Expense
            premium = round(exp_loss + tail_charge + expense, 2)

            # Rate on line in basis points (1 bp = 0.01%)
            rol_bps = round((premium / max(tiv, 1e-9)) * 10000.0, 2)

            # Individual reconciliation check: exp_loss + tail_charge + expense == premium
            diff = abs((exp_loss + tail_charge + expense) - premium)
            if diff > self.tolerance:
                raise ReconciliationError(
                    f"Pricing reconciliation failed for policy {pid}: {exp_loss} + {tail_charge} + {expense} = {exp_loss + tail_charge + expense} != {premium}"
                )

            # Check schemas contract compliance
            PricingResult(
                policy_id=pid,
                expected_loss=exp_loss,
                tail_charge=tail_charge,
                expense=expense,
                technical_premium=premium,
            )

            records.append(
                PolicyPriceBreakdown(
                    policy_id=pid,
                    insured_value=tiv,
                    expected_loss=exp_loss,
                    tail_contribution=round(t_contrib, 2),
                    net_tail_exposure=round(net_tail, 2),
                    tail_charge=tail_charge,
                    expense=expense,
                    technical_premium=premium,
                    rate_on_line_bps=rol_bps,
                )
            )

            tot_exp_loss += exp_loss
            tot_tail_charge += tail_charge
            tot_expense += expense
            tot_premium += premium

        # Portfolio totals
        port_aal = float(tail_df["aal"].sum()) if not tail_df.empty else 0.0
        port_tvar = float(tail_df["tail_contribution"].sum()) if not tail_df.empty else 0.0

        pricing_df = pd.DataFrame([
            {
                "policy_id": p.policy_id,
                "insured_value": p.insured_value,
                "expected_loss": p.expected_loss,
                "tail_contribution": p.tail_contribution,
                "net_tail_exposure": p.net_tail_exposure,
                "tail_charge": p.tail_charge,
                "expense": p.expense,
                "technical_premium": p.technical_premium,
                "rate_on_line_bps": p.rate_on_line_bps,
            }
            for p in records
        ])

        reconciled = abs((tot_exp_loss + tot_tail_charge + tot_expense) - tot_premium) <= self.tolerance

        logger.info(
            "Pricing Calculation PASSED: Total Technical Premium = $%s (Expected Loss = $%s, Tail Charge = $%s, Expense = $%s)",
            f"{tot_premium:,.2f}",
            f"{tot_exp_loss:,.2f}",
            f"{tot_tail_charge:,.2f}",
            f"{tot_expense:,.2f}",
        )

        return PortfolioPricingResult(
            run_id=run_id,
            policy_count=len(records),
            portfolio_aal=round(port_aal, 2),
            portfolio_tvar=round(port_tvar, 2),
            cost_of_capital_rate=r,
            expense_rate=e,
            total_expected_loss=round(tot_exp_loss, 2),
            total_tail_charge=round(tot_tail_charge, 2),
            total_expense=round(tot_expense, 2),
            total_technical_premium=round(tot_premium, 2),
            pricing_reconciled=reconciled,
            policy_pricing=records,
            pricing_dataframe=pricing_df,
        )
