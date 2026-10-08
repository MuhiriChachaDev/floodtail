"""LangGraph agent state for the FLOODTAIL run pipeline."""

from __future__ import annotations

from typing import Any, Optional, TypedDict

import pandas as pd

from packages.cat_core.assumptions import AssumptionsProfile
from packages.cat_core.types import (
    AgentResult,
    InsightPackage,
    MetricsPayload,
    StageStatus,
)
from packages.ml.registry import ModelRegistry


class AgentGraphState(TypedDict, total=False):
    """Mutable graph state passed between nodes."""

    # identity
    run_id: str
    portfolio_id: str
    tenant_id: str
    location_label: str
    actor: str

    # config
    profile: AssumptionsProfile
    use_ml: bool
    hazard_model_version: Optional[str]
    vuln_model_version: Optional[str]
    enable_freetext: bool
    freetext: Optional[str]
    require_human_gate_1: bool
    features_approved: bool
    use_osm: bool
    overpass_url: str
    hotspots: Optional[pd.DataFrame]
    registry: Optional[ModelRegistry]
    ollama_host: str
    ollama_model: str
    force_ollama_down: bool  # tests

    # working data
    frame: pd.DataFrame
    warnings: list[str]
    stages: list[AgentResult]
    metrics: Optional[MetricsPayload]
    allowlist: dict[str, Any]
    insight: Optional[InsightPackage]
    narrative: str
    query_answer: str
    audit_events: list[dict[str, Any]]

    # control
    status: str  # RUNNING | COMPLETED | FAILED | REVIEW_REQUIRED
    halt: bool
    error: Optional[str]
    ollama_degraded: bool


def new_state(**kwargs: Any) -> AgentGraphState:
    base: AgentGraphState = {
        "warnings": [],
        "stages": [],
        "allowlist": {},
        "audit_events": [],
        "status": "RUNNING",
        "halt": False,
        "error": None,
        "ollama_degraded": False,
        "features_approved": True,
        "enable_freetext": False,
        "freetext": None,
        "require_human_gate_1": False,
        "use_ml": True,
        "use_osm": False,
        "overpass_url": "https://overpass-api.de/api/interpreter",
        "narrative": "",
        "query_answer": "",
        "force_ollama_down": False,
        "tenant_id": "default",
        "actor": "anonymous",
    }
    base.update(kwargs)  # type: ignore[typeddict-item]
    return base


def append_stage(
    state: AgentGraphState,
    *,
    stage: str,
    status: StageStatus,
    message: str = "",
    warnings: Optional[list[str]] = None,
    data: Optional[dict[str, Any]] = None,
    critical: bool = False,
) -> AgentGraphState:
    stages = list(state.get("stages") or [])
    stages.append(
        AgentResult(
            stage=stage,
            status=status,
            message=message,
            warnings=list(warnings or []),
            data=dict(data or {}),
            critical=critical,
        )
    )
    out = dict(state)
    out["stages"] = stages
    if warnings:
        out["warnings"] = list(state.get("warnings") or []) + list(warnings)
    if critical and status == StageStatus.FAILED:
        out["halt"] = True
        out["status"] = "FAILED"
        out["error"] = message
    return out  # type: ignore[return-value]
