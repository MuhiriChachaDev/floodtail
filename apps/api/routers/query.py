"""Narrative + free-text query routes — Phase D."""

from __future__ import annotations

from typing import Any, Optional

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
from packages.agents.tools.math_tools import allowlist_from_client_metrics, get_allowlist

router = APIRouter()


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    force_ollama_down: bool = False
    use_rag: bool = True
    use_memory: bool = True
    session_id: Optional[str] = Field(default=None, max_length=128)


class AssistantChatRequest(BaseModel):
    """Floating UI chat — optional run grounding + RAG/memory + Ollama Qwen."""

    question: str = Field(min_length=1, max_length=4000)
    run_id: Optional[str] = Field(default=None, max_length=64)
    session_id: Optional[str] = Field(default=None, max_length=128)
    force_ollama_down: bool = False
    use_rag: bool = True
    use_memory: bool = True
    # Metrics JSON from browser localStorage when server store lost the run
    client_metrics: Optional[dict[str, Any]] = None


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
    from packages.rag.config import configure_rag

    configure_rag(settings.rag_settings())
    result = answer_query(
        body.question,
        allowlist,
        ollama_host=settings.ollama_host,
        ollama_model=settings.ollama_primary_model,
        force_down=body.force_ollama_down or run.ollama_degraded,
        tenant_id=ctx.tenant_id,
        session_id=body.session_id or run_id,
        use_rag=body.use_rag,
        use_memory=body.use_memory,
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


def _system_allowlist(settings: SettingsDep) -> dict[str, Any]:
    """Non-money context the assistant may cite when no run metrics exist."""
    return {
        "assumptions_version": settings.assumptions_version,
        "d_max_m": settings.d_max_m,
        "location_scope": "Nairobi County (prototype; location-flexible uploads supported)",
        "model": settings.ollama_primary_model,
    }


@router.post("/assistant/chat")
def assistant_chat(
    body: AssistantChatRequest,
    store: StoreDep,
    settings: SettingsDep,
    ctx: ContextDep,
) -> dict:
    """
    Underwriter assistant for the floating chat UI.

    Grounds answers on:
    - frozen run allowlist when ``run_id`` is provided and metrics exist
    - RAG knowledge documents
    - session memory
    - Ollama primary model (Qwen by default)

    Never invents CAT money figures outside the allowlist.
    """
    enforce_permission(ctx, "query")
    from packages.rag.config import configure_rag

    configure_rag(settings.rag_settings())

    allowlist: dict[str, Any] = _system_allowlist(settings)
    run_id: Optional[str] = None
    ollama_degraded = False
    grounded_on_run = False
    client_allow = allowlist_from_client_metrics(body.client_metrics)

    if body.run_id:
        run = store.get_run(body.run_id)
        if run is None:
            if client_allow:
                allowlist = {**allowlist, **client_allow}
                grounded_on_run = True
                run_id = body.run_id
            else:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        "run not found on server (API may have restarted). "
                        "Re-run the portfolio test or refresh with cached metrics."
                    ),
                )
        else:
            enforce_tenant(run, ctx)
            run_id = run.id
            ollama_degraded = bool(run.ollama_degraded)
            if run.metrics is not None:
                allowlist = {
                    **allowlist,
                    **(run.allowlist or get_allowlist(run.metrics)),
                }
                grounded_on_run = True
            elif client_allow:
                allowlist = {**allowlist, **client_allow}
                grounded_on_run = True
    elif client_allow:
        allowlist = {**allowlist, **client_allow}
        grounded_on_run = True

    session_id = body.session_id or run_id or f"ui-{ctx.actor}"
    result = answer_query(
        body.question,
        allowlist,
        ollama_host=settings.ollama_host,
        ollama_model=settings.ollama_primary_model,
        force_down=body.force_ollama_down or ollama_degraded,
        tenant_id=ctx.tenant_id,
        session_id=session_id,
        use_rag=body.use_rag,
        use_memory=body.use_memory,
    )
    append_audit(
        "assistant_chat",
        {
            "run_id": run_id,
            "blocked": result.get("blocked"),
            "ok": result.get("ok"),
            "source": result.get("source"),
            "grounded_on_run": grounded_on_run,
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
    return {
        "run_id": run_id,
        "session_id": session_id,
        "model": settings.ollama_primary_model,
        "grounded_on_run": grounded_on_run,
        **result,
    }
