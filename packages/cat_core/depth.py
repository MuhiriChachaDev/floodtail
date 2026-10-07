"""Hazard score → depth mapping and tier / RP helpers."""

from __future__ import annotations

import pandas as pd

from packages.cat_core.assumptions import AssumptionsProfile
from packages.cat_core.exposure import HAZARD_SCORE_PREFIX


def score_to_depth(score: float, d_max_m: float) -> float:
    """depth_m = hazard_score × D_max (clipped score)."""
    s = max(0.0, min(1.0, float(score)))
    return s * float(d_max_m)


def add_depth_columns(
    df: pd.DataFrame,
    profile: AssumptionsProfile,
    *,
    score_prefix: str = HAZARD_SCORE_PREFIX,
    depth_prefix: str = "depth_m_",
) -> pd.DataFrame:
    """Add depth_m_{tier} columns from hazard_score_{tier} × D_max."""
    out = df.copy()
    for tier in profile.tier_names:
        score_col = f"{score_prefix}{tier}"
        depth_col = f"{depth_prefix}{tier}"
        if score_col not in out.columns:
            out[score_col] = 0.0
        out[depth_col] = out[score_col].astype(float).clip(0.0, 1.0) * profile.d_max_m
    return out


def tier_return_period_table(profile: AssumptionsProfile) -> list[dict]:
    rows: list[dict] = []
    for tier, rp in profile.tier_rp_map().items():
        rows.append(
            {
                "tier": tier,
                "return_period": rp,
                "aep": profile.aep_for_rp(rp),
            }
        )
    return rows
