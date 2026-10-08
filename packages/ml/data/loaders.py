"""Flexible data loaders — any exposure CSV + optional hotspot layer."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from packages.cat_core.assumptions import AssumptionsProfile
from packages.cat_core.exposure import load_exposure_csv, validate_and_normalize
from packages.ml.enrich import enrich_frame


def load_hotspots(path: Optional[Path]) -> Optional[pd.DataFrame]:
    if path is None or not Path(path).exists():
        return None
    hs = pd.read_csv(path)
    if "lat" not in hs.columns or "lon" not in hs.columns:
        return None
    return hs


def load_training_exposure(
    exposure_path: Path,
    profile: AssumptionsProfile,
    *,
    hotspots_path: Optional[Path] = None,
    location_label: str = "training",
    use_osm: bool = False,
    overpass_url: str = "https://overpass-api.de/api/interpreter",
) -> tuple[pd.DataFrame, dict]:
    raw = load_exposure_csv(Path(exposure_path))
    frame, stats, warnings = validate_and_normalize(
        raw,
        profile,
        location_label=location_label,
        source=str(exposure_path),
        force_synthetic=True,
    )
    hotspots = load_hotspots(hotspots_path)
    frame = enrich_frame(
        frame,
        hotspots=hotspots,
        use_osm=use_osm,
        overpass_url=overpass_url,
    )
    manifest = {
        "n_rows": int(len(frame)),
        "location_label": location_label,
        "source": str(exposure_path),
        "hotspots_path": str(hotspots_path) if hotspots_path else None,
        "use_osm": use_osm,
        "warnings": warnings,
        "ingest_stats": stats.model_dump(),
    }
    return frame, manifest


def train_val_test_split(
    df: pd.DataFrame,
    *,
    seed: int = 42,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
    id_col: str = "loc_id",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """
    Split by unique loc_id to reduce leakage (location-grouped).
    Flexible: works for any id column present; else falls back to row index.
    """
    rng = np.random.default_rng(seed)
    if id_col in df.columns:
        ids = df[id_col].astype(str).unique()
    else:
        ids = df.index.astype(str).to_numpy()
        df = df.copy()
        df[id_col] = ids

    ids = np.array(sorted(ids))
    rng.shuffle(ids)
    n = len(ids)
    n_train = int(n * train_frac)
    n_val = int(n * val_frac)
    train_ids = set(ids[:n_train])
    val_ids = set(ids[n_train : n_train + n_val])
    test_ids = set(ids[n_train + n_val :])

    key = df[id_col].astype(str)
    train = df[key.isin(train_ids)].copy()
    val = df[key.isin(val_ids)].copy()
    test = df[key.isin(test_ids)].copy()

    # Ensure no id overlap
    assert train_ids.isdisjoint(val_ids)
    assert train_ids.isdisjoint(test_ids)
    assert val_ids.isdisjoint(test_ids)

    meta = {
        "seed": seed,
        "n_train": len(train),
        "n_val": len(val),
        "n_test": len(test),
        "n_train_ids": len(train_ids),
        "n_val_ids": len(val_ids),
        "n_test_ids": len(test_ids),
    }
    return train, val, test, meta
