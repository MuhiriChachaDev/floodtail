"""Stages 4–5 — PredictHazard / PredictVulnerability (required product ML stages)."""

from __future__ import annotations

import pandas as pd

from packages.agents.state import AgentGraphState, append_stage
from packages.agents.tools.ml_tools import run_hazard_infer, run_vuln_infer
from packages.cat_core.depth import add_depth_columns
from packages.cat_core.types import StageStatus
from packages.cat_core.vulnerability_prior import add_damage_ratio_columns


def node_predict_hazard(state: AgentGraphState) -> AgentGraphState:
    profile = state["profile"]
    work = state["frame"]
    use_ml = bool(state.get("use_ml") or state.get("hazard_model_version"))
    if not use_ml:
        return append_stage(
            state,
            stage="predict_hazard",
            status=StageStatus.SKIPPED,
            message="Using ingested / proxy hazard scores (no ML)",
            critical=False,
        )

    registry = state.get("registry")
    if registry is None:
        return append_stage(
            state,
            stage="predict_hazard",
            status=StageStatus.FAILED,
            message="Model registry required for hazard ML",
            critical=True,
        )
    try:
        work, lineage = run_hazard_infer(
            work, profile, registry, version=state.get("hazard_model_version")
        )
    except Exception as exc:  # noqa: BLE001
        return append_stage(
            state,
            stage="predict_hazard",
            status=StageStatus.FAILED,
            message=f"Hazard infer failed: {exc}",
            critical=True,
        )
    out = dict(state)
    out["frame"] = work
    out["hazard_model_version"] = lineage.get("hazard_model_version")
    return append_stage(
        out,  # type: ignore[arg-type]
        stage="predict_hazard",
        status=StageStatus.OK,
        message=f"Hazard ML version={lineage.get('hazard_model_version')}",
        data=lineage,
        critical=True,
    )


def node_depth_map(state: AgentGraphState) -> AgentGraphState:
    work = add_depth_columns(state["frame"], state["profile"])
    out = dict(state)
    out["frame"] = work
    return append_stage(
        out,  # type: ignore[arg-type]
        stage="depth_map",
        status=StageStatus.OK,
        message=f"Mapped scores → depth with D_max={state['profile'].d_max_m}",
        critical=True,
    )


def node_predict_vulnerability(state: AgentGraphState) -> AgentGraphState:
    profile = state["profile"]
    work = state["frame"]
    use_ml = bool(state.get("use_ml") or state.get("vuln_model_version"))
    curves = profile.resolved_vulnerability_curves()
    if not use_ml:
        work = add_damage_ratio_columns(work, profile.tier_names, curves=curves)
        out = dict(state)
        out["frame"] = work
        return append_stage(
            out,  # type: ignore[arg-type]
            stage="predict_vulnerability",
            status=StageStatus.SKIPPED,
            message=(
                f"Using pluggable vulnerability priors ({len(curves)} classes; no ML)"
            ),
            data={"housing_classes": sorted(curves.keys())},
            critical=False,
        )

    registry = state.get("registry")
    if registry is None:
        return append_stage(
            state,
            stage="predict_vulnerability",
            status=StageStatus.FAILED,
            message="Model registry required for vulnerability ML",
            critical=True,
        )
    try:
        prior = add_damage_ratio_columns(work, profile.tier_names, curves=curves)
        for tier in profile.tier_names:
            work[f"damage_ratio_prior_{tier}"] = prior[f"damage_ratio_{tier}"]
        work, lineage = run_vuln_infer(
            work, profile, registry, version=state.get("vuln_model_version")
        )
    except Exception as exc:  # noqa: BLE001
        return append_stage(
            state,
            stage="predict_vulnerability",
            status=StageStatus.FAILED,
            message=f"Vulnerability infer failed: {exc}",
            critical=True,
        )
    out = dict(state)
    out["frame"] = work
    out["vuln_model_version"] = lineage.get("vuln_model_version")
    return append_stage(
        out,  # type: ignore[arg-type]
        stage="predict_vulnerability",
        status=StageStatus.OK,
        message=f"Vulnerability ML version={lineage.get('vuln_model_version')}",
        data=lineage,
        critical=True,
    )


def capture_baseline_scores(state: AgentGraphState) -> AgentGraphState:
    """Store pre-ML hazard scores for delta (called before hazard ML)."""
    profile = state["profile"]
    work = state["frame"]
    baseline = {
        tier: work[f"hazard_score_{tier}"].astype(float).copy()
        if f"hazard_score_{tier}" in work.columns
        else pd.Series(0.0, index=work.index)
        for tier in profile.tier_names
    }
    out = dict(state)
    out["_baseline_scores"] = baseline  # type: ignore[typeddict-unknown-key]
    return out  # type: ignore[return-value]
