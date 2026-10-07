"""Optional OpenStreetMap Overpass client for waterway enrichment."""

from __future__ import annotations

import logging
from typing import Optional

import httpx
import numpy as np
import pandas as pd

from packages.ml.geo import nearest_distance_km

logger = logging.getLogger(__name__)

DEFAULT_OVERPASS = "https://overpass-api.de/api/interpreter"


def fetch_waterway_points(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    *,
    overpass_url: str = DEFAULT_OVERPASS,
    timeout_s: float = 25.0,
) -> pd.DataFrame:
    """
    Query OSM waterways in bbox via Overpass. Returns points (lat, lon).
    Empty frame on failure — callers must degrade gracefully.
    """
    query = f"""
    [out:json][timeout:20];
    (
      way["waterway"~"river|stream|drain|canal|ditch"]({min_lat},{min_lon},{max_lat},{max_lon});
      node["waterway"~"river|stream|drain|canal|ditch"]({min_lat},{min_lon},{max_lat},{max_lon});
    );
    out center 200;
    """
    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.post(overpass_url, data={"data": query})
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("OSM Overpass unavailable: %s", exc)
        return pd.DataFrame(columns=["lat", "lon"])

    rows: list[dict[str, float]] = []
    for el in payload.get("elements", []):
        if "lat" in el and "lon" in el:
            rows.append({"lat": float(el["lat"]), "lon": float(el["lon"])})
        elif "center" in el:
            c = el["center"]
            rows.append({"lat": float(c["lat"]), "lon": float(c["lon"])})
    if not rows:
        return pd.DataFrame(columns=["lat", "lon"])
    return pd.DataFrame(rows).drop_duplicates()


def add_osm_waterway_distance(
    df: pd.DataFrame,
    *,
    enabled: bool = False,
    overpass_url: str = DEFAULT_OVERPASS,
    col: str = "dist_waterway_km",
    flag_col: str = "has_osm_waterway",
    waterway_points: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Add distance to nearest OSM waterway.
    If disabled / failed: NaN + flag=0 (location-flexible degrade).
    """
    out = df.copy()
    if not enabled:
        out[col] = np.nan
        out[flag_col] = 0
        return out

    points = waterway_points
    if points is None:
        min_lat, max_lat = float(out["lat"].min()), float(out["lat"].max())
        min_lon, max_lon = float(out["lon"].min()), float(out["lon"].max())
        # pad bbox slightly
        pad = 0.02
        points = fetch_waterway_points(
            min_lat - pad,
            min_lon - pad,
            max_lat + pad,
            max_lon + pad,
            overpass_url=overpass_url,
        )

    if points is None or points.empty:
        out[col] = np.nan
        out[flag_col] = 0
        return out

    out[col] = nearest_distance_km(
        out["lat"].to_numpy(),
        out["lon"].to_numpy(),
        points["lat"].to_numpy(),
        points["lon"].to_numpy(),
    )
    out[flag_col] = 1
    return out
