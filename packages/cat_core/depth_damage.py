"""Depth–damage summary: prior curves + empirical portfolio points from a run frame."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .assumptions import AssumptionsProfile
from .vulnerability_prior import JRC_ADAPTED_CURVES


def prior_curve_payload(
    profile: AssumptionsProfile | None = None,
) -> dict[str, list[dict[str, float]]]:
    """Depth–damage priors for the API / UI (profile overrides merged when given)."""
    curves = (
        profile.resolved_vulnerability_curves()
        if profile is not None
        else JRC_ADAPTED_CURVES
    )
    out: dict[str, list[dict[str, float]]] = {}
    for housing, pts in curves.items():
        out[housing] = [
            {"depth_m": float(d), "damage_ratio": float(r)} for d, r in pts
        ]
    return out


def build_depth_damage_summary(
    frame: pd.DataFrame,
    profile: AssumptionsProfile,
) -> dict[str, Any]:
    """
    Empirical portfolio depth vs damage by flood tier, plus housing-class
    means at the most severe tier. Used for depth–damage curve overlays.
    """
    work = frame
    rp_map = profile.tier_rp_map()
    by_tier: list[dict[str, Any]] = []

    for tier in profile.tier_names:
        depth_col = f"depth_m_{tier}"
        dmg_col = f"damage_ratio_{tier}"
        if depth_col not in work.columns or dmg_col not in work.columns:
            continue
        depths = work[depth_col].astype(float)
        dmgs = work[dmg_col].astype(float).clip(0.0, 1.0)
        by_tier.append(
            {
                "tier": tier,
                "return_period": int(rp_map.get(tier, 0)),
                "mean_depth_m": round(float(depths.mean()), 4),
                "mean_damage_ratio": round(float(dmgs.mean()), 4),
                "p90_depth_m": round(float(depths.quantile(0.9)), 4),
                "p90_damage_ratio": round(float(dmgs.quantile(0.9)), 4),
            }
        )

    by_housing: list[dict[str, Any]] = []
    ref_tier = profile.tier_names[-1] if profile.tier_names else "extreme"
    depth_ref = f"depth_m_{ref_tier}"
    dmg_ref = f"damage_ratio_{ref_tier}"
    if (
        "housing_class" in work.columns
        and depth_ref in work.columns
        and dmg_ref in work.columns
    ):
        for housing, grp in work.groupby(work["housing_class"].astype(str)):
            by_housing.append(
                {
                    "housing_class": str(housing),
                    "n": int(len(grp)),
                    "reference_tier": ref_tier,
                    "mean_depth_m": round(float(grp[depth_ref].astype(float).mean()), 4),
                    "mean_damage_ratio": round(
                        float(grp[dmg_ref].astype(float).clip(0.0, 1.0).mean()), 4
                    ),
                }
            )
        by_housing.sort(key=lambda r: -r["n"])

    return {
        "source": "run_frame",
        "d_max_m": float(profile.d_max_m),
        "assumptions_version": profile.assumptions_version,
        "by_tier": by_tier,
        "by_housing_class": by_housing,
        "prior_curves": prior_curve_payload(profile),
    }
