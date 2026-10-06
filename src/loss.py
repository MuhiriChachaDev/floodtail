"""FLOODTAIL — Financial Catastrophe Loss Calculation, ELT, YLT, and Reconciliation Engine.

Calculates ground-up and net financial losses from exposure-damage ratios,
constructs the Event Loss Table (ELT) and Year Loss Table (YLT),
and performs rigorous mathematical reconciliation across policy, event, and annual totals.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd

from src.exceptions import LossCalculationError, ReconciliationError
from src.logging_config import get_logger
from src.schemas import AnnualLossResult, LossResult

logger = get_logger("loss")


@dataclass
class ReconciliationReport:
    """Audit report verifying mathematical equivalence between loss aggregation levels."""

    passed: bool
    elt_total_loss: float
    ylt_total_loss: float
    absolute_difference: float
    relative_difference: float
    tolerance: float
    total_elt_rows: int
    total_simulation_years: int
    years_with_events: int
    years_with_losses: int
    events_reconciled: bool
    annual_losses_reconciled: bool
    negative_losses_count: int
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CatastropheLossEngine:
    """Computes financial losses, applies policy terms, builds ELT/YLT, and reconciles totals."""

    def __init__(self, reconciliation_tolerance: float = 1e-4) -> None:
        self.tolerance = reconciliation_tolerance

    def calculate_losses(
        self,
        vulnerability_df: pd.DataFrame,
        simulation_years: int = 10000,
        default_deductible: float = 0.0,
        default_limit: Optional[float] = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame, ReconciliationReport]:
        """Compute ELT and YLT from vulnerability results and reconcile.

        Args:
            vulnerability_df: Output from VulnerabilityEngine with [simulation_year, occurrence_id, event_id, policy_id, depth_m, damage_ratio, insured_value]
            simulation_years: Total simulation years in the Monte Carlo run.
            default_deductible: Default deductible if not specified per policy.
            default_limit: Default limit if not specified per policy.

        Returns:
            Tuple of (elt_df, ylt_df, reconciliation_report)
        """
        logger.info(
            "Building Event Loss Table (ELT) from %d impacted exposure records across %d simulation years",
            len(vulnerability_df),
            simulation_years,
        )

        # 1. Build Event Loss Table (ELT)
        if vulnerability_df.empty:
            elt_df = pd.DataFrame(columns=[
                "simulation_year", "occurrence_id", "event_id", "policy_id",
                "depth_m", "damage_ratio", "insured_value", "ground_up_loss",
                "deductible", "policy_limit", "loss"
            ])
        else:
            elt_df = vulnerability_df.copy()
            elt_df["insured_value"] = elt_df["insured_value"].astype(float)
            elt_df["damage_ratio"] = elt_df["damage_ratio"].astype(float)

            # Ground-up loss = TIV * damage_ratio
            elt_df["ground_up_loss"] = (elt_df["insured_value"] * elt_df["damage_ratio"]).round(2)

            # Policy terms
            if "deductible" not in elt_df.columns:
                elt_df["deductible"] = default_deductible
            else:
                elt_df["deductible"] = elt_df["deductible"].fillna(default_deductible).astype(float)

            if "policy_limit" not in elt_df.columns:
                elt_df["policy_limit"] = default_limit if default_limit is not None else elt_df["insured_value"]
            else:
                elt_df["policy_limit"] = elt_df["policy_limit"].fillna(elt_df["insured_value"]).astype(float)

            # Net loss = min(max(ground_up - deductible, 0), limit)
            net_loss = np.maximum(elt_df["ground_up_loss"].values - elt_df["deductible"].values, 0.0)
            net_loss = np.minimum(net_loss, elt_df["policy_limit"].values)
            elt_df["loss"] = np.round(net_loss, 2)

            # Strict non-negativity check
            if (elt_df["loss"] < 0).any():
                neg_count = int((elt_df["loss"] < 0).sum())
                raise LossCalculationError(f"Detected {neg_count} negative losses in ELT.")

        # 2. Build Year Loss Table (YLT)
        ylt_rows: list[dict[str, Any]] = []

        if not elt_df.empty:
            # Group by simulation_year and occurrence_id to compute event-level losses first
            event_losses = elt_df.groupby(["simulation_year", "occurrence_id", "event_id"])["loss"].sum().reset_index()
            event_losses.rename(columns={"loss": "event_loss"}, inplace=True)

            # Group by simulation_year for annual totals
            year_grouped = event_losses.groupby("simulation_year").agg(
                annual_loss=("event_loss", "sum"),
                max_event_loss=("event_loss", "max"),
                event_count=("event_loss", "count"),
                event_ids=("event_id", lambda s: list(s.unique())),
            ).reset_index()

            year_dict = {int(row["simulation_year"]): row.to_dict() for _, row in year_grouped.iterrows()}
        else:
            year_dict = {}

        # Fill all simulation years 1..N (including zero-loss years)
        for y in range(1, simulation_years + 1):
            if y in year_dict:
                r = year_dict[y]
                ylt_rows.append({
                    "simulation_year": y,
                    "annual_loss": round(float(r["annual_loss"]), 2),
                    "max_event_loss": round(float(r["max_event_loss"]), 2),
                    "event_count": int(r["event_count"]),
                    "event_ids": r.get("event_ids", []),
                })
            else:
                ylt_rows.append({
                    "simulation_year": y,
                    "annual_loss": 0.0,
                    "max_event_loss": 0.0,
                    "event_count": 0,
                    "event_ids": [],
                })

        ylt_df = pd.DataFrame(ylt_rows)

        # 3. Perform Complete Reconciliation
        report = self.reconcile(elt_df, ylt_df, simulation_years)

        if not report.passed:
            raise ReconciliationError(
                f"Catastrophe Loss Reconciliation FAILED! "
                f"ELT Total = {report.elt_total_loss:,.2f}, YLT Total = {report.ylt_total_loss:,.2f}, "
                f"Diff = {report.absolute_difference:,.4f} (tolerance = {report.tolerance})"
            )

        logger.info(
            "Reconciliation PASSED: Total ELT Loss = $%s == Total YLT Loss = $%s across %d years",
            f"{report.elt_total_loss:,.2f}",
            f"{report.ylt_total_loss:,.2f}",
            simulation_years,
        )

        return elt_df, ylt_df, report

    def reconcile(
        self,
        elt_df: pd.DataFrame,
        ylt_df: pd.DataFrame,
        simulation_years: int,
    ) -> ReconciliationReport:
        """Perform comprehensive multi-tier loss reconciliation."""
        elt_total = float(elt_df["loss"].sum()) if not elt_df.empty else 0.0
        ylt_total = float(ylt_df["annual_loss"].sum()) if not ylt_df.empty else 0.0

        diff = abs(elt_total - ylt_total)
        rel_diff = diff / max(elt_total, 1.0)
        total_reconciled = diff <= max(self.tolerance, elt_total * 1e-6)

        # Negative checks
        neg_elt = int((elt_df["loss"] < 0).sum()) if not elt_df.empty else 0
        neg_ylt = int((ylt_df["annual_loss"] < 0).sum()) if not ylt_df.empty else 0
        total_negatives = neg_elt + neg_ylt

        # Event-level sum check vs ELT sum
        events_reconciled = True
        if not elt_df.empty:
            grouped_event_sum = float(elt_df.groupby(["simulation_year", "occurrence_id"])["loss"].sum().sum())
            if abs(grouped_event_sum - elt_total) > self.tolerance:
                events_reconciled = False

        # Annual sum check
        annual_reconciled = True
        if not elt_df.empty:
            grouped_year_sum = float(elt_df.groupby("simulation_year")["loss"].sum().sum())
            if abs(grouped_year_sum - ylt_total) > self.tolerance:
                annual_reconciled = False

        years_with_events = int((ylt_df["event_count"] > 0).sum()) if not ylt_df.empty else 0
        years_with_losses = int((ylt_df["annual_loss"] > 0).sum()) if not ylt_df.empty else 0

        passed = (
            total_reconciled
            and events_reconciled
            and annual_reconciled
            and (total_negatives == 0)
            and (len(ylt_df) == simulation_years)
        )

        return ReconciliationReport(
            passed=passed,
            elt_total_loss=round(elt_total, 2),
            ylt_total_loss=round(ylt_total, 2),
            absolute_difference=round(diff, 6),
            relative_difference=round(rel_diff, 8),
            tolerance=self.tolerance,
            total_elt_rows=len(elt_df),
            total_simulation_years=simulation_years,
            years_with_events=years_with_events,
            years_with_losses=years_with_losses,
            events_reconciled=events_reconciled,
            annual_losses_reconciled=annual_reconciled,
            negative_losses_count=total_negatives,
        )
