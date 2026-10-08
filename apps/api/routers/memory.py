"""Long-term agent memory routes (Postgres / in-memory)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from apps.api.deps import ContextDep, SettingsDep, enforce_permission
from packages.agents.tools.audit_tools import append_audit
from packages.agents.tools.memory_tools import tool_recall, tool_remember
from packages.memory.longterm import get_agent_memory
from packages.rag.config import configure_rag

router = APIRouter()


class RememberRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    session_id: str = Field(min_length=1, max_length=128)
    memory_type: str = Field(default="fact", max_length=64)
    metadata: Optional[dict] = None


class RecallRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    session_id: Optional[str] = Field(default=None, max_length=128)
    k: int = Field(default=5, ge=1, le=20)


class ChatAppendRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    role: str = Field(min_length=1, max_length=32)
    content: str = Field(min_length=1, max_length=16000)


def _sync(settings: SettingsDep) -> None:
    configure_rag(settings.rag_settings())


@router.post("/memory/remember")
def remember_fact(
    body: RememberRequest,
    settings: SettingsDep,
    ctx: ContextDep,
) -> dict:
    enforce_permission(ctx, "memory:write")
    _sync(settings)
    result = tool_remember(
        body.content,
        tenant_id=ctx.tenant_id,
        session_id=body.session_id,
        memory_type=body.memory_type,
        metadata=body.metadata,
    )
    append_audit(
        "memory_remember",
        {
            "memory_id": result["memory_id"],
            "session_id": body.session_id,
            "tenant_id": ctx.tenant_id,
            "actor": ctx.actor,
        },
    )
    return result


@router.post("/memory/recall")
def recall(
    body: RecallRequest,
    settings: SettingsDep,
    ctx: ContextDep,
) -> dict:
    enforce_permission(ctx, "memory:read")
    _sync(settings)
    return tool_recall(
        body.query,
        tenant_id=ctx.tenant_id,
        session_id=body.session_id,
        k=body.k,
    )


@router.post("/memory/chat")
def append_chat(
    body: ChatAppendRequest,
    settings: SettingsDep,
    ctx: ContextDep,
) -> dict:
    enforce_permission(ctx, "memory:write")
    _sync(settings)
    mem = get_agent_memory(settings.rag_settings())
    msg = mem.add_message(
        tenant_id=ctx.tenant_id,
        session_id=body.session_id,
        role=body.role,
        content=body.content,
    )
    return {
        "message_id": msg.id,
        "session_id": msg.session_id,
        "role": msg.role,
        "backend": mem.backend,
    }


@router.get("/memory/sessions/{session_id}/messages")
def list_messages(
    session_id: str,
    settings: SettingsDep,
    ctx: ContextDep,
    limit: int = 50,
) -> dict:
    enforce_permission(ctx, "memory:read")
    _sync(settings)
    mem = get_agent_memory(settings.rag_settings())
    msgs = mem.get_messages(
        tenant_id=ctx.tenant_id,
        session_id=session_id,
        limit=min(max(limit, 1), 200),
    )
    return {
        "session_id": session_id,
        "backend": mem.backend,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in msgs
        ],
    }


@router.delete("/memory/sessions/{session_id}")
def clear_session(
    session_id: str,
    settings: SettingsDep,
    ctx: ContextDep,
) -> dict:
    enforce_permission(ctx, "memory:write")
    _sync(settings)
    mem = get_agent_memory(settings.rag_settings())
    n = mem.clear_session(tenant_id=ctx.tenant_id, session_id=session_id)
    append_audit(
        "memory_clear",
        {"session_id": session_id, "cleared": n, "tenant_id": ctx.tenant_id},
    )
    return {"cleared": n, "session_id": session_id}


@router.get("/memory/health")
def memory_health(settings: SettingsDep, ctx: ContextDep) -> dict:
    enforce_permission(ctx, "memory:read")
    _sync(settings)
    mem = get_agent_memory(settings.rag_settings())
    return mem.health()
