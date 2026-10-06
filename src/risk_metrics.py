"""FLOODTAIL — Quantitative Risk Metrics, Loss Distributions, OEP, AEP, PML, VaR & TVaR Engine.

Computes empirical annual aggregate loss distributions, Average Annual Loss (AAL),
Occurrence Exceedance Probability (OEP), Aggregate Exceedance Probability (AEP),
Probable Maximum Loss (PML), Value at Risk (VaR), and Tail Value at Risk (TVaR/Expected Shortfall).
Includes independent verification recomputation methods to ensure numerical integrity.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd

from src.exceptions import ModelCalculationError
from src.logging_config import get_logger

logger = get_logger("risk_metrics")


@dataclass
class ExceedancePoint:
    """A single return-period point on an exceedance probability curve."""

    return_period_years: float
    exceedance_probability: float
    loss: float
    metric_type: str  # 'OEP' or 'AEP'
    sample_size: int
    empirical_support_warning: Optional[str] = None


@dataclass
class TailSetDetails:
    """Exact tail years and boundary weights used for Tail Value at Risk (TVaR)."""

    confidence_level: float
    tail_probability: float
    total_years: int
    tail_year_count: int
    var_threshold: float
    tail_indices: list[int]
    tail_years: list[int]
    tail_losses: list[float]
    tail_weights: list[float]


@dataclass
class RiskMetricsSummary:
    """Comprehensive portfolio-level risk metrics."""

    simulation_years: int
    total_simulated_loss: float
    aal: float
    var_99: float
    var_996: float
    tvar_99: float
    tvar_996: float
    pml_100: float
    pml_250: float
    pml_500: float
    oep_curve: list[ExceedancePoint]
    aep_curve: list[ExceedancePoint]
    tail_set_996: TailSetDetails
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RiskMetricsEngine:
    """Calculates actuarial and quantitative catastrophe risk metrics from YLT."""

    STANDARD_RETURN_PERIODS = [10, 25, 50, 100, 250, 500]

    def __init__(self, default_confidence: float = 0.996) -> None:
        self.default_confidence = default_confidence

    @staticmethod
    def calculate_aal(annual_losses: np.ndarray) -> float:
        """Calculate Average Annual Loss (AAL).

        AAL = (1/N) * sum(L_y)
        """
        if len(annual_losses) == 0:
            return 0.0
        return float(np.mean(annual_losses))

    @staticmethod
    def verify_aal_independent(annual_losses: np.ndarray) -> float:
        """Independent recomputation of AAL using compensated summation."""
        if len(annual_losses) == 0:
            return 0.0
        # Independent manual accumulator
        total = 0.0
        c = 0.0
        for x in annual_losses:
            y = float(x) - c
            t = total + y
            c = (t - total) - y
            total = t
        return float(total / len(annual_losses))

    @classmethod
    def calculate_exceedance_curve(
        cls,
        loss_values: np.ndarray,
        metric_type: str = "AEP",
        return_periods: Optional[list[int]] = None,
    ) -> list[ExceedancePoint]:
        """Compute empirical Exceedance Probability (EP) curve for given return periods.

        EP = 1 / Return_Period.
        Quantile is computed using empirical sorted ranks:
        rank = (1 - EP) * N.
        """
        n = len(loss_values)
        if n == 0:
            return []

        rps = return_periods or cls.STANDARD_RETURN_PERIODS
        sorted_losses = np.sort(loss_values)  # Ascending

        points: list[ExceedancePoint] = []
        for rp in rps:
            ep = 1.0 / rp
            tail_count = n * ep

            # Warning if tail observations are fewer than 10
            warning = None
            if tail_count < 10:
                warning = f"Limited empirical support: only ~{tail_count:.1f} annual observations in 1-in-{rp} tail."

            if tail_count < 1.0:
                # Beyond simulation resolution
                loss_val = float(sorted_losses[-1])
                warning = f"Return period 1-in-{rp} exceeds simulation resolution ({n} years)."
            else:
                # Standard empirical quantile: rank from top
                # Percentile q = 100 * (1 - ep)
                loss_val = float(np.percentile(sorted_losses, 100.0 * (1.0 - ep)))

            points.append(
                ExceedancePoint(
                    return_period_years=float(rp),
                    exceedance_probability=round(ep, 6),
                    loss=round(max(0.0, loss_val), 2),
                    metric_type=metric_type,
                    sample_size=n,
                    empirical_support_warning=warning,
                )
            )

        return points

    @staticmethod
    def calculate_var(loss_values: np.ndarray, alpha: float = 0.996) -> float:
        """Calculate empirical Value at Risk (VaR_alpha)."""
        if len(loss_values) == 0:
            return 0.0
        sorted_losses = np.sort(loss_values)
        return float(np.percentile(sorted_losses, 100.0 * alpha))

    @classmethod
    def identify_tail_set(
        cls,
        ylt_df: pd.DataFrame,
        alpha: float = 0.996,
    ) -> TailSetDetails:
        """Identify the exact simulation years and boundary weights belonging to the alpha-tail.

        For N years and confidence alpha:
        Tail mass = (1 - alpha) * N years.
        Observations sorted descending.
        The top k full years receive weight 1.0 / (N * (1 - alpha)),
        and the boundary year receives the exact fractional remainder.
        """
        n = len(ylt_df)
        if n == 0:
            raise ModelCalculationError("Cannot calculate tail set on empty YLT.")

        tail_mass = (1.0 - alpha) * n
        if tail_mass <= 0:
            raise ModelCalculationError(f"Invalid tail mass for alpha={alpha}, N={n}")

        sorted_df = ylt_df.sort_values(by="annual_loss", ascending=False).reset_index()

        k_full = int(math.floor(tail_mass))
        fraction = tail_mass - k_full

        tail_indices: list[int] = []
        tail_years: list[int] = []
        tail_losses: list[float] = []
        tail_weights: list[float] = []

        total_weight_denom = tail_mass

        for i in range(k_full):
            row = sorted_df.iloc[i]
            tail_indices.append(int(row["index"]))
            tail_years.append(int(row["simulation_year"]))
            tail_losses.append(float(row["annual_loss"]))
            tail_weights.append(1.0 / total_weight_denom)

        if fraction > 1e-9 and k_full < n:
            row = sorted_df.iloc[k_full]
            tail_indices.append(int(row["index"]))
            tail_years.append(int(row["simulation_year"]))
            tail_losses.append(float(row["annual_loss"]))
            tail_weights.append(fraction / total_weight_denom)

        var_threshold = float(sorted_df.iloc[min(k_full, n - 1)]["annual_loss"])

        return TailSetDetails(
            confidence_level=alpha,
            tail_probability=1.0 - alpha,
            total_years=n,
            tail_year_count=len(tail_years),
            var_threshold=var_threshold,
            tail_indices=tail_indices,
            tail_years=tail_years,
            tail_losses=tail_losses,
            tail_weights=tail_weights,
        )

    @classmethod
    def calculate_tvar(cls, ylt_df: pd.DataFrame, alpha: float = 0.996) -> float:
        """Calculate Tail Value at Risk (TVaR / Expected Shortfall) at confidence level alpha."""
        tail_set = cls.identify_tail_set(ylt_df, alpha=alpha)
        weighted_loss = sum(w * loss for w, loss in zip(tail_set.tail_weights, tail_set.tail_losses))
        return float(weighted_loss)

    @staticmethod
    def verify_tvar_independent(ylt_df: pd.DataFrame, alpha: float = 0.996) -> float:
        """Independent calculation of TVaR using simple tail slicing."""
        losses = ylt_df["annual_loss"].values
        n = len(losses)
        if n == 0:
            return 0.0
        cutoff = np.percentile(losses, 100.0 * alpha)
        tail = losses[losses >= cutoff]
        if len(tail) == 0:
            return float(cutoff)
        return float(np.mean(tail))

    def evaluate(self, ylt_df: pd.DataFrame) -> RiskMetricsSummary:
        """Compute full suite of portfolio risk metrics from verified Year Loss Table (YLT)."""
        n_years = len(ylt_df)
        if n_years == 0:
            raise ModelCalculationError("YLT is empty: cannot compute risk analytics.")

        annual_losses = ylt_df["annual_loss"].astype(float).values
        max_event_losses = ylt_df["max_event_loss"].astype(float).values
        tot_sim_loss = float(annual_losses.sum())

        # 1. AAL
        aal = self.calculate_aal(annual_losses)

        # 2. OEP Curve (based on max_event_loss)
        oep_curve = self.calculate_exceedance_curve(max_event_losses, metric_type="OEP")

        # 3. AEP Curve (based on annual_loss)
        aep_curve = self.calculate_exceedance_curve(annual_losses, metric_type="AEP")

        # 4. VaR & TVaR
        var_99 = self.calculate_var(annual_losses, alpha=0.99)
        var_996 = self.calculate_var(annual_losses, alpha=0.996)

        tvar_99 = self.calculate_tvar(ylt_df, alpha=0.99)
        tvar_996 = self.calculate_tvar(ylt_df, alpha=0.996)

        tail_set_996 = self.identify_tail_set(ylt_df, alpha=0.996)

        # 5. PML values from AEP curve
        pml_map = {int(pt.return_period_years): pt.loss for pt in aep_curve}
        pml_100 = pml_map.get(100, var_99)
        pml_250 = pml_map.get(250, var_996)
        pml_500 = pml_map.get(500, pml_250)

        logger.info(
            "Risk Metrics Evaluated (%d years): AAL = $%s, 1-in-250 PML = $%s, TVaR(99.6%%) = $%s",
            n_years,
            f"{aal:,.2f}",
            f"{pml_250:,.2f}",
            f"{tvar_996:,.2f}",
        )

        return RiskMetricsSummary(
            simulation_years=n_years,
            total_simulated_loss=tot_sim_loss,
            aal=round(aal, 2),
            var_99=round(var_99, 2),
            var_996=round(var_996, 2),
            tvar_99=round(tvar_99, 2),
            tvar_996=round(tvar_996, 2),
            pml_100=round(pml_100, 2),
            pml_250=round(pml_250, 2),
            pml_500=round(pml_500, 2),
            oep_curve=oep_curve,
            aep_curve=aep_curve,
            tail_set_996=tail_set_996,
        )
