"""Document ingest: load → chunk → embed → store."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

from packages.rag.chunking import chunk_text
from packages.rag.config import RagSettings, get_rag_settings
from packages.rag.loaders import load_bytes, load_file
from packages.rag.store import DocumentRecord, KnowledgeStore, get_knowledge_store


@dataclass
class IngestResult:
    document: DocumentRecord
    warnings: list[str] = field(default_factory=list)
    embedding_degraded: bool = False
    backend: str = "memory"


def ingest_bytes(
    data: bytes,
    *,
    filename: str,
    tenant_id: str,
    content_type: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    store: Optional[KnowledgeStore] = None,
    settings: Optional[RagSettings] = None,
) -> IngestResult:
    cfg = settings or get_rag_settings()
    knowledge = store or get_knowledge_store(cfg)
    loaded = load_bytes(data, filename=filename, content_type=content_type)
    warnings = list(loaded.warnings)

    pieces = chunk_text(
        loaded.text,
        chunk_size=cfg.chunk_size,
        chunk_overlap=cfg.chunk_overlap,
    )
    if not pieces:
        raise ValueError(f"No chunks produced from {filename!r}")

    texts = [p.content for p in pieces]
    vectors = knowledge.embeddings.embed_documents(texts)
    degraded = bool(getattr(knowledge.embeddings, "degraded", False))

    chunk_meta = [
        {
            "start_char": p.start_char,
            "end_char": p.end_char,
            "filename": loaded.filename,
        }
        for p in pieces
    ]
    meta = {
        **(metadata or {}),
        "filename": loaded.filename,
        "content_type": loaded.content_type,
    }
    doc = knowledge.add_document(
        tenant_id=tenant_id,
        filename=loaded.filename,
        content_type=loaded.content_type,
        chunks=texts,
        embeddings=vectors,
        byte_size=len(data),
        metadata=meta,
        chunk_metadata=chunk_meta,
    )
    return IngestResult(
        document=doc,
        warnings=warnings,
        embedding_degraded=degraded,
        backend=knowledge.backend,
    )


def ingest_file(
    path: Union[str, Path],
    *,
    tenant_id: str,
    metadata: Optional[dict[str, Any]] = None,
    store: Optional[KnowledgeStore] = None,
    settings: Optional[RagSettings] = None,
) -> IngestResult:
    p = Path(path)
    return ingest_bytes(
        p.read_bytes(),
        filename=p.name,
        tenant_id=tenant_id,
        metadata=metadata,
        store=store,
        settings=settings,
    )
