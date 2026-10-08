"""Ground-up loss: damage_ratio × tiv_kes."""

from __future__ import annotations

import pandas as pd

from packages.cat_core.exceptions import ReconciliationError


def add_loss_columns(
    df: pd.DataFrame,
    tier_names: list[str],
    *,
    damage_prefix: str = "damage_ratio_",
    loss_prefix: str = "loss_kes_",
    tiv_col: str = "tiv_kes",
) -> pd.DataFrame:
    out = df.copy()
    tiv = out[tiv_col].astype(float)
    for tier in tier_names:
        dmg = out[f"{damage_prefix}{tier}"].astype(float).clip(0.0, 1.0)
        out[f"{loss_prefix}{tier}"] = (dmg * tiv).round(2)
    return out


def reconcile_location_losses(
    df: pd.DataFrame,
    tier_names: list[str],
    *,
    loss_prefix: str = "loss_kes_",
    tolerance: float = 1e-2,
) -> dict[str, float]:
    """Sum per-location losses and verify non-negative + finite."""
    totals: dict[str, float] = {}
    for tier in tier_names:
        col = f"{loss_prefix}{tier}"
        vals = df[col].astype(float)
        if vals.isna().any():
            raise ReconciliationError(f"NaN losses in {col}")
        if (vals < -tolerance).any():
            raise ReconciliationError(f"Negative losses in {col}")
        totals[tier] = float(vals.sum())
    if not totals:
        raise ReconciliationError("Empty loss tables")
    return totals
