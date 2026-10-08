"""Underwriter insight routes — agent/template package (Phase D)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.deps import ContextDep, StoreDep, enforce_permission, enforce_tenant

router = APIRouter()


@router.get("/runs/{run_id}/insight")
def get_insight(run_id: str, store: StoreDep, ctx: ContextDep) -> dict:
    enforce_permission(ctx, "run:read")
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    enforce_tenant(run, ctx)
    if run.insight is None:
        raise HTTPException(status_code=404, detail="insight not available")
    return {
        "insight": run.insight.model_dump(mode="json"),
        "ollama_degraded": run.ollama_degraded,
    }
