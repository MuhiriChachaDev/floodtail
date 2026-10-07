"""Deterministic counterfactuals: feature ± → Δ prediction → Δ loss."""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from packages.cat_core.assumptions import AssumptionsProfile
from packages.ml.estimators import clip01
from packages.ml.features.builder import FeatureBuilder
from packages.ml.registry import ModelRegistry


def _predict_vuln_row(
    row: pd.DataFrame,
    model: Any,
    builder: FeatureBuilder,
    *,
    depth_m: float,
) -> float:
    tmp = row.copy()
    tmp["depth_m"] = depth_m
    x = builder.transform(tmp)
    return float(clip01(model.predict(x)).ravel()[0])


def _predict_hazard_row(
    row: pd.DataFrame,
    model: Any,
    builder: FeatureBuilder,
    tier_index: int,
) -> float:
    x = builder.transform(row)
    pred = clip01(model.predict(x))
    if getattr(pred, "ndim", 1) == 1:
        return float(pred.ravel()[0])
    return float(pred[0, tier_index])


def counterfactual_for_location(
    frame: pd.DataFrame,
    loc_id: str,
    profile: AssumptionsProfile,
    registry: ModelRegistry,
    *,
    model_type: str = "vulnerability",
    version: Optional[str] = None,
    tier: str = "extreme",
    feature_deltas: Optional[dict[str, Any]] = None,
    d_max_m: Optional[float] = None,
) -> dict[str, Any]:
    """
    Apply controlled feature deltas and recompute prediction + GU loss.

    Default deltas (if none provided):
      - dist_hotspot_km += 1.0 (move farther from hotspot)
      - depth_m *= 0.8 (shallower) for vulnerability
    """
    if "loc_id" not in frame.columns:
        raise ValueError("frame missing loc_id")
    mask = frame["loc_id"].astype(str) == str(loc_id)
    if not mask.any():
        raise KeyError(f"loc_id not found: {loc_id}")
    base = frame.loc[mask].iloc[[0]].copy()
    tiv = float(base["tiv_kes"].iloc[0]) if "tiv_kes" in base.columns else 0.0

    deltas = dict(feature_deltas or {})
    if not deltas:
        if model_type == "vulnerability":
            deltas = {"depth_m_scale": 0.8}
        else:
            deltas = {"dist_hotspot_km_add": 1.0}

    d_max = float(d_max_m if d_max_m is not None else profile.d_max_m)
    tier_names = list(profile.tier_names)
    tier_index = tier_names.index(tier) if tier in tier_names else len(tier_names) - 1

    cf = base.copy()
    applied: dict[str, Any] = {}

    # Apply generic numeric adds / housing class swap
    if "housing_class" in deltas:
        cf["housing_class"] = deltas["housing_class"]
        applied["housing_class"] = deltas["housing_class"]
    if "dist_hotspot_km_add" in deltas and "dist_hotspot_km" in cf.columns:
        cf["dist_hotspot_km"] = float(cf["dist_hotspot_km"].iloc[0]) + float(
            deltas["dist_hotspot_km_add"]
        )
        applied["dist_hotspot_km_add"] = deltas["dist_hotspot_km_add"]
    if "dist_hotspot_km" in deltas:
        cf["dist_hotspot_km"] = float(deltas["dist_hotspot_km"])
        applied["dist_hotspot_km"] = deltas["dist_hotspot_km"]

    if model_type == "vulnerability":
        model, builder_state, entry = registry.load("vulnerability", version)
        builder = FeatureBuilder.from_state(builder_state)
        depth_col = f"depth_m_{tier}"
        base_depth = float(base[depth_col].iloc[0]) if depth_col in base.columns else 0.0
        if "depth_m_scale" in deltas:
            cf_depth = base_depth * float(deltas["depth_m_scale"])
            applied["depth_m_scale"] = deltas["depth_m_scale"]
        elif "depth_m" in deltas:
            cf_depth = float(deltas["depth_m"])
            applied["depth_m"] = deltas["depth_m"]
        elif "hazard_score_scale" in deltas:
            score_col = f"hazard_score_{tier}"
            score = float(base[score_col].iloc[0]) if score_col in base.columns else 0.0
            cf_depth = score * float(deltas["hazard_score_scale"]) * d_max
            applied["hazard_score_scale"] = deltas["hazard_score_scale"]
        else:
            cf_depth = base_depth

        base_pred = _predict_vuln_row(base, model, builder, depth_m=base_depth)
        cf_pred = _predict_vuln_row(cf, model, builder, depth_m=cf_depth)
        base_loss = base_pred * tiv
        cf_loss = cf_pred * tiv
        lineage = {
            "vuln_model_version": entry.version,
            "vuln_model_sha": entry.sha256,
        }
    else:
        model, builder_state, entry = registry.load("hazard", version)
        builder = FeatureBuilder.from_state(builder_state)
        base_pred = _predict_hazard_row(base, model, builder, tier_index)
        cf_pred = _predict_hazard_row(cf, model, builder, tier_index)
        # Map score → depth → prior-style damage approx via score*d_max depth proportionality
        # Use simple loss proxy: pred_score * tiv (honest label: prediction delta only)
        base_loss = base_pred * tiv
        cf_loss = cf_pred * tiv
        lineage = {
            "hazard_model_version": entry.version,
            "hazard_model_sha": entry.sha256,
        }

    return {
        "loc_id": str(loc_id),
        "model_type": model_type,
        "tier": tier,
        "applied_deltas": applied,
        "baseline": {
            "prediction": round(base_pred, 6),
            "loss_kes": round(base_loss, 2),
            "tiv_kes": tiv,
        },
        "counterfactual": {
            "prediction": round(cf_pred, 6),
            "loss_kes": round(cf_loss, 2),
        },
        "delta": {
            "prediction": round(cf_pred - base_pred, 6),
            "loss_kes": round(cf_loss - base_loss, 2),
        },
        "lineage": lineage,
        "disclaimer": "Counterfactual is model recompute, not engineering mitigation ROI.",
    }
