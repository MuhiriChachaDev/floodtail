"""Housing-class (and optional hotspot) concentration metrics."""

from __future__ import annotations

from typing import Any

import pandas as pd


def housing_class_accumulation(
    df: pd.DataFrame,
    tier_names: list[str],
    *,
    loss_prefix: str = "loss_kes_",
    tiv_col: str = "tiv_kes",
) -> list[dict[str, Any]]:
    total_tiv = float(df[tiv_col].sum()) or 1.0
    # Use most severe tier present for loss share if available, else last tier
    loss_col = f"{loss_prefix}{tier_names[-1]}" if tier_names else None
    total_loss = float(df[loss_col].sum()) if loss_col and loss_col in df.columns else 0.0
    total_loss = total_loss or 1.0

    rows: list[dict[str, Any]] = []
    for housing_class, group in df.groupby("housing_class"):
        tiv = float(group[tiv_col].sum())
        loss = float(group[loss_col].sum()) if loss_col and loss_col in group.columns else 0.0
        rows.append(
            {
                "housing_class": str(housing_class),
                "n_locations": int(len(group)),
                "tiv_kes": tiv,
                "tiv_share_pct": 100.0 * tiv / total_tiv,
                "loss_kes_extreme": loss,
                "loss_share_pct": 100.0 * loss / total_loss,
            }
        )
    rows.sort(key=lambda r: r["loss_share_pct"], reverse=True)
    return rows


def top_location_concentration(
    df: pd.DataFrame,
    *,
    loss_col: str,
    top_n: int = 10,
) -> list[dict[str, Any]]:
    if loss_col not in df.columns:
        return []
    ranked = df.nlargest(top_n, loss_col)
    total = float(df[loss_col].sum()) or 1.0
    out: list[dict[str, Any]] = []
    for _, row in ranked.iterrows():
        loss = float(row[loss_col])
        out.append(
            {
                "loc_id": str(row.get("loc_id", "")),
                "housing_class": str(row.get("housing_class", "")),
                "loss_kes": loss,
                "loss_share_pct": 100.0 * loss / total,
                "lat": float(row["lat"]) if "lat" in row else None,
                "lon": float(row["lon"]) if "lon" in row else None,
            }
        )
    return out


def build_accumulation_summary(
    df: pd.DataFrame,
    tier_names: list[str],
    *,
    loss_prefix: str = "loss_kes_",
) -> dict[str, Any]:
    severe_tier = tier_names[-1] if tier_names else "extreme"
    loss_col = f"{loss_prefix}{severe_tier}"
    by_class = housing_class_accumulation(df, tier_names, loss_prefix=loss_prefix)
    top_locs = top_location_concentration(df, loss_col=loss_col, top_n=10)
    return {
        "by_housing_class": by_class,
        "top_locations": top_locs,
        "reference_tier": severe_tier,
    }
