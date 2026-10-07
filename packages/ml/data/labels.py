"""Honest synthetic label builders for hazard and vulnerability."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from packages.cat_core.assumptions import AssumptionsProfile
from packages.cat_core.exposure import HAZARD_SCORE_PREFIX
from packages.cat_core.vulnerability_prior import damage_ratio


LABEL_RECIPE_HAZARD = "proxy_scores_plus_optional_hotspot_uplift_v1"
LABEL_RECIPE_VULN = "jrc_prior_plus_gaussian_noise_v1"


def build_hazard_labels(
    df: pd.DataFrame,
    profile: AssumptionsProfile,
    *,
    hotspot_uplift: float = 0.05,
    hotspot_radius_km: float = 2.0,
) -> tuple[pd.DataFrame, dict]:
    """
    Labels = clipped proxy CSV/raster scores.
    Optional mild uplift when near a hotspot (dist_hotspot_km present).
    Synthetic — not gauge-validated.
    """
    out = df.copy()
    target_cols: list[str] = []
    for tier in profile.tier_names:
        src = f"{HAZARD_SCORE_PREFIX}{tier}"
        tgt = f"label_hazard_{tier}"
        if src not in out.columns:
            out[src] = 0.0
        scores = pd.to_numeric(out[src], errors="coerce").fillna(0.0).clip(0.0, 1.0)
        if "dist_hotspot_km" in out.columns and "has_hotspot_layer" in out.columns:
            near = (
                (out["has_hotspot_layer"] == 1)
                & out["dist_hotspot_km"].notna()
                & (out["dist_hotspot_km"] <= hotspot_radius_km)
            )
            scores = scores.where(~near, (scores + hotspot_uplift).clip(0.0, 1.0))
        out[tgt] = scores
        target_cols.append(tgt)

    meta = {
        "label_recipe_id": LABEL_RECIPE_HAZARD,
        "synthetic": True,
        "hotspot_uplift": hotspot_uplift,
        "hotspot_radius_km": hotspot_radius_km,
        "target_columns": target_cols,
        "notes": "Proxy susceptibility labels; optional hotspot uplift; not flood gauges.",
    }
    return out, meta


def build_vulnerability_training_frame(
    profile: AssumptionsProfile,
    *,
    n_samples: int = 2000,
    seed: int = 42,
    noise_std: float = 0.03,
) -> tuple[pd.DataFrame, dict]:
    """
    Synthetic vulnerability dataset from JRC prior ± noise.
    Location-flexible: only needs housing_class enum from assumptions profile.
    """
    rng = np.random.default_rng(seed)
    classes = list(profile.housing_classes)
    rows: list[dict] = []
    for i in range(n_samples):
        housing = classes[int(rng.integers(0, len(classes)))]
        depth = float(rng.uniform(0.0, profile.d_max_m))
        prior = damage_ratio(depth, housing)
        noisy = float(np.clip(prior + rng.normal(0.0, noise_std), 0.0, 1.0))
        rows.append(
            {
                "loc_id": f"SYN-VULN-{i:05d}",
                "housing_class": housing,
                "depth_m": depth,
                "tiv_kes": float(rng.uniform(5e5, 5e7)),
                "floor_area_m2": float(rng.uniform(10, 400)),
                "lat": 0.0,
                "lon": 0.0,
                "dist_hotspot_km": np.nan,
                "has_hotspot_layer": 0,
                "label_damage_ratio": noisy,
                "prior_damage_ratio": prior,
            }
        )
    frame = pd.DataFrame(rows)
    meta = {
        "label_recipe_id": LABEL_RECIPE_VULN,
        "synthetic": True,
        "n_samples": n_samples,
        "noise_std": noise_std,
        "seed": seed,
        "target_columns": ["label_damage_ratio"],
        "notes": "Synthetic labels from JRC-adapted priors ± noise; not claims-calibrated.",
    }
    return frame, meta
