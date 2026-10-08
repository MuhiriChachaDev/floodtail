"""Run pipeline routes — LangGraph agent orchestration (Phase D)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from apps.api.deps import (
    ContextDep,
    SettingsDep,
    StoreDep,
    enforce_permission,
    enforce_tenant,
)
from packages.agents.graph import run_agent_graph
from packages.agents.tools.audit_tools import append_audit
from packages.cat_core.assumptions import AssumptionsProfile
from packages.cat_core.engine import default_hotspots_frame
from packages.cat_core.geo_scope import hotspots_near_portfolio
from packages.cat_core.types import DecisionRecord, Recommendation, RunConfig, utc_now
from packages.ml.registry import ModelRegistry
from packages.security.audit_log import get_audit_chain

router = APIRouter()


class CreateRunRequest(BaseModel):
    portfolio_id: str
    use_ml: Optional[bool] = True  # product default: ML required; false only if allow_prior_only
    hazard_model_version: Optional[str] = None
    vuln_model_version: Optional[str] = None
    d_max_m: Optional[float] = None
    assumptions_version: Optional[str] = None
    use_osm: Optional[bool] = None  # None → settings.use_osm_default (off; never required)
    enable_freetext: bool = False
    freetext: Optional[str] = None
    require_human_gate_1: bool = False
    features_approved: bool = True
    force_ollama_down: bool = False  # tests / offline demos
    # Optional XL / pricing overrides (absolute KES / load); else profile defaults
    treaty_attachment_kes: Optional[float] = Field(default=None, ge=0.0)
    treaty_limit_kes: Optional[float] = Field(default=None, ge=0.0)
    pricing_load_factor: Optional[float] = Field(default=None, ge=1.0, le=3.0)


class ApproveRequest(BaseModel):
    decision: Recommendation
    reason: str = Field(min_length=3)
    gate: str = "gate2"


def _profile_for_run(settings: SettingsDep, body: CreateRunRequest) -> AssumptionsProfile:
    profile = settings.assumptions_profile()
    data = profile.model_dump()
    if body.d_max_m is not None:
        data["d_max_m"] = body.d_max_m
    if body.assumptions_version is not None:
        data["assumptions_version"] = body.assumptions_version
    if body.treaty_attachment_kes is not None:
        data["treaty"]["attachment_kes"] = body.treaty_attachment_kes
    if body.treaty_limit_kes is not None:
        data["treaty"]["limit_kes"] = body.treaty_limit_kes
    if body.pricing_load_factor is not None:
        data["pricing"]["default_load_factor"] = body.pricing_load_factor
    return AssumptionsProfile(**data)


def _resolve_ml(
    body: CreateRunRequest, settings: SettingsDep
) -> tuple[bool, Optional[str], Optional[str], Optional[ModelRegistry]]:
    """
    Predictive ML is a required product stage.
    Prior-only (use_ml=false) is rejected unless settings.allow_prior_only.
    """
    registry = ModelRegistry(settings.models_dir)
    want_prior = body.use_ml is False and not (
        body.hazard_model_version or body.vuln_model_version
    )

    if want_prior:
        if settings.require_ml and not settings.allow_prior_only:
            raise HTTPException(
                status_code=400,
                detail="Predictive ML is required for FLOODTAIL runs "
                "(hazard + vulnerability models). Train/pin via POST /v1/models/*/train "
                "or omit use_ml=false. Set ALLOW_PRIOR_ONLY=true only for offline debug.",
            )
        return False, None, None, None

    haz_ver = body.hazard_model_version or registry.get_pinned("hazard")
    vuln_ver = body.vuln_model_version or registry.get_pinned("vulnerability")
    if haz_ver is None or vuln_ver is None:
        raise HTTPException(
            status_code=400,
            detail="Pinned hazard and vulnerability models are required "
            "(python scripts/train_models.py or POST /v1/models/*/train).",
        )
    if not registry.verify_integrity("hazard", haz_ver):
        raise HTTPException(status_code=400, detail="hazard model integrity failed")
    if not registry.verify_integrity("vulnerability", vuln_ver):
        raise HTTPException(status_code=400, detail="vulnerability model integrity failed")
    return True, haz_ver, vuln_ver, registry


@router.post("/runs")
def create_run(
    body: CreateRunRequest,
    settings: SettingsDep,
    store: StoreDep,
    ctx: ContextDep,
) -> dict:
    enforce_permission(ctx, "run:write")
    portfolio = store.get_portfolio(body.portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="portfolio not found")
    enforce_tenant(portfolio, ctx)
    frame = store.get_portfolio_frame(body.portfolio_id)
    if frame is None or frame.empty:
        raise HTTPException(status_code=400, detail="portfolio has no exposure rows")

    profile = _profile_for_run(settings, body)
    use_ml, haz_ver, vuln_ver, registry = _resolve_ml(body, settings)

    config = RunConfig(
        portfolio_id=body.portfolio_id,
        use_ml=use_ml,
        hazard_model_version=haz_ver,
        vuln_model_version=vuln_ver,
        enable_freetext=body.enable_freetext,
        freetext=body.freetext,
        require_human_gate_1=body.require_human_gate_1,
        assumptions_version=profile.assumptions_version,
        d_max_m=profile.d_max_m,
        treaty_attachment_kes=body.treaty_attachment_kes,
        treaty_limit_kes=body.treaty_limit_kes,
        pricing_load_factor=body.pricing_load_factor,
        tenant_id=ctx.tenant_id,
        actor=ctx.actor,
    )
    run = store.create_run(config)
    run.status = "RUNNING"
    store.save_run(run)

    # Hotspots only when they fall near this portfolio (Kisumu ≠ Nairobi spots).
    all_hotspots = default_hotspots_frame(
        settings.nairobi_data_dir / settings.hotspots_filename
    )
    hotspots = hotspots_near_portfolio(all_hotspots, frame)
    # OSM is never required: opt-in only; Overpass failure degrades inside enrich_frame.
    use_osm = settings.use_osm_default if body.use_osm is None else bool(body.use_osm)

    append_audit(
        "run_started",
        {"run_id": run.id, "portfolio_id": portfolio.id, "use_ml": use_ml},
    )

    try:
        result = run_agent_graph(
            frame,
            profile,
            run_id=run.id,
            portfolio_id=portfolio.id,
            location_label=portfolio.location_label,
            use_ml=use_ml,
            hazard_model_version=haz_ver,
            vuln_model_version=vuln_ver,
            registry=registry,
            enable_freetext=body.enable_freetext,
            freetext=body.freetext,
            require_human_gate_1=body.require_human_gate_1,
            features_approved=body.features_approved,
            hotspots=hotspots,
            use_osm=use_osm,
            overpass_url=settings.overpass_url,
            ollama_host=settings.ollama_host,
            ollama_model=settings.ollama_primary_model,
            force_ollama_down=body.force_ollama_down,
            tenant_id=ctx.tenant_id,
            actor=ctx.actor,
        )
    except Exception as exc:  # noqa: BLE001
        run.status = "FAILED"
        run.error = str(exc)
        run.updated_at = utc_now()
        store.save_run(run)
        append_audit("run_failed", {"run_id": run.id, "error": str(exc)})
        raise HTTPException(status_code=500, detail=f"run failed: {exc}") from exc

    run.status = result.status  # type: ignore[assignment]
    run.stages = result.stages
    run.metrics = result.metrics
    run.insight = result.insight
    run.narrative = result.narrative
    run.allowlist = result.allowlist
    run.ollama_degraded = result.ollama_degraded
    run.error = result.error
    run.updated_at = utc_now()
    store.save_run(run)
    if result.properties is not None:
        store.save_run_properties(run.id, result.properties)

    append_audit(
        "run_completed",
        {
            "run_id": run.id,
            "status": run.status,
            "recommendation": (
                result.insight.recommendation.value if result.insight else None
            ),
        },
    )

    if run.status == "FAILED":
        raise HTTPException(
            status_code=400,
            detail={
                "message": run.error or "run failed",
                "run_id": run.id,
                "stages": [s.model_dump(mode="json") for s in run.stages],
            },
        )

    return {
        "run": run.model_dump(mode="json"),
        "metrics": result.metrics.model_dump(mode="json") if result.metrics else None,
        "insight": result.insight.model_dump(mode="json") if result.insight else None,
        "ollama_degraded": result.ollama_degraded,
        "audit_chain_valid": get_audit_chain().verify(),
    }


@router.get("/runs/{run_id}")
def get_run(run_id: str, store: StoreDep, ctx: ContextDep) -> dict:
    enforce_permission(ctx, "run:read")
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    enforce_tenant(run, ctx)
    return {"run": run.model_dump(mode="json")}


@router.get("/runs/{run_id}/metrics")
def get_metrics(run_id: str, store: StoreDep, ctx: ContextDep) -> dict:
    enforce_permission(ctx, "run:read")
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    enforce_tenant(run, ctx)
    if run.metrics is None:
        raise HTTPException(status_code=404, detail="metrics not available")
    return {"metrics": run.metrics.model_dump(mode="json")}


@router.get("/runs/{run_id}/properties")
def get_properties(
    run_id: str,
    store: StoreDep,
    ctx: ContextDep,
    limit: int = Query(default=50, ge=1, le=600),
    offset: int = Query(default=0, ge=0),
) -> dict:
    enforce_permission(ctx, "run:read")
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    enforce_tenant(run, ctx)
    props = store.get_run_properties(run_id)
    if props is None:
        raise HTTPException(status_code=404, detail="properties not available")

    total = len(props)
    page = props.iloc[offset : offset + limit]
    cols = [
        c
        for c in [
            "loc_id",
            "lat",
            "lon",
            "housing_class",
            "tiv_kes",
            "synthetic",
            "dist_hotspot_km",
            "dist_waterway_km",
            "loss_kes_common",
            "loss_kes_occasional",
            "loss_kes_moderate",
            "loss_kes_severe",
            "loss_kes_extreme",
            "damage_ratio_severe",
            "damage_ratio_extreme",
            "depth_m_severe",
            "depth_m_extreme",
            "hazard_score_severe",
            "hazard_score_extreme",
            "hazard_score_pred_severe",
            "hazard_score_pred_extreme",
        ]
        if c in page.columns
    ]
    records: list[dict[str, Any]] = page[cols].to_dict(orient="records")
    return {
        "run_id": run_id,
        "total": total,
        "offset": offset,
        "limit": limit,
        "properties": records,
    }


@router.get("/runs/{run_id}/accumulation")
def get_accumulation(run_id: str, store: StoreDep, ctx: ContextDep) -> dict:
    enforce_permission(ctx, "run:read")
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    enforce_tenant(run, ctx)
    if run.metrics is None:
        raise HTTPException(status_code=404, detail="accumulation not available")
    return {
        "run_id": run_id,
        "accumulation": run.metrics.accumulation_summary,
    }


@router.post("/runs/{run_id}/approve")
def approve_run(
    run_id: str,
    body: ApproveRequest,
    store: StoreDep,
    ctx: ContextDep,
) -> dict:
    enforce_permission(ctx, "approve")
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    enforce_tenant(run, ctx)
    if run.status not in ("COMPLETED", "REVIEW_REQUIRED"):
        raise HTTPException(
            status_code=400,
            detail=f"run status {run.status} cannot be approved",
        )
    decision = DecisionRecord(
        decision=body.decision,
        reason=body.reason.strip(),
        actor=ctx.actor,
        gate=body.gate if body.gate in ("gate1", "gate2") else "gate2",  # type: ignore[arg-type]
    )
    run.decision = decision
    run.updated_at = utc_now()
    store.save_run(run)
    audit = append_audit(
        "decision",
        {
            "run_id": run_id,
            "decision": decision.decision.value,
            "reason": decision.reason,
            "actor": decision.actor,
            "role": ctx.role,
            "tenant_id": ctx.tenant_id,
            "gate": decision.gate,
        },
    )
    return {
        "run_id": run_id,
        "decision": decision.model_dump(mode="json"),
        "audit": audit,
        "chain_valid": get_audit_chain().verify(),
    }
