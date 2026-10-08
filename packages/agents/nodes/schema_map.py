"""Stage 0 — Ingest & SchemaMap (critical)."""

from __future__ import annotations

from packages.agents.state import AgentGraphState, append_stage
from packages.agents.tools.portfolio_tools import schema_map
from packages.cat_core.types import StageStatus


def node_schema_map(state: AgentGraphState) -> AgentGraphState:
    frame = state.get("frame")
    if frame is None or getattr(frame, "empty", True):
        return append_stage(
            state,
            stage="schema_map",
            status=StageStatus.FAILED,
            message="Empty portfolio frame",
            critical=True,
        )
    mapped, mapping, warnings = schema_map(frame)
    out = dict(state)
    out["frame"] = mapped
    out = append_stage(
        out,  # type: ignore[arg-type]
        stage="schema_map",
        status=StageStatus.OK,
        message=f"Mapped {len(mapping)} canonical columns",
        warnings=warnings,
        data={"column_mapping": mapping},
        critical=True,
    )
    return out
