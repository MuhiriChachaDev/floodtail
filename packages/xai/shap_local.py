"""Local SHAP explanations for tree hazard / vulnerability models."""

from __future__ import annotations

from typing import Any, Literal, Optional

import numpy as np
import pandas as pd

from packages.ml.features.builder import FeatureBuilder
from packages.ml.registry import ModelRegistry

ModelKind = Literal["hazard", "vulnerability"]


def _tree_explainer(model: Any):
    import shap

    # MultiOutputRegressor (hazard): explain first estimator / use shap on wrapper
    base = model
    if hasattr(model, "estimators_") and model.estimators_:
        # Prefer explaining extreme / last tier estimator for local narrative
        base = model.estimators_[-1]
    return shap.TreeExplainer(base)


def _matrix_and_names(
    frame: pd.DataFrame,
    registry: ModelRegistry,
    model_type: ModelKind,
    *,
    version: Optional[str] = None,
    tier: Optional[str] = None,
) -> tuple[Any, np.ndarray, list[str], dict[str, Any]]:
    model, builder_state, entry = registry.load(model_type, version)
    builder = FeatureBuilder.from_state(builder_state)
    work = frame.copy()
    if model_type == "vulnerability":
        depth_col = f"depth_m_{tier}" if tier else None
        if depth_col and depth_col in work.columns:
            work["depth_m"] = work[depth_col]
        elif "depth_m" not in work.columns:
            # fallback: use extreme depth if present
            for c in work.columns:
                if c.startswith("depth_m_"):
                    work["depth_m"] = work[c]
                    break
            else:
                work["depth_m"] = 0.0
    x = builder.transform(work)
    names = list(builder.feature_names_)
    lineage = {
        "model_type": model_type,
        "model_version": entry.version,
        "model_sha": entry.sha256,
        "feature_schema_version": entry.feature_schema.get("version"),
    }
    return model, x, names, lineage


def local_shap_for_row(
    frame: pd.DataFrame,
    loc_id: str,
    registry: ModelRegistry,
    *,
    model_type: ModelKind = "hazard",
    version: Optional[str] = None,
    tier: str = "extreme",
    top_k: int = 8,
) -> dict[str, Any]:
    """
    SHAP values for a single location.
    Explains model prediction — not flood physics.
    """
    if "loc_id" not in frame.columns:
        raise ValueError("frame missing loc_id")
    mask = frame["loc_id"].astype(str) == str(loc_id)
    if not mask.any():
        raise KeyError(f"loc_id not found: {loc_id}")
    row = frame.loc[mask].iloc[[0]]

    model, x, names, lineage = _matrix_and_names(
        row, registry, model_type, version=version, tier=tier
    )
    explainer = _tree_explainer(model)
    sv = explainer.shap_values(x)
    # Handle list (multiclass) or 2d
    if isinstance(sv, list):
        vals = np.asarray(sv[-1])[0]
    else:
        arr = np.asarray(sv)
        vals = arr[0] if arr.ndim == 2 else arr

    pairs = sorted(
        (
            {"feature": names[i], "shap": float(vals[i]), "value": float(x[0, i])}
            for i in range(min(len(names), len(vals)))
        ),
        key=lambda d: abs(d["shap"]),
        reverse=True,
    )[:top_k]

    # Prediction for honesty
    if hasattr(model, "estimators_"):
        pred = float(np.asarray(model.predict(x)).ravel()[-1])
    else:
        pred = float(np.asarray(model.predict(x)).ravel()[0])

    return {
        "loc_id": str(loc_id),
        "model_type": model_type,
        "tier": tier if model_type == "vulnerability" else None,
        "prediction": pred,
        "top_features": pairs,
        "lineage": lineage,
        "disclaimer": "SHAP explains model predictions, not real flood physics.",
    }
