"""Narrative + free-text query routes — Phase D."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from apps.api.deps import (
    ContextDep,
    SettingsDep,
    StoreDep,
    enforce_permission,
    enforce_tenant,
)
from packages.agents.nodes.briefing import generate_narrative
from packages.agents.nodes.query import answer_query
from packages.agents.tools.audit_tools import append_audit
from packages.agents.tools.math_tools import get_allowlist

router = APIRouter()


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    force_ollama_down: bool = False


@router.get("/runs/{run_id}/narrative")
def get_narrative(
    run_id: str,
    store: StoreDep,
    settings: SettingsDep,
    ctx: ContextDep,
    force_ollama_down: bool = False,
) -> dict:
    enforce_permission(ctx, "narrative")
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    enforce_tenant(run, ctx)
    if run.metrics is None:
        raise HTTPException(status_code=404, detail="metrics not available")

    allowlist = run.allowlist or get_allowlist(run.metrics)
    if run.narrative and run.insight and not force_ollama_down:
        return {
            "run_id": run_id,
            "narrative": run.narrative,
            "source": run.insight.numbers_source,
            "allowlist_keys": sorted(allowlist.keys()),
        }

    narrative, source = generate_narrative(
        run.metrics,
        allowlist,
        ollama_host=settings.ollama_host,
        ollama_model=settings.ollama_primary_model,
        force_down=force_ollama_down or run.ollama_degraded,
    )
    run.narrative = narrative
    store.save_run(run)
    append_audit(
        "narrative",
        {"run_id": run_id, "source": source},
    )
    return {
        "run_id": run_id,
        "narrative": narrative,
        "source": source,
        "allowlist_keys": sorted(allowlist.keys()),
    }


@router.post("/runs/{run_id}/query")
def query_run(
    run_id: str,
    body: QueryRequest,
    store: StoreDep,
    settings: SettingsDep,
    ctx: ContextDep,
) -> dict:
    enforce_permission(ctx, "query")
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    enforce_tenant(run, ctx)
    if run.metrics is None:
        raise HTTPException(status_code=404, detail="metrics not available")

    allowlist = run.allowlist or get_allowlist(run.metrics)
    result = answer_query(
        body.question,
        allowlist,
        ollama_host=settings.ollama_host,
        ollama_model=settings.ollama_primary_model,
        force_down=body.force_ollama_down or run.ollama_degraded,
    )
    append_audit(
        "query",
        {
            "run_id": run_id,
            "blocked": result.get("blocked"),
            "ok": result.get("ok"),
            "source": result.get("source"),
        },
    )
    if result.get("blocked"):
        raise HTTPException(
            status_code=400,
            detail={
                "message": "prompt injection blocked",
                "reasons": result.get("detail"),
            },
        )
    return {"run_id": run_id, **result}
