"""Flexible enrichment: hotspots (haversine) + optional OSM waterways."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from packages.ml.geo import add_nearest_hotspot_distance
from packages.ml.osm import add_osm_waterway_distance


def enrich_frame(
    df: pd.DataFrame,
    *,
    hotspots: Optional[pd.DataFrame] = None,
    use_osm: bool = False,
    overpass_url: str = "https://overpass-api.de/api/interpreter",
    waterway_points: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Attach geo enrichment columns. Safe for any location:
    - missing hotspot layer → NaN distances + flags 0
    - OSM disabled/down → NaN + flag 0
    """
    out = add_nearest_hotspot_distance(df, hotspots)
    out = add_osm_waterway_distance(
        out,
        enabled=use_osm,
        overpass_url=overpass_url,
        waterway_points=waterway_points,
    )
    return out
