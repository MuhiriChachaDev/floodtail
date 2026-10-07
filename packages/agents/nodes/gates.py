"""Stage 3 / 9 — Human gates."""

from __future__ import annotations

from packages.agents.state import AgentGraphState, append_stage
from packages.agents.tools.audit_tools import append_audit
from packages.cat_core.types import StageStatus


def node_human_gate_1(state: AgentGraphState) -> AgentGraphState:
    if not state.get("require_human_gate_1"):
        out = append_stage(
            state,
            stage="human_gate_1",
            status=StageStatus.SKIPPED,
            message="Human gate 1 not required",
            critical=False,
        )
        out = dict(out)
        out["features_approved"] = True
        return out  # type: ignore[return-value]

    if state.get("features_approved"):
        audit = append_audit(
            "human_gate_1_approved",
            {"run_id": state.get("run_id"), "actor": state.get("actor")},
        )
        out = dict(state)
        out["audit_events"] = list(state.get("audit_events") or []) + [audit]
        return append_stage(
            out,  # type: ignore[arg-type]
            stage="human_gate_1",
            status=StageStatus.OK,
            message="Features approved",
            critical=True,
        )

    return append_stage(
        state,
        stage="human_gate_1",
        status=StageStatus.FAILED,
        message="Human gate 1 required but features not approved",
        critical=True,
    )


def node_governance(state: AgentGraphState) -> AgentGraphState:
    """Stage 9 — stamp ready_for_human + audit; decision via approve API."""
    audit = append_audit(
        "governance_ready",
        {
            "run_id": state.get("run_id"),
            "recommendation": (
                state["insight"].recommendation.value
                if state.get("insight") is not None
                else None
            ),
            "status": state.get("status"),
        },
    )
    out = dict(state)
    out["audit_events"] = list(state.get("audit_events") or []) + [audit]
    if out.get("status") == "RUNNING":
        out["status"] = "COMPLETED"
    return append_stage(
        out,  # type: ignore[arg-type]
        stage="governance",
        status=StageStatus.OK,
        message="Ready for underwriter decision (approve endpoint)",
        data={"ready_for_human": True, "chain_event": audit["event_hash"][:16]},
        critical=False,
    )
