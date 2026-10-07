"""Underwriter insight routes — template in Phase B."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.deps import StoreDep

router = APIRouter()


@router.get("/runs/{run_id}/insight")
def get_insight(run_id: str, store: StoreDep) -> dict:
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    if run.insight is None:
        raise HTTPException(status_code=404, detail="insight not available")
    return {"insight": run.insight.model_dump(mode="json")}
