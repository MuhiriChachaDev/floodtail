"""Stage 1b — geo enrichment (hotspot / optional OSM)."""

from __future__ import annotations

from packages.agents.state import AgentGraphState, append_stage
from packages.cat_core.types import StageStatus
from packages.ml.enrich import enrich_frame


def node_enrich(state: AgentGraphState) -> AgentGraphState:
    work = enrich_frame(
        state["frame"],
        hotspots=state.get("hotspots"),
        use_osm=bool(state.get("use_osm")),
        overpass_url=state.get("overpass_url") or "https://overpass-api.de/api/interpreter",
    )
    out = dict(state)
    out["frame"] = work
    return append_stage(
        out,  # type: ignore[arg-type]
        stage="enrich",
        status=StageStatus.OK,
        message="Geo enrichment applied",
        data={
            "has_hotspot_layer": int(work["has_hotspot_layer"].iloc[0])
            if "has_hotspot_layer" in work.columns
            else 0,
        },
        critical=False,
    )
