"""Stage 1b — geo enrichment (hotspot / optional OSM)."""

from __future__ import annotations

import numpy as np

from packages.agents.state import AgentGraphState, append_stage
from packages.cat_core.types import StageStatus
from packages.ml.enrich import enrich_frame


def node_enrich(state: AgentGraphState) -> AgentGraphState:
    requested_osm = bool(state.get("use_osm"))
    work = enrich_frame(
        state["frame"],
        hotspots=state.get("hotspots"),
        use_osm=requested_osm,
        overpass_url=state.get("overpass_url") or "https://overpass-api.de/api/interpreter",
    )
    has_hotspot = (
        int(work["has_hotspot_layer"].max()) if "has_hotspot_layer" in work.columns else 0
    )
    has_osm = int(work["has_osm_waterway"].max()) if "has_osm_waterway" in work.columns else 0
    osm_dist = None
    if has_osm and "dist_waterway_km" in work.columns:
        vals = work["dist_waterway_km"].astype(float)
        if vals.notna().any():
            osm_dist = round(float(np.nanmedian(vals)), 4)

    warnings: list[str] = []
    if requested_osm and not has_osm:
        warnings.append(
            "OSM waterway enrichment requested but Overpass returned no data; "
            "continuing with hotspot/proxy features only."
        )
    msg = "Geo enrichment applied"
    if requested_osm and has_osm:
        msg = "Geo enrichment applied (hotspots + OSM waterways)"
    elif requested_osm:
        msg = "Geo enrichment applied (hotspots; OSM unavailable — degraded)"

    out = dict(state)
    out["frame"] = work
    return append_stage(
        out,  # type: ignore[arg-type]
        stage="enrich",
        status=StageStatus.OK,
        message=msg,
        warnings=warnings,
        data={
            "has_hotspot_layer": has_hotspot,
            "osm_requested": requested_osm,
            "has_osm_waterway": has_osm,
            "median_dist_waterway_km": osm_dist,
        },
        critical=False,
    )
