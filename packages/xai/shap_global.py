"""Global mean-|SHAP| drivers for tree models."""

from __future__ import annotations

from typing import Any, Literal, Optional

import numpy as np
import pandas as pd

from packages.ml.features.builder import FeatureBuilder
from packages.ml.registry import ModelRegistry
from packages.xai.shap_local import _tree_explainer

ModelKind = Literal["hazard", "vulnerability"]


def global_shap(
    frame: pd.DataFrame,
    registry: ModelRegistry,
    *,
    model_type: ModelKind = "hazard",
    version: Optional[str] = None,
    tier: str = "extreme",
    sample_size: int = 100,
    top_k: int = 12,
    seed: int = 42,
) -> dict[str, Any]:
    """
    Mean absolute SHAP across a sample of locations.
    """
    if frame.empty:
        raise ValueError("empty frame")
    n = min(sample_size, len(frame))
    sample = frame.sample(n=n, random_state=seed) if len(frame) > n else frame

    model, builder_state, entry = registry.load(model_type, version)
    builder = FeatureBuilder.from_state(builder_state)
    work = sample.copy()
    if model_type == "vulnerability":
        depth_col = f"depth_m_{tier}"
        if depth_col in work.columns:
            work["depth_m"] = work[depth_col]
        elif "depth_m" not in work.columns:
            work["depth_m"] = 0.0

    x = builder.transform(work)
    names = list(builder.feature_names_)
    explainer = _tree_explainer(model)
    sv = explainer.shap_values(x)
    if isinstance(sv, list):
        arr = np.asarray(sv[-1])
    else:
        arr = np.asarray(sv)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    mean_abs = np.mean(np.abs(arr), axis=0)
    ranked = sorted(
        (
            {"feature": names[i], "mean_abs_shap": float(mean_abs[i])}
            for i in range(min(len(names), len(mean_abs)))
        ),
        key=lambda d: d["mean_abs_shap"],
        reverse=True,
    )[:top_k]

    # Deterministic concentration context if present on frame
    class_share: list[dict[str, Any]] = []
    if "housing_class" in frame.columns and any(
        c.startswith("loss_kes_") for c in frame.columns
    ):
        loss_col = "loss_kes_extreme" if "loss_kes_extreme" in frame.columns else None
        if loss_col is None:
            loss_cols = [c for c in frame.columns if c.startswith("loss_kes_")]
            loss_col = loss_cols[-1] if loss_cols else None
        if loss_col:
            g = frame.groupby("housing_class")[loss_col].sum()
            total = float(g.sum()) or 1.0
            class_share = [
                {
                    "housing_class": str(k),
                    "loss_share_pct": round(100.0 * float(v) / total, 2),
                }
                for k, v in g.sort_values(ascending=False).items()
            ]

    return {
        "model_type": model_type,
        "sample_size": int(n),
        "tier": tier if model_type == "vulnerability" else None,
        "drivers": ranked,
        "housing_class_loss_share": class_share,
        "lineage": {
            "model_version": entry.version,
            "model_sha": entry.sha256,
            "feature_schema_version": entry.feature_schema.get("version"),
        },
        "disclaimer": "Global SHAP reflects synthetic/proxy label process, not hydrology.",
    }
