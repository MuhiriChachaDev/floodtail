"""LangChain tools for RAG knowledge ingest and retrieval."""

from __future__ import annotations

from typing import Any, Optional

from packages.rag.ingest import ingest_bytes
from packages.rag.retrieve import format_context, search_knowledge
from packages.rag.store import get_knowledge_store


def tool_ingest_document(
    data: bytes,
    *,
    filename: str,
    tenant_id: str,
    content_type: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Ingest a PDF/DOCX/text document into the knowledge store."""
    result = ingest_bytes(
        data,
        filename=filename,
        tenant_id=tenant_id,
        content_type=content_type,
        metadata=metadata,
    )
    doc = result.document
    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "n_chunks": doc.n_chunks,
        "backend": result.backend,
        "embedding_degraded": result.embedding_degraded,
        "warnings": result.warnings,
    }


def tool_search_knowledge(
    query: str,
    *,
    tenant_id: str,
    k: int = 5,
    document_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Semantic search over ingested insurer documents.

    Returns grounded passages — does NOT invent loss / EP / AAL figures.
    """
    hits = search_knowledge(
        query,
        tenant_id=tenant_id,
        k=k,
        document_id=document_id,
    )
    return {
        "query": query,
        "n_hits": len(hits),
        "context": format_context(hits),
        "hits": [
            {
                "content": h.content,
                "score": round(h.score, 4),
                "document_id": h.document_id,
                "chunk_index": h.chunk_index,
                "filename": h.filename,
            }
            for h in hits
        ],
        "backend": get_knowledge_store().backend,
    }


try:
    from langchain_core.tools import tool

    @tool
    def search_knowledge_tool(query: str, tenant_id: str = "default", k: int = 5) -> str:
        """Search ingested PDF/DOC knowledge for CAT / underwriting context."""
        result = tool_search_knowledge(query, tenant_id=tenant_id, k=k)
        if not result["hits"]:
            return "No matching document passages found."
        return result["context"] or "No matching document passages found."

    @tool
    def list_knowledge_tool(tenant_id: str = "default") -> str:
        """List documents currently in the knowledge store for a tenant."""
        store = get_knowledge_store()
        docs = store.list_documents(tenant_id=tenant_id)
        if not docs:
            return "No documents ingested."
        lines = [
            f"- {d.filename} id={d.id} chunks={d.n_chunks}" for d in docs
        ]
        return "\n".join(lines)

except ImportError:  # pragma: no cover
    pass
