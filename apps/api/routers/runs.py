"""Run pipeline routes — prior-only or ML-backed."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from apps.api.deps import ContextDep, SettingsDep, StoreDep
from packages.cat_core.assumptions import AssumptionsProfile
from packages.cat_core.engine import default_hotspots_frame, run_cat
from packages.cat_core.exceptions import CatCoreError
from packages.cat_core.types import RunConfig, utc_now
from packages.ml.registry import ModelRegistry

router = APIRouter()


class CreateRunRequest(BaseModel):
    portfolio_id: str
    use_ml: bool = False
    hazard_model_version: Optional[str] = None
    vuln_model_version: Optional[str] = None
    d_max_m: Optional[float] = None
    assumptions_version: Optional[str] = None
    use_osm: bool = False


def _profile_for_run(settings: SettingsDep, body: CreateRunRequest) -> AssumptionsProfile:
    profile = settings.assumptions_profile()
    data = profile.model_dump()
    if body.d_max_m is not None:
        data["d_max_m"] = body.d_max_m
    if body.assumptions_version is not None:
        data["assumptions_version"] = body.assumptions_version
    return AssumptionsProfile(**data)


@router.post("/runs")
def create_run(
    body: CreateRunRequest,
    settings: SettingsDep,
    store: StoreDep,
    ctx: ContextDep,
) -> dict:
    portfolio = store.get_portfolio(body.portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="portfolio not found")
    frame = store.get_portfolio_frame(body.portfolio_id)
    if frame is None or frame.empty:
        raise HTTPException(status_code=400, detail="portfolio has no exposure rows")

    profile = _profile_for_run(settings, body)
    use_ml = bool(body.use_ml or body.hazard_model_version or body.vuln_model_version)
    registry = ModelRegistry(settings.models_dir) if use_ml else None

    if use_ml:
        assert registry is not None
        # Resolve versions — pin if use_ml without explicit versions
        haz_ver = body.hazard_model_version
        vuln_ver = body.vuln_model_version
        if body.use_ml and haz_ver is None:
            haz_ver = registry.get_pinned("hazard")
        if body.use_ml and vuln_ver is None:
            vuln_ver = registry.get_pinned("vulnerability")
        if body.use_ml and (haz_ver is None or vuln_ver is None):
            raise HTTPException(
                status_code=400,
                detail="use_ml=true requires pinned hazard and vulnerability models "
                "(POST /v1/models/*/train first) or explicit versions.",
            )
        if haz_ver and not registry.verify_integrity("hazard", haz_ver):
            raise HTTPException(status_code=400, detail="hazard model integrity failed")
        if vuln_ver and not registry.verify_integrity("vulnerability", vuln_ver):
            raise HTTPException(status_code=400, detail="vulnerability model integrity failed")
    else:
        haz_ver = None
        vuln_ver = None

    config = RunConfig(
        portfolio_id=body.portfolio_id,
        use_ml=use_ml,
        hazard_model_version=haz_ver,
        vuln_model_version=vuln_ver,
        assumptions_version=profile.assumptions_version,
        d_max_m=profile.d_max_m,
        tenant_id=ctx.tenant_id,
        actor=ctx.actor,
    )
    run = store.create_run(config)
    run.status = "RUNNING"
    store.save_run(run)

    hotspots = default_hotspots_frame(
        settings.nairobi_data_dir / settings.hotspots_filename
    )
    # Prefer portfolio-attached hotspots later; for now optional global layer if present
    use_osm = body.use_osm or settings.use_osm_default

    try:
        result = run_cat(
            frame,
            profile,
            run_id=run.id,
            portfolio_id=portfolio.id,
            location_label=portfolio.location_label,
            data_labels=portfolio.data_labels,
            hotspots=hotspots,
            use_osm=use_osm,
            overpass_url=settings.overpass_url,
            registry=registry,
            hazard_model_version=haz_ver,
            vuln_model_version=vuln_ver,
            use_ml=use_ml,
        )
    except CatCoreError as exc:
        run.status = "FAILED"
        run.error = str(exc)
        run.updated_at = utc_now()
        store.save_run(run)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        run.status = "FAILED"
        run.error = str(exc)
        run.updated_at = utc_now()
        store.save_run(run)
        raise HTTPException(status_code=500, detail=f"run failed: {exc}") from exc

    run.status = "COMPLETED"
    run.stages = result.stages
    run.metrics = result.metrics
    run.insight = result.insight
    run.error = None
    run.updated_at = utc_now()
    store.save_run(run)
    store.save_run_properties(run.id, result.properties)

    return {
        "run": run.model_dump(mode="json"),
        "metrics": result.metrics.model_dump(mode="json"),
        "insight": result.insight.model_dump(mode="json"),
    }


@router.get("/runs/{run_id}")
def get_run(run_id: str, store: StoreDep) -> dict:
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return {"run": run.model_dump(mode="json")}


@router.get("/runs/{run_id}/metrics")
def get_metrics(run_id: str, store: StoreDep) -> dict:
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    if run.metrics is None:
        raise HTTPException(status_code=404, detail="metrics not available")
    return {"metrics": run.metrics.model_dump(mode="json")}


@router.get("/runs/{run_id}/properties")
def get_properties(
    run_id: str,
    store: StoreDep,
    limit: int = Query(default=50, ge=1, le=600),
    offset: int = Query(default=0, ge=0),
) -> dict:
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
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
            "damage_ratio_extreme",
            "depth_m_extreme",
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
def get_accumulation(run_id: str, store: StoreDep) -> dict:
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    if run.metrics is None:
        raise HTTPException(status_code=404, detail="accumulation not available")
    return {
        "run_id": run_id,
        "accumulation": run.metrics.accumulation_summary,
    }


@router.post("/runs/{run_id}/approve")
def approve_run(run_id: str) -> dict:
    return {
        "status": "not_implemented",
        "phase": "C",
        "run_id": run_id,
        "next": "D",
        "detail": "Human gate approve lands in Phase D/E.",
    }
