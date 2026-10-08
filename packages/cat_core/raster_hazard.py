"""Optional GeoTIFF hazard sampling for portfolios missing hazard_score_* columns.

Uses rasterio when installed (`pip install floodtail[geo]`). Without rasterio,
returns the frame unchanged with a warning — never invents scores.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from packages.cat_core.exposure import HAZARD_SCORE_PREFIX
from packages.cat_core.geo_scope import select_overlapping_rasters


def default_tier_raster_paths(data_dir: Path, tier_names: list[str]) -> dict[str, Path]:
    """Map tier → Nairobi_Data/nairobi_pluvial_proxy_{tier}.tif when present.

    These are the *starter* Nairobi proxy rasters — callers must gate by geography
    (see ``fill_hazard_from_data_dir``) so non-Nairobi portfolios are not sampled.
    """
    out: dict[str, Path] = {}
    for tier in tier_names:
        path = data_dir / f"nairobi_pluvial_proxy_{tier}.tif"
        if path.exists():
            out[tier] = path
    return out


def _sample_raster(path: Path, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    import rasterio
    from rasterio.sample import sample_gen

    values = np.zeros(len(lats), dtype=float)
    with rasterio.open(path) as ds:
        coords = list(zip(lons.tolist(), lats.tolist()))  # (x, y) = (lon, lat)
        for i, sample in enumerate(sample_gen(ds, coords)):
            v = sample[0] if sample is not None and len(sample) else 0.0
            if v is None or (isinstance(v, float) and np.isnan(v)):
                values[i] = 0.0
            else:
                values[i] = float(v)
    return np.clip(values, 0.0, 1.0)


def sample_hazard_rasters(
    df: pd.DataFrame,
    tier_raster_paths: dict[str, Path],
    *,
    only_missing_or_zero: bool = True,
    score_prefix: str = HAZARD_SCORE_PREFIX,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Sample GeoTIFF susceptibility into hazard_score_{tier}.

    Parameters
    ----------
    only_missing_or_zero
        If True, only overwrite rows where the score column is missing or all-zero.
        If False, always overwrite from rasters for listed tiers.
    """
    warnings: list[str] = []
    if not tier_raster_paths:
        warnings.append("No hazard rasters provided — scores unchanged")
        return df.copy(), warnings

    try:
        import rasterio  # noqa: F401
    except ImportError:
        warnings.append(
            "rasterio not installed — cannot sample GeoTIFFs "
            "(pip install floodtail[geo]). Scores unchanged."
        )
        return df.copy(), warnings

    out = df.copy()
    if "lat" not in out.columns or "lon" not in out.columns:
        warnings.append("lat/lon required for raster sampling — skipped")
        return out, warnings

    lats = out["lat"].astype(float).to_numpy()
    lons = out["lon"].astype(float).to_numpy()

    for tier, path in tier_raster_paths.items():
        col = f"{score_prefix}{tier}"
        path = Path(path)
        if not path.exists():
            warnings.append(f"raster missing for tier={tier}: {path}")
            continue

        if only_missing_or_zero and col in out.columns:
            existing = out[col].astype(float)
            if existing.to_numpy().sum() > 0:
                warnings.append(f"kept existing non-zero {col} (skip raster)")
                continue

        try:
            sampled = _sample_raster(path, lats, lons)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"raster sample failed for {tier}: {exc}")
            continue

        out[col] = sampled
        warnings.append(
            f"sampled {col} from {path.name} "
            f"(mean={float(sampled.mean()):.4f}, max={float(sampled.max()):.4f})"
        )

    return out, warnings


def fill_hazard_from_data_dir(
    df: pd.DataFrame,
    data_dir: Path,
    tier_names: list[str],
    *,
    only_missing_or_zero: bool = True,
    require_overlap: bool = True,
) -> tuple[pd.DataFrame, list[str]]:
    """Sample starter Nairobi proxy TIFFs only when they cover this portfolio.

    For Kisumu / Mombasa / other uploads outside the Nairobi raster footprint,
    scores are left as CSV values (or zeros) with an explicit warning — never
    silently stamped from an unrelated city's GeoTIFF.
    """
    paths = default_tier_raster_paths(Path(data_dir), tier_names)
    if not paths:
        return df.copy(), ["No nairobi_pluvial_proxy_*.tif found under data_dir"]

    warnings: list[str] = []
    if require_overlap:
        paths, geo_warns = select_overlapping_rasters(df, paths)
        warnings.extend(geo_warns)
        if not paths:
            return df.copy(), warnings

    out, sample_warns = sample_hazard_rasters(
        df, paths, only_missing_or_zero=only_missing_or_zero
    )
    return out, warnings + sample_warns
