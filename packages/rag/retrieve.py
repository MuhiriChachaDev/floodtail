"""Semantic retrieval over ingested knowledge chunks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from packages.rag.config import RagSettings, get_rag_settings
from packages.rag.store import KnowledgeStore, get_knowledge_store


@dataclass
class RetrievedChunk:
    content: str
    score: float
    document_id: str
    chunk_index: int
    filename: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def search_knowledge(
    query: str,
    *,
    tenant_id: str,
    k: int = 5,
    document_id: Optional[str] = None,
    store: Optional[KnowledgeStore] = None,
    settings: Optional[RagSettings] = None,
) -> list[RetrievedChunk]:
    """Embed query and return top-k similar chunks for the tenant."""
    if not (query or "").strip():
        return []
    cfg = settings or get_rag_settings()
    knowledge = store or get_knowledge_store(cfg)
    q_emb = knowledge.embeddings.embed_query(query.strip())
    hits = knowledge.search(
        q_emb,
        tenant_id=tenant_id,
        k=k,
        document_id=document_id,
    )
    # Resolve filenames from chunk metadata when present
    out: list[RetrievedChunk] = []
    for h in hits:
        out.append(
            RetrievedChunk(
                content=h.content,
                score=h.score,
                document_id=h.document_id,
                chunk_index=h.chunk_index,
                filename=str(h.metadata.get("filename") or ""),
                metadata=dict(h.metadata),
            )
        )
    return out


def format_context(chunks: list[RetrievedChunk], *, max_chars: int = 6000) -> str:
    """Format retrieved chunks as grounded context for an LLM prompt."""
    if not chunks:
        return ""
    parts: list[str] = []
    used = 0
    for i, c in enumerate(chunks, start=1):
        header = f"[{i}] doc={c.filename or c.document_id} score={c.score:.3f}"
        block = f"{header}\n{c.content.strip()}"
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block) + 2
    return "\n\n---\n\n".join(parts)
