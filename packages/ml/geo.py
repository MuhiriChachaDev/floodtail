"""Location-agnostic geo helpers (haversine distances)."""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
import pandas as pd


def haversine_km(
    lat1: np.ndarray | float,
    lon1: np.ndarray | float,
    lat2: np.ndarray | float,
    lon2: np.ndarray | float,
) -> np.ndarray:
    """Great-circle distance in km. Broadcasts like numpy."""
    r = 6371.0
    lat1_r = np.radians(lat1)
    lon1_r = np.radians(lon1)
    lat2_r = np.radians(lat2)
    lon2_r = np.radians(lon2)
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlon / 2.0) ** 2
    return 2.0 * r * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def nearest_distance_km(
    lat: Sequence[float] | np.ndarray,
    lon: Sequence[float] | np.ndarray,
    ref_lat: Sequence[float] | np.ndarray,
    ref_lon: Sequence[float] | np.ndarray,
) -> np.ndarray:
    """For each (lat,lon), distance to nearest reference point (km)."""
    lat_a = np.asarray(lat, dtype=float).reshape(-1, 1)
    lon_a = np.asarray(lon, dtype=float).reshape(-1, 1)
    ref_lat_a = np.asarray(ref_lat, dtype=float).reshape(1, -1)
    ref_lon_a = np.asarray(ref_lon, dtype=float).reshape(1, -1)
    if ref_lat_a.size == 0:
        return np.full(lat_a.shape[0], np.nan, dtype=float)
    dist = haversine_km(lat_a, lon_a, ref_lat_a, ref_lon_a)
    return dist.min(axis=1)


def add_nearest_hotspot_distance(
    df: pd.DataFrame,
    hotspots: Optional[pd.DataFrame],
    *,
    col: str = "dist_hotspot_km",
    flag_col: str = "has_hotspot_layer",
) -> pd.DataFrame:
    """
    Add haversine distance to nearest hotspot.
    If no hotspot layer: col=NaN, flag=0 (flexible — no city hardcode).
    """
    out = df.copy()
    if (
        hotspots is None
        or hotspots.empty
        or "lat" not in hotspots.columns
        or "lon" not in hotspots.columns
    ):
        out[col] = np.nan
        out[flag_col] = 0
        return out
    out[col] = nearest_distance_km(
        out["lat"].to_numpy(),
        out["lon"].to_numpy(),
        hotspots["lat"].to_numpy(),
        hotspots["lon"].to_numpy(),
    )
    out[flag_col] = 1
    return out
