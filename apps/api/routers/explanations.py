"""XAI explanation routes — SHAP local/global + counterfactuals (Phase E)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from apps.api.deps import ContextDep, SettingsDep, StoreDep, enforce_permission, enforce_tenant
from packages.agents.tools.audit_tools import append_audit
from packages.ml.registry import ModelRegistry
from packages.xai.counterfactual import counterfactual_for_location
from packages.xai.model_card import build_model_card, list_model_cards
from packages.xai.shap_global import global_shap
from packages.xai.shap_local import local_shap_for_row

router = APIRouter()


def _run_frame(store: StoreDep, run_id: str, ctx: ContextDep):
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    enforce_tenant(run, ctx)
    props = store.get_run_properties(run_id)
    if props is None or props.empty:
        raise HTTPException(status_code=404, detail="run properties not available")
    return run, props


def _registry(settings: SettingsDep) -> ModelRegistry:
    return ModelRegistry(settings.models_dir)


@router.get("/runs/{run_id}/explanations/global")
def explanations_global(
    run_id: str,
    store: StoreDep,
    settings: SettingsDep,
    ctx: ContextDep,
    model_type: str = Query(default="hazard", pattern="^(hazard|vulnerability)$"),
    sample_size: int = Query(default=80, ge=5, le=600),
    tier: str = Query(default="extreme"),
) -> dict:
    enforce_permission(ctx, "explain")
    run, props = _run_frame(store, run_id, ctx)
    reg = _registry(settings)
    version = (
        run.metrics.hazard_model_version
        if model_type == "hazard" and run.metrics
        else (run.metrics.vuln_model_version if run.metrics else None)
    )
    if version is None:
        version = reg.get_pinned(model_type)  # type: ignore[arg-type]
    if version is None:
        raise HTTPException(
            status_code=400,
            detail=f"No {model_type} model available — train/pin or run with use_ml=true",
        )
    try:
        payload = global_shap(
            props,
            reg,
            model_type=model_type,  # type: ignore[arg-type]
            version=version,
            tier=tier,
            sample_size=sample_size,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    append_audit(
        "explanations_global",
        {"run_id": run_id, "model_type": model_type, "actor": ctx.actor},
    )
    return {"run_id": run_id, "explanation": payload}


@router.get("/runs/{run_id}/explanations/local/{loc_id}")
def explanations_local(
    run_id: str,
    loc_id: str,
    store: StoreDep,
    settings: SettingsDep,
    ctx: ContextDep,
    model_type: str = Query(default="hazard", pattern="^(hazard|vulnerability)$"),
    tier: str = Query(default="extreme"),
) -> dict:
    enforce_permission(ctx, "explain")
    run, props = _run_frame(store, run_id, ctx)
    reg = _registry(settings)
    version = None
    if run.metrics:
        version = (
            run.metrics.hazard_model_version
            if model_type == "hazard"
            else run.metrics.vuln_model_version
        )
    if version is None:
        version = reg.get_pinned(model_type)  # type: ignore[arg-type]
    if version is None:
        raise HTTPException(status_code=400, detail=f"No {model_type} model available")
    try:
        payload = local_shap_for_row(
            props,
            loc_id,
            reg,
            model_type=model_type,  # type: ignore[arg-type]
            version=version,
            tier=tier,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    append_audit(
        "explanations_local",
        {"run_id": run_id, "loc_id": loc_id, "actor": ctx.actor},
    )
    return {"run_id": run_id, "explanation": payload}


@router.get("/runs/{run_id}/explanations/counterfactual/{loc_id}")
def explanations_counterfactual(
    run_id: str,
    loc_id: str,
    store: StoreDep,
    settings: SettingsDep,
    ctx: ContextDep,
    model_type: str = Query(default="vulnerability", pattern="^(hazard|vulnerability)$"),
    tier: str = Query(default="extreme"),
    depth_m_scale: Optional[float] = Query(default=0.8),
    dist_hotspot_km_add: Optional[float] = Query(default=None),
) -> dict:
    enforce_permission(ctx, "explain")
    run, props = _run_frame(store, run_id, ctx)
    reg = _registry(settings)
    version = None
    if run.metrics:
        version = (
            run.metrics.vuln_model_version
            if model_type == "vulnerability"
            else run.metrics.hazard_model_version
        )
    if version is None:
        version = reg.get_pinned(model_type)  # type: ignore[arg-type]
    if version is None:
        raise HTTPException(status_code=400, detail=f"No {model_type} model available")

    deltas: dict[str, Any] = {}
    if depth_m_scale is not None and model_type == "vulnerability":
        deltas["depth_m_scale"] = depth_m_scale
    if dist_hotspot_km_add is not None:
        deltas["dist_hotspot_km_add"] = dist_hotspot_km_add

    profile = settings.assumptions_profile()
    try:
        payload = counterfactual_for_location(
            props,
            loc_id,
            profile,
            reg,
            model_type=model_type,
            version=version,
            tier=tier,
            feature_deltas=deltas or None,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    append_audit(
        "explanations_counterfactual",
        {"run_id": run_id, "loc_id": loc_id, "actor": ctx.actor},
    )
    return {"run_id": run_id, "counterfactual": payload}


@router.get("/models/cards")
def model_cards(settings: SettingsDep, ctx: ContextDep) -> dict:
    enforce_permission(ctx, "model:read")
    cards = list_model_cards(_registry(settings))
    return {"cards": cards}


@router.get("/models/{model_type}/card")
def model_card(
    model_type: str,
    settings: SettingsDep,
    ctx: ContextDep,
    version: Optional[str] = None,
) -> dict:
    enforce_permission(ctx, "model:read")
    if model_type not in ("hazard", "vulnerability"):
        raise HTTPException(status_code=400, detail="model_type must be hazard|vulnerability")
    try:
        card = build_model_card(_registry(settings), model_type, version=version)  # type: ignore[arg-type]
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"card": card}
