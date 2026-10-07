"""Hazard model: data → features → train → evaluate → optional tune → register."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import numpy as np
from sklearn.model_selection import ParameterSampler

from packages.cat_core.assumptions import AssumptionsProfile
from packages.ml.data.labels import build_hazard_labels
from packages.ml.data.loaders import load_training_exposure, train_val_test_split
from packages.ml.estimators import DEFAULT_SEARCH_SPACE, clip01, make_multioutput_regressor
from packages.ml.evaluate import passes_threshold, regression_report
from packages.ml.features.builder import FeatureBuilder
from packages.ml.registry import ModelRegistry, RegistryEntry


def _xy(frame, builder: FeatureBuilder, target_cols: list[str]):
    x = builder.transform(frame)
    y = frame[target_cols].to_numpy(dtype=float)
    return x, y


def train_hazard_model(
    exposure_path: Path,
    profile: AssumptionsProfile,
    registry: ModelRegistry,
    *,
    hotspots_path: Optional[Path] = None,
    use_osm: bool = False,
    tune: bool = True,
    n_iter: int = 8,
    seed: int = 42,
    max_mae: float = 0.35,
    overpass_url: str = "https://overpass-api.de/api/interpreter",
    pin: bool = True,
) -> RegistryEntry:
    frame, data_manifest = load_training_exposure(
        exposure_path,
        profile,
        hotspots_path=hotspots_path,
        location_label="training",
        use_osm=use_osm,
        overpass_url=overpass_url,
    )
    frame, label_meta = build_hazard_labels(frame, profile)
    target_cols = label_meta["target_columns"]

    train, val, test, split_meta = train_val_test_split(frame, seed=seed)
    builder = FeatureBuilder(
        "hazard",
        profile.housing_classes,
        target_columns=target_cols,
    )
    builder.fit(train)

    x_train, y_train = _xy(train, builder, target_cols)
    x_val, y_val = _xy(val, builder, target_cols)
    x_test, y_test = _xy(test, builder, target_cols)

    best_params: dict[str, Any] = {
        "n_estimators": 80,
        "max_depth": 4,
        "learning_rate": 0.08,
        "subsample": 0.9,
        "min_child_weight": 2,
    }
    tuning_enabled = bool(tune)

    if tune and len(val) >= 5:
        best_score = float("inf")
        for params in ParameterSampler(DEFAULT_SEARCH_SPACE, n_iter=n_iter, random_state=seed):
            model = make_multioutput_regressor(dict(params), random_state=seed)
            model.fit(x_train, y_train)
            pred = clip01(model.predict(x_val))
            mae = float(np.mean(np.abs(y_val - pred)))
            if mae < best_score:
                best_score = mae
                best_params = dict(params)

    model = make_multioutput_regressor(best_params, random_state=seed)
    # refit on train+val for final model (test held out)
    x_fit = np.vstack([x_train, x_val]) if len(val) else x_train
    y_fit = np.vstack([y_train, y_val]) if len(val) else y_train
    model.fit(x_fit, y_fit)

    test_pred = clip01(model.predict(x_test)) if len(test) else clip01(model.predict(x_train))
    y_eval = y_test if len(test) else y_train
    metrics = regression_report(y_eval, test_pred, target_names=target_cols)
    metrics["split"] = split_meta
    metrics["threshold_max_mae"] = max_mae
    metrics["passed_gate"] = passes_threshold(metrics, max_mae=max_mae)
    if not metrics["passed_gate"]:
        raise RuntimeError(
            f"Hazard model failed MAE gate: mae={metrics['mae']:.4f} > {max_mae}"
        )

    # baseline = predict mean train labels
    baseline = np.repeat(y_train.mean(axis=0, keepdims=True), len(y_eval), axis=0)
    metrics["baseline_mae"] = float(np.mean(np.abs(y_eval - baseline)))

    training_card = {
        "model_type": "hazard",
        "purpose": "Predict per-tier pluvial susceptibility from flexible exposure + geo enrichments",
        "data_manifest": data_manifest,
        "label_meta": label_meta,
        "feature_schema_version": builder.schema.version,
        "tuning_enabled": tuning_enabled,
        "limitations": [
            "Labels are synthetic proxy scores (+ optional hotspot uplift), not gauges",
            "Location-flexible features; OSM enrichment optional and may be absent",
        ],
    }
    params = {
        "best_params": best_params,
        "tuning_enabled": tuning_enabled,
        "n_iter": n_iter if tune else 0,
        "seed": seed,
        "backend": type(model.estimators_[0]).__name__
        if hasattr(model, "estimators_")
        else type(model).__name__,
    }

    return registry.register(
        "hazard",
        model,
        feature_builder_state=builder.to_state(),
        metrics=metrics,
        params=params,
        feature_schema=builder.schema.to_dict(),
        training_card=training_card,
        pin=pin,
    )
