"""FLOODTAIL — Shadow Exposure & Protection Gap Analytics Engine.

Estimates surrounding uninsured and underinsured commercial & residential asset values
using spatial urbanization density proxies and regional multipliers.
Provides insurers and reinsurers with a community-level risk amplification metric.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd

from src.exceptions import ModelCalculationError
from src.logging_config import get_logger

logger = get_logger("shadow_exposure")


# Regional shadow exposure density multipliers (uninsured asset ratio to insured TIV)
REGIONAL_SHADOW_MULTIPLIERS: dict[str, dict[str, Any]] = {
    "Nairobi": {"multiplier": 3.8, "tier": "CBD_HIGH_DENSITY", "amplification": "HIGH"},
    "Mombasa": {"multiplier": 3.2, "tier": "COASTAL_PORT_URBAN", "amplification": "HIGH"},
    "Kisumu": {"multiplier": 2.5, "tier": "LAKE_BASIN_REGIONAL", "amplification": "MEDIUM"},
    "Nakuru": {"multiplier": 2.2, "tier": "RIFT_VALLEY_URBAN", "amplification": "MEDIUM"},
    "Eldoret": {"multiplier": 2.0, "tier": "WESTERN_HIGHLANDS", "amplification": "LOW"},
    "Naivasha": {"multiplier": 2.4, "tier": "HORTICULTURE_BASIN", "amplification": "MEDIUM"},
    "Malindi": {"multiplier": 2.1, "tier": "COASTAL_TOURISM", "amplification": "LOW"},
}

DEFAULT_SHADOW_MULTIPLIER = {"multiplier": 2.0, "tier": "PERI_URBAN", "amplification": "LOW"}


@dataclass
class ShadowExposureResult:
    """Shadow exposure metrics for a single policy and surrounding zone."""

    policy_id: str
    region: str
    insured_tiv: float
    shadow_tiv_estimate: float
    shadow_multiplier: float
    protection_gap_pct: float
    community_amplification: str
    urban_density_tier: str


class ShadowExposureEngine:
    """Evaluates surrounding uninsured assets and protection gap ratios."""

    def evaluate_portfolio_shadow(
        self,
        portfolio_df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """Compute shadow exposure for all portfolio policies."""
        if portfolio_df is None or portfolio_df.empty:
            raise ModelCalculationError("Portfolio DataFrame is empty for shadow exposure calculation.")

        results: list[ShadowExposureResult] = []

        for _, row in portfolio_df.iterrows():
            pid = str(row["policy_id"])
            region = str(row.get("region", "Nairobi"))
            tiv = float(row["insured_value"])

            meta = REGIONAL_SHADOW_MULTIPLIERS.get(region, DEFAULT_SHADOW_MULTIPLIER)
            mult = float(meta["multiplier"])
            shadow_tiv = tiv * mult
            total_community_tiv = tiv + shadow_tiv
            protection_gap = (shadow_tiv / total_community_tiv * 100.0) if total_community_tiv > 0 else 0.0

            results.append(
                ShadowExposureResult(
                    policy_id=pid,
                    region=region,
                    insured_tiv=tiv,
                    shadow_tiv_estimate=shadow_tiv,
                    shadow_multiplier=mult,
                    protection_gap_pct=round(protection_gap, 1),
                    community_amplification=str(meta["amplification"]),
                    urban_density_tier=str(meta["tier"]),
                )
            )

        shadow_df = pd.DataFrame([
            {
                "policy_id": r.policy_id,
                "region": r.region,
                "insured_tiv": r.insured_tiv,
                "shadow_tiv_estimate": r.shadow_tiv_estimate,
                "shadow_multiplier": r.shadow_multiplier,
                "protection_gap_pct": r.protection_gap_pct,
                "community_amplification": r.community_amplification,
                "urban_density_tier": r.urban_density_tier,
            }
            for r in results
        ])

        total_insured = float(shadow_df["insured_tiv"].sum())
        total_shadow = float(shadow_df["shadow_tiv_estimate"].sum())
        overall_gap = (total_shadow / (total_insured + total_shadow) * 100.0) if (total_insured + total_shadow) > 0 else 0.0

        summary = {
            "total_insured_tiv": total_insured,
            "total_shadow_tiv_estimate": total_shadow,
            "aggregate_protection_gap_pct": round(overall_gap, 1),
            "high_amplification_policy_count": int((shadow_df["community_amplification"] == "HIGH").sum()),
            "provenance_note": "Shadow exposure is an estimated proxy of surrounding uninsured assets based on urban density models.",
        }

        return shadow_df, summary
