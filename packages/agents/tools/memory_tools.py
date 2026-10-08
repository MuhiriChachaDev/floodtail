"""LangChain tools for long-term agent memory (Postgres / in-memory)."""

from __future__ import annotations

from typing import Any, Optional

from packages.memory.longterm import get_agent_memory, langchain_chat_history


def tool_remember(
    content: str,
    *,
    tenant_id: str,
    session_id: str,
    memory_type: str = "fact",
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Persist a long-term memory fact/summary for later recall."""
    mem = get_agent_memory()
    rec = mem.remember(
        content,
        tenant_id=tenant_id,
        session_id=session_id,
        memory_type=memory_type,
        metadata=metadata,
    )
    return {
        "memory_id": rec.id,
        "session_id": rec.session_id,
        "memory_type": rec.memory_type,
        "backend": mem.backend,
    }


def tool_recall(
    query: str,
    *,
    tenant_id: str,
    session_id: Optional[str] = None,
    k: int = 5,
) -> dict[str, Any]:
    """Semantically recall prior agent memories relevant to a query."""
    mem = get_agent_memory()
    hits = mem.recall(
        query,
        tenant_id=tenant_id,
        session_id=session_id,
        k=k,
    )
    return {
        "query": query,
        "n_hits": len(hits),
        "backend": mem.backend,
        "memories": [
            {
                "id": h.id,
                "content": h.content,
                "score": round(h.score, 4),
                "memory_type": h.memory_type,
                "session_id": h.session_id,
            }
            for h in hits
        ],
        "context": "\n".join(f"- ({h.memory_type}) {h.content}" for h in hits),
    }


def tool_append_chat(
    *,
    tenant_id: str,
    session_id: str,
    role: str,
    content: str,
) -> dict[str, Any]:
    mem = get_agent_memory()
    msg = mem.add_message(
        tenant_id=tenant_id,
        session_id=session_id,
        role=role,
        content=content,
    )
    return {"message_id": msg.id, "backend": mem.backend}


def get_session_chat_history(*, tenant_id: str, session_id: str):
    """LangChain BaseChatMessageHistory for a tenant/session."""
    return langchain_chat_history(
        get_agent_memory(),
        tenant_id=tenant_id,
        session_id=session_id,
    )


try:
    from langchain_core.tools import tool

    @tool
    def remember_tool(
        content: str,
        session_id: str,
        tenant_id: str = "default",
        memory_type: str = "fact",
    ) -> str:
        """Store a long-term memory about this underwriting / CAT session."""
        result = tool_remember(
            content,
            tenant_id=tenant_id,
            session_id=session_id,
            memory_type=memory_type,
        )
        return f"Remembered {result['memory_id']} ({result['memory_type']})"

    @tool
    def recall_memory_tool(
        query: str,
        tenant_id: str = "default",
        session_id: str = "",
        k: int = 5,
    ) -> str:
        """Recall prior session memories relevant to the query."""
        result = tool_recall(
            query,
            tenant_id=tenant_id,
            session_id=session_id or None,
            k=k,
        )
        if not result["memories"]:
            return "No memories found."
        return result["context"]

except ImportError:  # pragma: no cover
    pass
