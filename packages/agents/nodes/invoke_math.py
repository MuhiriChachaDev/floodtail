"""Stage 6 — Grounded financial + EP + capital band (critical)."""

from __future__ import annotations

from packages.agents.state import AgentGraphState, append_stage
from packages.agents.tools.math_tools import compute_ep_capital, get_allowlist
from packages.cat_core.depth import add_depth_columns
from packages.cat_core.exposure import default_data_labels
from packages.cat_core.financial import add_loss_columns, reconcile_location_losses
from packages.cat_core.ep import build_tier_losses, discrete_aal
from packages.cat_core.types import StageStatus
from packages.cat_core.vulnerability_prior import add_damage_ratio_columns
from packages.ml.enrich import enrich_frame


def node_invoke_math(state: AgentGraphState) -> AgentGraphState:
    profile = state["profile"]
    work = state["frame"]
    labels = default_data_labels(profile)
    baseline_delta: dict = {}

    use_hazard_ml = any(
        s.stage == "predict_hazard" and s.status == StageStatus.OK
        for s in (state.get("stages") or [])
    )
    use_vuln_ml = any(
        s.stage == "predict_vulnerability" and s.status == StageStatus.OK
        for s in (state.get("stages") or [])
    )

    if use_hazard_ml or use_vuln_ml:
        baseline_scores = state.get("_baseline_scores") or {}  # type: ignore[attr-defined]
        base = work.copy()
        # Prefer original ingest scores if captured
        for tier in profile.tier_names:
            col = f"hazard_score_{tier}"
            if tier in baseline_scores:
                base[col] = baseline_scores[tier]
        base = enrich_frame(base, hotspots=state.get("hotspots"), use_osm=False)
        base = add_depth_columns(base, profile)
        base = add_damage_ratio_columns(base, profile.tier_names)
        base = add_loss_columns(base, profile.tier_names)
        base_totals = reconcile_location_losses(base, profile.tier_names)
        base_tiers = build_tier_losses(base_totals, profile)
        base_aal = discrete_aal(base_tiers)
        # Current totals for delta after compute
        baseline_delta = {"baseline_aal_kes": round(base_aal, 2)}

    try:
        work, metrics, _tiers, _band = compute_ep_capital(
            work,
            profile,
            run_id=state["run_id"],
            portfolio_id=state["portfolio_id"],
            location_label=state.get("location_label") or "unknown",
            data_labels=labels,
            hazard_model_version=state.get("hazard_model_version"),
            vuln_model_version=state.get("vuln_model_version"),
            baseline_delta=baseline_delta,
            warnings=list(state.get("warnings") or []),
        )
    except Exception as exc:  # noqa: BLE001
        return append_stage(
            state,
            stage="ep_capital",
            status=StageStatus.FAILED,
            message=f"Financial / EP / capital failed: {exc}",
            critical=True,
        )

    if baseline_delta:
        # Fill tier loss deltas vs current metrics
        cur_totals = {t.tier: t.loss_kes for t in metrics.tier_losses}
        # Recompute base totals keys
        if use_hazard_ml or use_vuln_ml:
            metrics.baseline_delta = {
                **baseline_delta,
                "aal_delta_kes": round(metrics.aal_kes - float(baseline_delta["baseline_aal_kes"]), 2),
                "tier_loss_delta_kes": {
                    t: round(float(cur_totals.get(t, 0.0)), 2) for t in profile.tier_names
                },
            }

    enrich_data = {}
    for stage in state.get("stages") or []:
        if stage.stage == "enrich" and stage.data:
            enrich_data = dict(stage.data)
            break
    if enrich_data:
        metrics.accumulation_summary = {
            **(metrics.accumulation_summary or {}),
            "enrichment": enrich_data,
        }

    allowlist = get_allowlist(metrics)
    out = dict(state)
    out["frame"] = work
    out["metrics"] = metrics
    out["allowlist"] = allowlist
    return append_stage(
        out,  # type: ignore[arg-type]
        stage="ep_capital",
        status=StageStatus.OK,
        message="EP curve + capital band computed",
        data={"aal_kes": metrics.aal_kes},
        critical=True,
    )

