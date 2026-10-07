"""LangGraph state machine for FLOODTAIL run pipeline (flowchart stages 0–9)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

import pandas as pd
from langgraph.graph import END, START, StateGraph

from packages.agents.nodes.dq_pii import node_dq_pii
from packages.agents.nodes.enrich import node_enrich
from packages.agents.nodes.freetext import node_freetext
from packages.agents.nodes.gates import node_governance, node_human_gate_1
from packages.agents.nodes.insight import node_insight
from packages.agents.nodes.invoke_math import node_invoke_math, node_xai_stub
from packages.agents.nodes.invoke_ml import (
    capture_baseline_scores,
    node_depth_map,
    node_predict_hazard,
    node_predict_vulnerability,
)
from packages.agents.nodes.schema_map import node_schema_map
from packages.agents.state import AgentGraphState, new_state
from packages.cat_core.assumptions import AssumptionsProfile
from packages.cat_core.types import InsightPackage, MetricsPayload
from packages.ml.registry import ModelRegistry


def _route_after(state: AgentGraphState) -> str:
    """Critical halt: route to END when halt flag set."""
    if state.get("halt"):
        return "halted"
    return "continue"


def _wrap(fn: Callable[[AgentGraphState], AgentGraphState]) -> Callable[[AgentGraphState], AgentGraphState]:
    """Skip node body if already halted."""

    def _inner(state: AgentGraphState) -> AgentGraphState:
        if state.get("halt"):
            return state
        return fn(state)

    return _inner


def _node_baseline(state: AgentGraphState) -> AgentGraphState:
    return capture_baseline_scores(state)


def build_agent_graph():
    """Compile the LangGraph pipeline with critical-halt edges."""
    g: StateGraph = StateGraph(AgentGraphState)

    g.add_node("schema_map", _wrap(node_schema_map))
    g.add_node("dq_pii", _wrap(node_dq_pii))
    g.add_node("enrich", _wrap(node_enrich))
    g.add_node("freetext", _wrap(node_freetext))
    g.add_node("gate1", _wrap(node_human_gate_1))
    g.add_node("baseline", _wrap(_node_baseline))
    g.add_node("hazard", _wrap(node_predict_hazard))
    g.add_node("depth", _wrap(node_depth_map))
    g.add_node("vuln", _wrap(node_predict_vulnerability))
    g.add_node("math", _wrap(node_invoke_math))
    g.add_node("xai", _wrap(node_xai_stub))
    g.add_node("insight", _wrap(node_insight))
    g.add_node("governance", _wrap(node_governance))

    g.add_edge(START, "schema_map")
    g.add_conditional_edges(
        "schema_map", _route_after, {"halted": END, "continue": "dq_pii"}
    )
    g.add_conditional_edges(
        "dq_pii", _route_after, {"halted": END, "continue": "enrich"}
    )
    g.add_edge("enrich", "freetext")
    g.add_edge("freetext", "gate1")
    g.add_conditional_edges(
        "gate1", _route_after, {"halted": END, "continue": "baseline"}
    )
    g.add_edge("baseline", "hazard")
    g.add_conditional_edges(
        "hazard", _route_after, {"halted": END, "continue": "depth"}
    )
    g.add_edge("depth", "vuln")
    g.add_conditional_edges(
        "vuln", _route_after, {"halted": END, "continue": "math"}
    )
    g.add_conditional_edges(
        "math", _route_after, {"halted": END, "continue": "xai"}
    )
    g.add_edge("xai", "insight")
    g.add_edge("insight", "governance")
    g.add_edge("governance", END)

    return g.compile()


_compiled = None


def get_compiled_graph():
    global _compiled
    if _compiled is None:
        _compiled = build_agent_graph()
    return _compiled


@dataclass
class GraphRunResult:
    status: str
    metrics: Optional[MetricsPayload]
    insight: Optional[InsightPackage]
    properties: pd.DataFrame
    stages: list
    allowlist: dict[str, Any]
    narrative: str
    error: Optional[str]
    ollama_degraded: bool
    audit_events: list[dict[str, Any]]
    state: AgentGraphState


def run_agent_graph(
    frame: pd.DataFrame,
    profile: AssumptionsProfile,
    *,
    run_id: str,
    portfolio_id: str,
    location_label: str,
    use_ml: bool = False,
    hazard_model_version: Optional[str] = None,
    vuln_model_version: Optional[str] = None,
    registry: Optional[ModelRegistry] = None,
    enable_freetext: bool = False,
    freetext: Optional[str] = None,
    require_human_gate_1: bool = False,
    features_approved: bool = True,
    hotspots: Optional[pd.DataFrame] = None,
    use_osm: bool = False,
    overpass_url: str = "https://overpass-api.de/api/interpreter",
    ollama_host: str = "http://localhost:11434",
    ollama_model: str = "qwen2.5:3b-instruct",
    force_ollama_down: bool = False,
    tenant_id: str = "default",
    actor: str = "anonymous",
) -> GraphRunResult:
    """Execute the full agent graph for a run."""
    initial = new_state(
        run_id=run_id,
        portfolio_id=portfolio_id,
        location_label=location_label,
        profile=profile,
        frame=frame.copy(),
        use_ml=use_ml,
        hazard_model_version=hazard_model_version,
        vuln_model_version=vuln_model_version,
        registry=registry,
        enable_freetext=enable_freetext,
        freetext=freetext,
        require_human_gate_1=require_human_gate_1,
        features_approved=features_approved,
        hotspots=hotspots,
        use_osm=use_osm,
        overpass_url=overpass_url,
        ollama_host=ollama_host,
        ollama_model=ollama_model,
        force_ollama_down=force_ollama_down,
        tenant_id=tenant_id,
        actor=actor,
    )
    graph = get_compiled_graph()
    final: AgentGraphState = graph.invoke(initial)

    status = final.get("status") or ("FAILED" if final.get("halt") else "COMPLETED")
    if final.get("halt"):
        status = "FAILED"

    return GraphRunResult(
        status=status,
        metrics=final.get("metrics"),
        insight=final.get("insight"),
        properties=final.get("frame") if final.get("frame") is not None else frame,
        stages=list(final.get("stages") or []),
        allowlist=dict(final.get("allowlist") or {}),
        narrative=final.get("narrative") or "",
        error=final.get("error"),
        ollama_degraded=bool(final.get("ollama_degraded")),
        audit_events=list(final.get("audit_events") or []),
        state=final,
    )
