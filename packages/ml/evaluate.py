"""Shared evaluation metrics."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def regression_report(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    *,
    target_names: list[str] | None = None,
) -> dict[str, Any]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if y_true.ndim == 1:
        y_true = y_true.reshape(-1, 1)
        y_pred = y_pred.reshape(-1, 1)
    names = target_names or [f"t{i}" for i in range(y_true.shape[1])]
    per_target: dict[str, Any] = {}
    for i, name in enumerate(names):
        yt, yp = y_true[:, i], y_pred[:, i]
        per_target[name] = {
            "mae": float(mean_absolute_error(yt, yp)),
            "rmse": float(np.sqrt(mean_squared_error(yt, yp))),
            "r2": float(r2_score(yt, yp)) if len(np.unique(yt)) > 1 else 0.0,
        }
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    return {
        "mae": mae,
        "rmse": rmse,
        "r2_macro": float(np.mean([per_target[n]["r2"] for n in names])),
        "per_target": per_target,
        "n": int(y_true.shape[0]),
    }


def passes_threshold(metrics: dict[str, Any], *, max_mae: float = 0.35) -> bool:
    """Hackathon-lenient gate — proxy labels are noisy."""
    return float(metrics.get("mae", 999.0)) <= max_mae
