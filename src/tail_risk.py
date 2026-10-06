"""FLOODTAIL — Policy Tail Contribution, TVaR Allocation, and Simulation Stability Engine.

Aggregates ELT into policy annual losses, computes policy-level AAL and tail contributions,
guarantees mathematical reconciliation (sum of contributions == Portfolio TVaR),
and provides bootstrap simulation-stability analytics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd

from src.exceptions import ModelCalculationError, ReconciliationError
from src.logging_config import get_logger
from src.risk_metrics import RiskMetricsEngine, TailSetDetails

logger = get_logger("tail_risk")


@dataclass
class PolicyTailContributionRecord:
    """Individual policy tail risk allocation record."""

    policy_id: str
    aal: float
    tail_contribution: float
    tail_share_pct: float
    tail_rank: int
    insured_value: float
    property_type: str
    region: Optional[str] = None
    bootstrap_median: Optional[float] = None
    bootstrap_p05: Optional[float] = None
    bootstrap_p95: Optional[float] = None


@dataclass
class TailRiskAllocationResult:
    """Complete portfolio tail risk allocation output and reconciliation report."""

    portfolio_aal: float
    portfolio_tvar: float
    total_allocated_aal: float
    total_allocated_tail: float
    aal_reconciled: bool
    tail_reconciled: bool
    policy_records: list[PolicyTailContributionRecord]
    top_10_contributors: list[PolicyTailContributionRecord]
    policy_annual_losses_df: pd.DataFrame
    tail_dataframe: pd.DataFrame
    reconciliation_error: float
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PolicyTailRiskEngine:
    """Computes exact policy annual losses and allocates portfolio TVaR."""

    def __init__(self, tolerance: float = 1e-3) -> None:
        self.tolerance = tolerance

    @staticmethod
    def build_policy_annual_loss_matrix(
        elt_df: pd.DataFrame,
        all_policy_ids: list[str],
        simulation_years: int,
    ) -> pd.DataFrame:
        """Construct a dense (policies × years) annual loss matrix from sparse ELT.

        Rows = policy_id
        Columns = simulation_year (1..N)
        Values = annual loss sum
        """
        if elt_df.empty:
            return pd.DataFrame(0.0, index=all_policy_ids, columns=range(1, simulation_years + 1))

        # Groupby policy_id and simulation_year
        grouped = elt_df.groupby(["policy_id", "simulation_year"])["loss"].sum().unstack(level="simulation_year", fill_value=0.0)

        # Reindex to ensure all policies and all years 1..N are present
        reindexed = grouped.reindex(index=all_policy_ids, columns=range(1, simulation_years + 1), fill_value=0.0)
        return reindexed

    def allocate_tail_risk(
        self,
        elt_df: pd.DataFrame,
        ylt_df: pd.DataFrame,
        portfolio_df: pd.DataFrame,
        tail_set: TailSetDetails,
        portfolio_tvar: float,
        portfolio_aal: float,
        run_bootstrap: bool = False,
        bootstrap_iterations: int = 50,
        bootstrap_seed: int = 42,
    ) -> TailRiskAllocationResult:
        """Perform exact TVaR allocation across all policies using the same tail-year weights.

        TailContribution_i = sum_{y in Tail} (weight_y * Loss_{i,y})
        """
        all_pids = portfolio_df["policy_id"].astype(str).tolist()
        n_years = tail_set.total_years

        logger.info(
            "Allocating tail risk across %d policies over %d tail years (TVaR = $%s)",
            len(all_pids),
            tail_set.tail_year_count,
            f"{portfolio_tvar:,.2f}",
        )

        # 1. Build Policy Annual Loss Table (Policies × Years)
        pal_matrix = self.build_policy_annual_loss_matrix(elt_df, all_pids, n_years)

        # 2. Policy-Level AAL
        policy_aals = pal_matrix.mean(axis=1).values

        # 3. Policy-Level Tail Contribution (Exact Weighted Average over Tail Years)
        tail_years = tail_set.tail_years
        tail_weights = np.array(tail_set.tail_weights, dtype=float)

        # Extract columns for tail years (1-indexed year columns)
        tail_loss_matrix = pal_matrix[tail_years].values  # Shape: (n_policies, n_tail_years)

        # Matrix multiply with tail weights: (n_policies, n_tail_years) @ (n_tail_years,) -> (n_policies,)
        policy_tail_contribs = tail_loss_matrix @ tail_weights

        # 4. Reconciliation Checks
        total_alloc_aal = float(policy_aals.sum())
        total_alloc_tail = float(policy_tail_contribs.sum())

        diff_aal = abs(total_alloc_aal - portfolio_aal)
        diff_tail = abs(total_alloc_tail - portfolio_tvar)

        aal_reconciled = diff_aal <= max(self.tolerance, portfolio_aal * 1e-4)
        tail_reconciled = diff_tail <= max(self.tolerance, portfolio_tvar * 1e-4)

        if not (aal_reconciled and tail_reconciled):
            logger.error(
                "Tail Risk Reconciliation MISMATCH: Alloc AAL = %.2f (Port AAL = %.2f, diff=%.4f), "
                "Alloc TVaR = %.2f (Port TVaR = %.2f, diff=%.4f)",
                total_alloc_aal, portfolio_aal, diff_aal,
                total_alloc_tail, portfolio_tvar, diff_tail,
            )
            raise ReconciliationError(
                f"Tail risk allocation failed reconciliation: Sum(Policy Tail Contributions) = {total_alloc_tail:.2f} != Portfolio TVaR = {portfolio_tvar:.2f}"
            )

        # 5. Optional Bootstrap Stability Analysis
        bootstrap_stats: dict[str, dict[str, float]] = {}
        if run_bootstrap and n_years >= 100:
            logger.info("Running bootstrap stability analysis (%d iterations)...", bootstrap_iterations)
            rng = np.random.default_rng(bootstrap_seed)
            bs_contribs = np.zeros((len(all_pids), bootstrap_iterations), dtype=float)
            all_years_arr = np.arange(1, n_years + 1)

            for b in range(bootstrap_iterations):
                sample_years = rng.choice(all_years_arr, size=n_years, replace=True)
                # Compute sample annual losses
                sample_pal = pal_matrix[sample_years]
                sample_ann_losses = sample_pal.sum(axis=0).values

                # Sort top (1 - alpha)*N years
                k_tail = max(1, int(math.ceil((1.0 - tail_set.confidence_level) * n_years)))
                top_indices = np.argsort(sample_ann_losses)[-k_tail:]
                sample_tail_matrix = sample_pal.iloc[:, top_indices].values
                bs_contribs[:, b] = sample_tail_matrix.mean(axis=1)

            for i, pid in enumerate(all_pids):
                arr = bs_contribs[i, :]
                bootstrap_stats[pid] = {
                    "median": float(np.median(arr)),
                    "p05": float(np.percentile(arr, 5)),
                    "p95": float(np.percentile(arr, 95)),
                }

        # 6. Assemble Policy Contribution Records
        port_meta = portfolio_df.set_index("policy_id")
        records: list[PolicyTailContributionRecord] = []

        # Sort indices by tail contribution descending
        sorted_indices = np.argsort(-policy_tail_contribs)

        for rank, idx in enumerate(sorted_indices, 1):
            pid = all_pids[idx]
            c_val = float(policy_tail_contribs[idx])
            aal_val = float(policy_aals[idx])
            share_pct = (c_val / max(portfolio_tvar, 1e-9)) * 100.0

            meta_row = port_meta.loc[pid] if pid in port_meta.index else {}
            tiv = float(meta_row.get("insured_value", 0.0)) if isinstance(meta_row, pd.Series) else float(meta_row.iloc[0].get("insured_value", 0.0)) if hasattr(meta_row, "iloc") else 0.0
            ptype = str(meta_row.get("property_type", "Unknown")) if isinstance(meta_row, pd.Series) else str(meta_row.iloc[0].get("property_type", "Unknown")) if hasattr(meta_row, "iloc") else "Unknown"
            reg = str(meta_row.get("region", "")) if isinstance(meta_row, pd.Series) else str(meta_row.iloc[0].get("region", "")) if hasattr(meta_row, "iloc") else ""

            bs = bootstrap_stats.get(pid, {})
            records.append(
                PolicyTailContributionRecord(
                    policy_id=pid,
                    aal=round(aal_val, 2),
                    tail_contribution=round(c_val, 2),
                    tail_share_pct=round(share_pct, 4),
                    tail_rank=rank,
                    insured_value=tiv,
                    property_type=ptype,
                    region=reg,
                    bootstrap_median=round(bs["median"], 2) if "median" in bs else None,
                    bootstrap_p05=round(bs["p05"], 2) if "p05" in bs else None,
                    bootstrap_p95=round(bs["p95"], 2) if "p95" in bs else None,
                )
            )

        top_10 = records[:10]

        tail_df = pd.DataFrame([
            {
                "policy_id": r.policy_id,
                "aal": r.aal,
                "tail_contribution": r.tail_contribution,
                "tail_share_pct": r.tail_share_pct,
                "tail_rank": r.tail_rank,
                "insured_value": r.insured_value,
                "property_type": r.property_type,
                "region": r.region,
                "bootstrap_median": r.bootstrap_median,
                "bootstrap_p05": r.bootstrap_p05,
                "bootstrap_p95": r.bootstrap_p95,
            }
            for r in records
        ])

        logger.info(
            "Tail Risk Allocation PASSED: %d policies allocated. Top 1 contributor: %s ($%s, %.2f%%)",
            len(records),
            top_10[0].policy_id if top_10 else "None",
            f"{top_10[0].tail_contribution:,.2f}" if top_10 else "0",
            top_10[0].tail_share_pct if top_10 else 0.0,
        )

        return TailRiskAllocationResult(
            portfolio_aal=round(portfolio_aal, 2),
            portfolio_tvar=round(portfolio_tvar, 2),
            total_allocated_aal=round(total_alloc_aal, 2),
            total_allocated_tail=round(total_alloc_tail, 2),
            aal_reconciled=aal_reconciled,
            tail_reconciled=tail_reconciled,
            policy_records=records,
            top_10_contributors=top_10,
            policy_annual_losses_df=pal_matrix,
            tail_dataframe=tail_df,
            reconciliation_error=round(diff_tail, 6),
        )
