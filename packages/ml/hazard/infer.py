"""Hazard inference — load registry artifact, transform, predict, clip."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from packages.cat_core.assumptions import AssumptionsProfile
from packages.cat_core.exposure import HAZARD_SCORE_PREFIX
from packages.ml.estimators import clip01
from packages.ml.features.builder import FeatureBuilder
from packages.ml.registry import ModelRegistry


def predict_hazard(
    frame: pd.DataFrame,
    profile: AssumptionsProfile,
    registry: ModelRegistry,
    *,
    version: Optional[str] = None,
) -> tuple[pd.DataFrame, dict]:
    model, builder_state, entry = registry.load("hazard", version)
    builder = FeatureBuilder.from_state(builder_state)
    x = builder.transform(frame)
    pred = clip01(model.predict(x))
    out = frame.copy()
    lineage = {
        "hazard_model_version": entry.version,
        "hazard_model_sha": entry.sha256,
        "feature_schema_version": entry.feature_schema.get("version"),
    }
    # Keep baseline proxy scores if present
    for i, tier in enumerate(profile.tier_names):
        src = f"{HAZARD_SCORE_PREFIX}{tier}"
        if src in out.columns:
            out[f"hazard_score_baseline_{tier}"] = out[src]
        col = f"{HAZARD_SCORE_PREFIX}{tier}"
        if pred.ndim == 1:
            out[col] = float(pred[0]) if len(profile.tier_names) == 1 else pred
        else:
            out[col] = pred[:, i]
        out[f"hazard_score_pred_{tier}"] = out[col]
    return out, lineage
