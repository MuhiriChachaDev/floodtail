"""FLOODTAIL — Portfolio Accumulation, Concentration & Spatial Co-Hit Analytics Engine.

Calculates geographic, occupancy, and peril accumulation metrics,
identifies spatial risk concentrations (TIV vs Loss), and computes event-level
co-hit metrics to expose portfolio correlation drivers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd

from src.logging_config import get_logger

logger = get_logger("accumulation")


@dataclass
class RegionalAccumulation:
    """Accumulation summary for a geographic region."""

    region: str
    policy_count: int
    total_tiv: float
    tiv_share_pct: float
    total_aal: float
    aal_share_pct: float
    total_tail_contribution: float
    tail_share_pct: float


@dataclass
class PropertyTypeAccumulation:
    """Accumulation summary for an occupancy/property type."""

    property_type: str
    policy_count: int
    total_tiv: float
    tiv_share_pct: float
    total_aal: float
    aal_share_pct: float
    total_tail_contribution: float
    tail_share_pct: float


@dataclass
class CoHitPolicyMetric:
    """Co-hit profile for an individual policy."""

    policy_id: str
    event_hit_count: int
    co_hit_event_count: int  # Events where >= 2 policies were hit simultaneously
    co_hit_rate: float  # co_hit_event_count / max(1, event_hit_count)
    max_concurrent_exposed_tiv: float
    top_co_hit_perils: list[str]


@dataclass
class AccumulationAnalysisResult:
    """Comprehensive portfolio accumulation and concentration results."""

    total_portfolio_tiv: float
    total_portfolio_aal: float
    total_portfolio_tvar: float
    regional_breakdown: list[RegionalAccumulation]
    property_type_breakdown: list[PropertyTypeAccumulation]
    tiv_concentration_top1_pct: float
    tiv_concentration_top5_pct: float
    tiv_concentration_top10_pct: float
    loss_concentration_top1_pct: float
    loss_concentration_top5_pct: float
    loss_concentration_top10_pct: float
    regional_tiv_hhi: float
    regional_loss_hhi: float
    co_hit_metrics: list[CoHitPolicyMetric]
    accumulation_dataframe: pd.DataFrame
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PortfolioAccumulationEngine:
    """Analyzes accumulation of exposure, loss, and spatial co-occurrences."""

    def evaluate(
        self,
        portfolio_df: pd.DataFrame,
        elt_df: pd.DataFrame,
        tail_df: pd.DataFrame,
    ) -> AccumulationAnalysisResult:
        """Run complete accumulation, concentration, and co-hit analysis."""
        tot_tiv = float(portfolio_df["insured_value"].sum()) if not portfolio_df.empty else 1.0

        # Merge portfolio exposure metadata with allocated tail metrics
        merged = pd.merge(
            portfolio_df[["policy_id", "insured_value", "property_type", "region"]],
            tail_df[["policy_id", "aal", "tail_contribution"]],
            on="policy_id",
            how="left",
        ).fillna({"aal": 0.0, "tail_contribution": 0.0, "region": "Unknown"})

        tot_aal = float(merged["aal"].sum()) if not merged.empty else 1.0
        tot_tvar = float(merged["tail_contribution"].sum()) if not merged.empty else 1.0

        logger.info(
            "Analyzing portfolio accumulation: %d policies, Total TIV = $%s, Total AAL = $%s",
            len(merged),
            f"{tot_tiv:,.2f}",
            f"{tot_aal:,.2f}",
        )

        # 1. Regional Breakdown
        regional_rows: list[RegionalAccumulation] = []
        for reg, grp in merged.groupby("region"):
            reg_tiv = float(grp["insured_value"].sum())
            reg_aal = float(grp["aal"].sum())
            reg_tail = float(grp["tail_contribution"].sum())
            regional_rows.append(
                RegionalAccumulation(
                    region=str(reg),
                    policy_count=len(grp),
                    total_tiv=round(reg_tiv, 2),
                    tiv_share_pct=round((reg_tiv / max(tot_tiv, 1e-9)) * 100.0, 2),
                    total_aal=round(reg_aal, 2),
                    aal_share_pct=round((reg_aal / max(tot_aal, 1e-9)) * 100.0, 2),
                    total_tail_contribution=round(reg_tail, 2),
                    tail_share_pct=round((reg_tail / max(tot_tvar, 1e-9)) * 100.0, 2),
                )
            )
        regional_rows.sort(key=lambda r: r.total_tail_contribution, reverse=True)

        # 2. Property Type Breakdown
        ptype_rows: list[PropertyTypeAccumulation] = []
        for ptype, grp in merged.groupby("property_type"):
            p_tiv = float(grp["insured_value"].sum())
            p_aal = float(grp["aal"].sum())
            p_tail = float(grp["tail_contribution"].sum())
            ptype_rows.append(
                PropertyTypeAccumulation(
                    property_type=str(ptype),
                    policy_count=len(grp),
                    total_tiv=round(p_tiv, 2),
                    tiv_share_pct=round((p_tiv / max(tot_tiv, 1e-9)) * 100.0, 2),
                    total_aal=round(p_aal, 2),
                    aal_share_pct=round((p_aal / max(tot_aal, 1e-9)) * 100.0, 2),
                    total_tail_contribution=round(p_tail, 2),
                    tail_share_pct=round((p_tail / max(tot_tvar, 1e-9)) * 100.0, 2),
                )
            )
        ptype_rows.sort(key=lambda r: r.total_tail_contribution, reverse=True)

        # 3. Concentration Metrics: Top 1%, Top 5%, Top 10%
        n_pols = len(merged)
        k1 = max(1, int(math.ceil(n_pols * 0.01)))
        k5 = max(1, int(math.ceil(n_pols * 0.05)))
        k10 = max(1, int(math.ceil(n_pols * 0.10)))

        sorted_tiv = merged["insured_value"].sort_values(ascending=False).values
        tiv_top1 = (sorted_tiv[:k1].sum() / max(tot_tiv, 1e-9)) * 100.0
        tiv_top5 = (sorted_tiv[:k5].sum() / max(tot_tiv, 1e-9)) * 100.0
        tiv_top10 = (sorted_tiv[:k10].sum() / max(tot_tiv, 1e-9)) * 100.0

        sorted_loss = merged["tail_contribution"].sort_values(ascending=False).values
        loss_top1 = (sorted_loss[:k1].sum() / max(tot_tvar, 1e-9)) * 100.0
        loss_top5 = (sorted_loss[:k5].sum() / max(tot_tvar, 1e-9)) * 100.0
        loss_top10 = (sorted_loss[:k10].sum() / max(tot_tvar, 1e-9)) * 100.0

        # Herfindahl-Hirschman Index (HHI = sum(shares^2))
        reg_tiv_shares = np.array([r.tiv_share_pct / 100.0 for r in regional_rows])
        reg_loss_shares = np.array([r.tail_share_pct / 100.0 for r in regional_rows])
        hhi_tiv = float((reg_tiv_shares**2).sum()) if len(reg_tiv_shares) > 0 else 0.0
        hhi_loss = float((reg_loss_shares**2).sum()) if len(reg_loss_shares) > 0 else 0.0

        # 4. Spatial Co-Hit Analysis
        co_hit_records: list[CoHitPolicyMetric] = []
        if not elt_df.empty:
            # Group ELT by occurrence (simulation_year, occurrence_id)
            occ_groups = elt_df.groupby(["simulation_year", "occurrence_id"])

            # Map occurrence -> list of affected policies and concurrent TIV
            occ_to_pols: dict[tuple[int, int], set[str]] = {}
            occ_to_tiv: dict[tuple[int, int], float] = {}

            for (s_yr, o_id), grp in occ_groups:
                p_set = set(grp["policy_id"].astype(str))
                occ_to_pols[(s_yr, o_id)] = p_set
                occ_to_tiv[(s_yr, o_id)] = float(grp["insured_value"].sum())

            # For each policy, analyze occurrences it participated in
            pol_to_occs = elt_df.groupby("policy_id")[["simulation_year", "occurrence_id", "event_id"]].apply(
                lambda g: list(zip(g["simulation_year"], g["occurrence_id"], g["event_id"]))
            ).to_dict()

            for pid in merged["policy_id"]:
                occs = pol_to_occs.get(pid, [])
                evt_hit_count = len(occs)
                co_hit_count = 0
                max_conc_tiv = 0.0
                co_events = []

                for s_yr, o_id, e_id in occs:
                    conc_pols = occ_to_pols.get((s_yr, o_id), set())
                    if len(conc_pols) >= 2:
                        co_hit_count += 1
                        co_events.append(e_id)
                        conc_tiv = occ_to_tiv.get((s_yr, o_id), 0.0)
                        if conc_tiv > max_conc_tiv:
                            max_conc_tiv = conc_tiv

                co_hit_rate = (co_hit_count / max(1, evt_hit_count)) if evt_hit_count > 0 else 0.0
                co_hit_records.append(
                    CoHitPolicyMetric(
                        policy_id=pid,
                        event_hit_count=evt_hit_count,
                        co_hit_event_count=co_hit_count,
                        co_hit_rate=round(co_hit_rate, 4),
                        max_concurrent_exposed_tiv=round(max_conc_tiv, 2),
                        top_co_hit_perils=list(set(co_events))[:5],
                    )
                )
        else:
            for pid in merged["policy_id"]:
                co_hit_records.append(
                    CoHitPolicyMetric(
                        policy_id=pid,
                        event_hit_count=0,
                        co_hit_event_count=0,
                        co_hit_rate=0.0,
                        max_concurrent_exposed_tiv=0.0,
                        top_co_hit_perils=[],
                    )
                )

        co_hit_df = pd.DataFrame([
            {
                "policy_id": c.policy_id,
                "event_hit_count": c.event_hit_count,
                "co_hit_event_count": c.co_hit_event_count,
                "co_hit_rate": c.co_hit_rate,
                "max_concurrent_exposed_tiv": c.max_concurrent_exposed_tiv,
            }
            for c in co_hit_records
        ])

        accum_df = pd.merge(merged, co_hit_df, on="policy_id", how="left")

        return AccumulationAnalysisResult(
            total_portfolio_tiv=round(tot_tiv, 2),
            total_portfolio_aal=round(tot_aal, 2),
            total_portfolio_tvar=round(tot_tvar, 2),
            regional_breakdown=regional_rows,
            property_type_breakdown=ptype_rows,
            tiv_concentration_top1_pct=round(tiv_top1, 2),
            tiv_concentration_top5_pct=round(tiv_top5, 2),
            tiv_concentration_top10_pct=round(tiv_top10, 2),
            loss_concentration_top1_pct=round(loss_top1, 2),
            loss_concentration_top5_pct=round(loss_top5, 2),
            loss_concentration_top10_pct=round(loss_top10, 2),
            regional_tiv_hhi=round(hhi_tiv, 4),
            regional_loss_hhi=round(hhi_loss, 4),
            co_hit_metrics=co_hit_records,
            accumulation_dataframe=accum_df,
        )
