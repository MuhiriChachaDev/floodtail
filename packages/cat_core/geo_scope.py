"""Geography helpers — keep enrichment scoped to the uploaded portfolio.

Nairobi starter rasters / hotspots must not silently drive Kisumu or Mombasa books.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import pandas as pd


# Portfolio / ingest bbox: (min_lat, min_lon, max_lat, max_lon)
BBox = tuple[float, float, float, float]


def frame_bbox(df: pd.DataFrame) -> Optional[BBox]:
    if df is None or df.empty:
        return None
    if "lat" not in df.columns or "lon" not in df.columns:
        return None
    return (
        float(df["lat"].min()),
        float(df["lon"].min()),
        float(df["lat"].max()),
        float(df["lon"].max()),
    )


def bbox_overlaps(
    a: BBox,
    b: BBox,
    *,
    pad_deg: float = 0.05,
) -> bool:
    """True if two (min_lat, min_lon, max_lat, max_lon) boxes overlap (with pad)."""
    a_min_lat, a_min_lon, a_max_lat, a_max_lon = a
    b_min_lat, b_min_lon, b_max_lat, b_max_lon = b
    return not (
        a_max_lat + pad_deg < b_min_lat
        or b_max_lat + pad_deg < a_min_lat
        or a_max_lon + pad_deg < b_min_lon
        or b_max_lon + pad_deg < a_min_lon
    )


def raster_bounds_wgs84(path: Path) -> Optional[BBox]:
    """Return raster geographic bbox as (min_lat, min_lon, max_lat, max_lon)."""
    try:
        import rasterio
    except ImportError:
        return None
    try:
        with rasterio.open(path) as ds:
            b = ds.bounds  # left, bottom, right, top in CRS units
            # Assume geographic WGS84 for Nairobi proxy TIFFs.
            return (float(b.bottom), float(b.left), float(b.top), float(b.right))
    except Exception:  # noqa: BLE001
        return None


def fraction_points_in_bbox(
    df: pd.DataFrame,
    bbox: BBox,
) -> float:
    if df is None or df.empty or "lat" not in df.columns or "lon" not in df.columns:
        return 0.0
    min_lat, min_lon, max_lat, max_lon = bbox
    inside = (
        (df["lat"] >= min_lat)
        & (df["lat"] <= max_lat)
        & (df["lon"] >= min_lon)
        & (df["lon"] <= max_lon)
    )
    return float(inside.mean())


def hotspots_near_portfolio(
    hotspots: Optional[pd.DataFrame],
    portfolio: pd.DataFrame,
    *,
    pad_deg: float = 0.45,
) -> Optional[pd.DataFrame]:
    """
    Keep hotspot rows near the portfolio bbox; return None when none overlap.

    pad_deg≈0.45° ≈ 50 km — enough for local named spots, not cross-country.
    """
    if hotspots is None or hotspots.empty:
        return None
    if "lat" not in hotspots.columns or "lon" not in hotspots.columns:
        return None
    pb = frame_bbox(portfolio)
    if pb is None:
        return None
    min_lat, min_lon, max_lat, max_lon = pb
    near = hotspots[
        (hotspots["lat"] >= min_lat - pad_deg)
        & (hotspots["lat"] <= max_lat + pad_deg)
        & (hotspots["lon"] >= min_lon - pad_deg)
        & (hotspots["lon"] <= max_lon + pad_deg)
    ].copy()
    return near if not near.empty else None


def select_overlapping_rasters(
    portfolio: pd.DataFrame,
    tier_raster_paths: dict[str, Path],
    *,
    min_fraction_inside: float = 0.05,
) -> tuple[dict[str, Path], list[str]]:
    """
    Drop rasters whose footprint does not cover the portfolio.

    Returns (filtered_paths, warnings).
    """
    warnings: list[str] = []
    pb = frame_bbox(portfolio)
    if pb is None:
        warnings.append("No portfolio lat/lon — skipping raster geography check")
        return {}, warnings

    kept: dict[str, Path] = {}
    for tier, path in tier_raster_paths.items():
        path = Path(path)
        rb = raster_bounds_wgs84(path)
        if rb is None:
            # Cannot read bounds (no rasterio / bad file) — keep path; sampler warns later.
            kept[tier] = path
            continue
        frac = fraction_points_in_bbox(portfolio, rb)
        if frac < min_fraction_inside and not bbox_overlaps(pb, rb, pad_deg=0.02):
            warnings.append(
                f"Skipped {path.name} for tier={tier}: portfolio is outside raster "
                f"extent (overlap={frac:.0%}). Include hazard_score_* in the CSV "
                "for this location, or provide city-matched rasters."
            )
            continue
        if frac < 0.5:
            warnings.append(
                f"Partial coverage for {path.name} (tier={tier}): "
                f"{frac:.0%} of locations inside raster — out-of-extent points stay 0."
            )
        kept[tier] = path

    if tier_raster_paths and not kept:
        warnings.append(
            "No hazard rasters overlap this portfolio geography — "
            "using CSV hazard_score_* values as-is (zeros if absent)."
        )
    return kept, warnings
