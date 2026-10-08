"""Stage 7 — XAI: global/local SHAP into metrics + allowlist (non-critical)."""

from __future__ import annotations

from typing import Any

from packages.agents.state import AgentGraphState, append_stage
from packages.agents.tools.math_tools import get_allowlist
from packages.cat_core.types import StageStatus
from packages.xai.shap_global import global_shap
from packages.xai.shap_local import local_shap_for_row


def _top_driver_names(drivers: list[dict[str, Any]], k: int = 5) -> list[str]:
    return [str(d.get("feature")) for d in drivers[:k] if d.get("feature")]


def compute_run_xai(
    frame,
    registry,
    *,
    hazard_version: str | None,
    vuln_version: str | None,
    sample_size: int = 60,
    tier: str = "extreme",
) -> dict[str, Any]:
    """
    Build a compact XAI summary for the run allowlist / insight agent.
    Non-raising: callers wrap exceptions for non-critical degrade.
    """
    summary: dict[str, Any] = {
        "tier": tier,
        "disclaimer": "SHAP explains model predictions on synthetic/proxy labels, not flood physics.",
    }
    warnings: list[str] = []

    if hazard_version:
        haz = global_shap(
            frame,
            registry,
            model_type="hazard",
            version=hazard_version,
            sample_size=sample_size,
            top_k=8,
        )
        summary["hazard_global"] = {
            "drivers": haz.get("drivers") or [],
            "top_features": _top_driver_names(haz.get("drivers") or []),
            "sample_size": haz.get("sample_size"),
            "lineage": haz.get("lineage"),
        }
    else:
        warnings.append("XAI skipped hazard SHAP — no hazard model version")

    if vuln_version:
        vuln = global_shap(
            frame,
            registry,
            model_type="vulnerability",
            version=vuln_version,
            tier=tier,
            sample_size=sample_size,
            top_k=8,
        )
        summary["vulnerability_global"] = {
            "drivers": vuln.get("drivers") or [],
            "top_features": _top_driver_names(vuln.get("drivers") or []),
            "sample_size": vuln.get("sample_size"),
            "lineage": vuln.get("lineage"),
        }
        # One local example (highest extreme loss if available)
        loc_id = None
        if "loc_id" in frame.columns:
            if "loss_kes_extreme" in frame.columns:
                loc_id = str(frame.nlargest(1, "loss_kes_extreme").iloc[0]["loc_id"])
            else:
                loc_id = str(frame.iloc[0]["loc_id"])
        if loc_id:
            local = local_shap_for_row(
                frame,
                loc_id,
                registry,
                model_type="vulnerability",
                version=vuln_version,
                tier=tier,
                top_k=5,
            )
            summary["sample_local"] = {
                "loc_id": local.get("loc_id"),
                "model_type": "vulnerability",
                "tier": tier,
                "prediction": local.get("prediction"),
                "top_features": local.get("top_features") or [],
            }
    else:
        warnings.append("XAI skipped vulnerability SHAP — no vuln model version")

    return {"summary": summary, "warnings": warnings}


def node_xai(state: AgentGraphState) -> AgentGraphState:
    """Non-critical: attach SHAP drivers to metrics + allowlist for insight."""
    metrics = state.get("metrics")
    frame = state.get("frame")
    registry = state.get("registry")
    use_ml = bool(state.get("use_ml") or state.get("hazard_model_version"))

    if metrics is None or frame is None or frame.empty:
        return append_stage(
            state,
            stage="xai",
            status=StageStatus.SKIPPED,
            message="XAI skipped — no metrics/frame",
            critical=False,
        )

    if not use_ml or registry is None:
        return append_stage(
            state,
            stage="xai",
            status=StageStatus.SKIPPED,
            message="XAI skipped — ML models not in run",
            critical=False,
        )

    try:
        payload = compute_run_xai(
            frame,
            registry,
            hazard_version=state.get("hazard_model_version") or metrics.hazard_model_version,
            vuln_version=state.get("vuln_model_version") or metrics.vuln_model_version,
            sample_size=min(60, len(frame)),
            tier="extreme",
        )
    except Exception as exc:  # noqa: BLE001
        return append_stage(
            state,
            stage="xai",
            status=StageStatus.WARN,
            message=f"XAI failed (non-critical): {exc}",
            warnings=[str(exc)],
            critical=False,
        )

    summary = payload["summary"]
    warnings = list(payload.get("warnings") or [])
    metrics.xai_summary = summary
    allowlist = get_allowlist(metrics)
    # Preserve any prior allowlist keys then overlay
    prior = dict(state.get("allowlist") or {})
    prior.update(allowlist)

    out = dict(state)
    out["metrics"] = metrics
    out["allowlist"] = prior
    haz_tops = (summary.get("hazard_global") or {}).get("top_features") or []
    vuln_tops = (summary.get("vulnerability_global") or {}).get("top_features") or []
    return append_stage(
        out,  # type: ignore[arg-type]
        stage="xai",
        status=StageStatus.OK,
        message=(
            f"SHAP drivers attached "
            f"(hazard top={haz_tops[:3]}; vuln top={vuln_tops[:3]})"
        ),
        warnings=warnings,
        data={
            "hazard_top_features": haz_tops,
            "vulnerability_top_features": vuln_tops,
            "sample_local_loc_id": (summary.get("sample_local") or {}).get("loc_id"),
        },
        critical=False,
    )
