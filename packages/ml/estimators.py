"""Model factory — prefer XGBoost, fall back to sklearn HistGradientBoosting."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor


def _xgb_available() -> bool:
    try:
        import xgboost  # noqa: F401

        return True
    except Exception:
        return False


def make_regressor(params: dict[str, Any] | None = None, *, random_state: int = 42):
    params = dict(params or {})
    if _xgb_available():
        from xgboost import XGBRegressor

        defaults = {
            "n_estimators": 80,
            "max_depth": 4,
            "learning_rate": 0.08,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "min_child_weight": 2,
            "objective": "reg:squarederror",
            "n_jobs": 2,
            "random_state": random_state,
            "verbosity": 0,
        }
        defaults.update(params)
        return XGBRegressor(**defaults)

    defaults = {
        "max_depth": 4,
        "learning_rate": 0.08,
        "max_iter": 120,
        "random_state": random_state,
    }
    # map xgb-ish names
    if "n_estimators" in params:
        defaults["max_iter"] = int(params.pop("n_estimators"))
    params.pop("subsample", None)
    params.pop("colsample_bytree", None)
    params.pop("min_child_weight", None)
    params.pop("objective", None)
    params.pop("n_jobs", None)
    params.pop("verbosity", None)
    defaults.update(params)
    return HistGradientBoostingRegressor(**defaults)


def make_multioutput_regressor(params: dict[str, Any] | None = None, *, random_state: int = 42):
    base = make_regressor(params, random_state=random_state)
    return MultiOutputRegressor(base)


def clip01(arr: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(arr, dtype=float), 0.0, 1.0)


DEFAULT_SEARCH_SPACE = {
    "n_estimators": [40, 80, 120],
    "max_depth": [3, 4, 5],
    "learning_rate": [0.05, 0.08, 0.12],
    "subsample": [0.8, 0.9, 1.0],
    "min_child_weight": [1, 2, 4],
}
