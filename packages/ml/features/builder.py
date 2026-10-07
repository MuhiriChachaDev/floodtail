"""Location-agnostic feature builder — fit on train, transform at infer."""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from packages.ml.features.schema import (
    FEATURE_SCHEMA_VERSION,
    HAZARD_NUMERIC_FEATURES,
    VULN_NUMERIC_FEATURES,
    FeatureSchema,
)


def _log1p_safe(series: pd.Series) -> pd.Series:
    return np.log1p(pd.to_numeric(series, errors="coerce").fillna(0.0).clip(lower=0.0))


def prepare_raw_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Derive log features; fill missing optional columns with NaN."""
    out = df.copy()
    if "tiv_kes" in out.columns:
        out["log_tiv"] = _log1p_safe(out["tiv_kes"])
    else:
        out["log_tiv"] = 0.0
    if "floor_area_m2" in out.columns:
        out["log_floor_area"] = _log1p_safe(out["floor_area_m2"])
    else:
        out["log_floor_area"] = 0.0
    for col in (
        "dist_hotspot_km",
        "has_hotspot_layer",
        "dist_waterway_km",
        "has_osm_waterway",
        "depth_m",
    ):
        if col not in out.columns:
            out[col] = np.nan if "dist_" in col else 0.0
    if "housing_class" not in out.columns:
        out["housing_class"] = "unknown"
    return out


class FeatureBuilder:
    """One-hot housing_class + numeric matrix. Unknown classes → zero one-hots."""

    def __init__(
        self,
        model_type: str,
        housing_classes: list[str],
        *,
        numeric_features: Optional[list[str]] = None,
        target_columns: Optional[list[str]] = None,
    ) -> None:
        self.model_type = model_type
        self.housing_classes = list(housing_classes)
        if numeric_features is not None:
            self.numeric_features = list(numeric_features)
        elif model_type == "vulnerability":
            self.numeric_features = list(VULN_NUMERIC_FEATURES)
        else:
            self.numeric_features = list(HAZARD_NUMERIC_FEATURES)
        self.target_columns = list(target_columns or [])
        self.feature_names_: list[str] = []
        self.numeric_medians_: dict[str, float] = {}
        self.fitted_ = False

    @property
    def schema(self) -> FeatureSchema:
        return FeatureSchema(
            version=FEATURE_SCHEMA_VERSION,
            model_type=self.model_type,
            numeric_features=self.numeric_features,
            categorical_features=["housing_class"],
            housing_classes=self.housing_classes,
            target_columns=self.target_columns,
        )

    def fit(self, df: pd.DataFrame) -> FeatureBuilder:
        raw = prepare_raw_columns(df)
        self.numeric_medians_ = {}
        for col in self.numeric_features:
            vals = pd.to_numeric(raw[col], errors="coerce")
            med = float(vals.median()) if vals.notna().any() else 0.0
            if not np.isfinite(med):
                med = 0.0
            self.numeric_medians_[col] = med
        self.feature_names_ = [f"housing_class__{c}" for c in self.housing_classes]
        self.feature_names_ += list(self.numeric_features)
        self.fitted_ = True
        return self

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        if not self.fitted_:
            raise RuntimeError("FeatureBuilder must be fit before transform")
        raw = prepare_raw_columns(df)
        n = len(raw)
        blocks: list[np.ndarray] = []
        classes = raw["housing_class"].astype(str)
        for c in self.housing_classes:
            blocks.append((classes == c).astype(float).to_numpy().reshape(n, 1))
        for col in self.numeric_features:
            vals = pd.to_numeric(raw[col], errors="coerce").to_numpy(dtype=float)
            fill = self.numeric_medians_.get(col, 0.0)
            vals = np.where(np.isfinite(vals), vals, fill)
            blocks.append(vals.reshape(n, 1))
        return np.hstack(blocks)

    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        return self.fit(df).transform(df)

    def to_state(self) -> dict[str, Any]:
        return {
            "model_type": self.model_type,
            "housing_classes": self.housing_classes,
            "numeric_features": self.numeric_features,
            "target_columns": self.target_columns,
            "feature_names": self.feature_names_,
            "numeric_medians": self.numeric_medians_,
            "fitted": self.fitted_,
            "schema": self.schema.to_dict(),
        }

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> FeatureBuilder:
        b = cls(
            state["model_type"],
            state["housing_classes"],
            numeric_features=state["numeric_features"],
            target_columns=state.get("target_columns") or [],
        )
        b.feature_names_ = list(state.get("feature_names") or [])
        b.numeric_medians_ = dict(state.get("numeric_medians") or {})
        b.fitted_ = bool(state.get("fitted"))
        return b
