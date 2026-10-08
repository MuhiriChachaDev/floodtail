"""Postgres + pgvector knowledge store with in-memory fallback."""

from __future__ import annotations

import json
import logging
import math
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Sequence
from uuid import uuid4

from packages.rag.config import RagSettings, get_rag_settings
from packages.rag.embeddings import Embeddings, build_embeddings

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DocumentRecord:
    id: str
    tenant_id: str
    filename: str
    content_type: str
    n_chunks: int
    byte_size: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)


@dataclass
class ChunkRecord:
    id: str
    document_id: str
    tenant_id: str
    chunk_index: int
    content: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0


class KnowledgeStore:
    """Abstract interface implemented by Postgres and in-memory backends."""

    backend: str
    embeddings: Embeddings

    def ensure_schema(self) -> None: ...

    def add_document(
        self,
        *,
        tenant_id: str,
        filename: str,
        content_type: str,
        chunks: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        byte_size: int = 0,
        metadata: Optional[dict[str, Any]] = None,
        chunk_metadata: Optional[Sequence[dict[str, Any]]] = None,
    ) -> DocumentRecord: ...

    def search(
        self,
        query_embedding: Sequence[float],
        *,
        tenant_id: str,
        k: int = 5,
        document_id: Optional[str] = None,
    ) -> list[ChunkRecord]: ...

    def list_documents(self, *, tenant_id: str) -> list[DocumentRecord]: ...

    def delete_document(self, document_id: str, *, tenant_id: str) -> bool: ...

    def health(self) -> dict[str, Any]: ...


class InMemoryKnowledgeStore(KnowledgeStore):
    """Thread-safe in-memory RAG store for tests / Postgres-down prototype."""

    backend = "memory"

    def __init__(self, embeddings: Optional[Embeddings] = None) -> None:
        self.embeddings = embeddings or build_embeddings(force_hash=True)
        self._lock = threading.RLock()
        self._docs: dict[str, DocumentRecord] = {}
        self._chunks: list[ChunkRecord] = []

    def ensure_schema(self) -> None:
        return None

    def add_document(
        self,
        *,
        tenant_id: str,
        filename: str,
        content_type: str,
        chunks: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        byte_size: int = 0,
        metadata: Optional[dict[str, Any]] = None,
        chunk_metadata: Optional[Sequence[dict[str, Any]]] = None,
    ) -> DocumentRecord:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")
        doc_id = str(uuid4())
        meta = dict(metadata or {})
        doc = DocumentRecord(
            id=doc_id,
            tenant_id=tenant_id,
            filename=filename,
            content_type=content_type,
            n_chunks=len(chunks),
            byte_size=byte_size,
            metadata=meta,
        )
        with self._lock:
            self._docs[doc_id] = doc
            for i, (content, emb) in enumerate(zip(chunks, embeddings)):
                cm = dict(chunk_metadata[i]) if chunk_metadata and i < len(chunk_metadata) else {}
                self._chunks.append(
                    ChunkRecord(
                        id=str(uuid4()),
                        document_id=doc_id,
                        tenant_id=tenant_id,
                        chunk_index=i,
                        content=content,
                        embedding=list(emb),
                        metadata=cm,
                    )
                )
        return doc

    def search(
        self,
        query_embedding: Sequence[float],
        *,
        tenant_id: str,
        k: int = 5,
        document_id: Optional[str] = None,
    ) -> list[ChunkRecord]:
        with self._lock:
            candidates = [
                c
                for c in self._chunks
                if c.tenant_id == tenant_id
                and (document_id is None or c.document_id == document_id)
            ]
        scored: list[ChunkRecord] = []
        for c in candidates:
            score = _cosine(query_embedding, c.embedding)
            scored.append(
                ChunkRecord(
                    id=c.id,
                    document_id=c.document_id,
                    tenant_id=c.tenant_id,
                    chunk_index=c.chunk_index,
                    content=c.content,
                    embedding=c.embedding,
                    metadata=dict(c.metadata),
                    score=score,
                )
            )
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[: max(1, k)]

    def list_documents(self, *, tenant_id: str) -> list[DocumentRecord]:
        with self._lock:
            return [d for d in self._docs.values() if d.tenant_id == tenant_id]

    def delete_document(self, document_id: str, *, tenant_id: str) -> bool:
        with self._lock:
            doc = self._docs.get(document_id)
            if doc is None or doc.tenant_id != tenant_id:
                return False
            del self._docs[document_id]
            self._chunks = [c for c in self._chunks if c.document_id != document_id]
            return True

    def health(self) -> dict[str, Any]:
        with self._lock:
            return {
                "ok": True,
                "backend": self.backend,
                "n_documents": len(self._docs),
                "n_chunks": len(self._chunks),
            }


class PostgresKnowledgeStore(KnowledgeStore):
    """pgvector-backed document + chunk store."""

    backend = "postgres"

    def __init__(
        self,
        settings: RagSettings,
        embeddings: Optional[Embeddings] = None,
    ) -> None:
        self.settings = settings
        self.embeddings = embeddings or build_embeddings(settings)
        self._conn = None
        self._ensure_psycopg()

    def _ensure_psycopg(self) -> None:
        try:
            import psycopg  # noqa: F401
            from pgvector.psycopg import register_vector  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "psycopg and pgvector required for Postgres RAG: "
                "pip install 'psycopg[binary]' pgvector"
            ) from exc

    def _connect(self):
        import psycopg
        from pgvector.psycopg import register_vector

        conn = psycopg.connect(
            self.settings.database_url(),
            autocommit=True,
            connect_timeout=3,
        )
        register_vector(conn)
        return conn

    @property
    def conn(self):
        if self._conn is None or self._conn.closed:
            self._conn = self._connect()
        return self._conn

    def ensure_schema(self) -> None:
        dim = self.settings.embedding_dim
        with self.conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_documents (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    content_type TEXT NOT NULL DEFAULT 'application/octet-stream',
                    byte_size INT NOT NULL DEFAULT 0,
                    n_chunks INT NOT NULL DEFAULT 0,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id UUID PRIMARY KEY,
                    document_id UUID NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
                    tenant_id TEXT NOT NULL,
                    chunk_index INT NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector({dim}),
                    metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS rag_chunks_tenant_idx
                ON rag_chunks (tenant_id)
                """
            )
            # HNSW needs rows; create if missing (ignore if dim mismatch on old DB)
            try:
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS rag_chunks_embedding_hnsw
                    ON rag_chunks USING hnsw (embedding vector_cosine_ops)
                    """
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not create HNSW index (ok for empty DB): %s", exc)

    def add_document(
        self,
        *,
        tenant_id: str,
        filename: str,
        content_type: str,
        chunks: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        byte_size: int = 0,
        metadata: Optional[dict[str, Any]] = None,
        chunk_metadata: Optional[Sequence[dict[str, Any]]] = None,
    ) -> DocumentRecord:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")
        doc_id = str(uuid4())
        meta = dict(metadata or {})
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO rag_documents
                    (id, tenant_id, filename, content_type, byte_size, n_chunks, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    doc_id,
                    tenant_id,
                    filename,
                    content_type,
                    byte_size,
                    len(chunks),
                    json.dumps(meta),
                ),
            )
            for i, (content, emb) in enumerate(zip(chunks, embeddings)):
                cm = dict(chunk_metadata[i]) if chunk_metadata and i < len(chunk_metadata) else {}
                cur.execute(
                    """
                    INSERT INTO rag_chunks
                        (id, document_id, tenant_id, chunk_index, content, embedding, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        str(uuid4()),
                        doc_id,
                        tenant_id,
                        i,
                        content,
                        list(emb),
                        json.dumps(cm),
                    ),
                )
        return DocumentRecord(
            id=doc_id,
            tenant_id=tenant_id,
            filename=filename,
            content_type=content_type,
            n_chunks=len(chunks),
            byte_size=byte_size,
            metadata=meta,
        )

    def search(
        self,
        query_embedding: Sequence[float],
        *,
        tenant_id: str,
        k: int = 5,
        document_id: Optional[str] = None,
    ) -> list[ChunkRecord]:
        sql = """
            SELECT id, document_id, tenant_id, chunk_index, content, embedding, metadata,
                   1 - (embedding <=> %s::vector) AS score
            FROM rag_chunks
            WHERE tenant_id = %s
        """
        params: list[Any] = [list(query_embedding), tenant_id]
        if document_id:
            sql += " AND document_id = %s"
            params.append(document_id)
        sql += " ORDER BY embedding <=> %s::vector LIMIT %s"
        params.extend([list(query_embedding), max(1, k)])

        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        out: list[ChunkRecord] = []
        for row in rows:
            meta = row[6] if isinstance(row[6], dict) else json.loads(row[6] or "{}")
            emb = list(row[5]) if row[5] is not None else []
            out.append(
                ChunkRecord(
                    id=str(row[0]),
                    document_id=str(row[1]),
                    tenant_id=row[2],
                    chunk_index=int(row[3]),
                    content=row[4],
                    embedding=emb,
                    metadata=meta,
                    score=float(row[7] or 0.0),
                )
            )
        return out

    def list_documents(self, *, tenant_id: str) -> list[DocumentRecord]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, tenant_id, filename, content_type, n_chunks, byte_size,
                       metadata, created_at
                FROM rag_documents
                WHERE tenant_id = %s
                ORDER BY created_at DESC
                """,
                (tenant_id,),
            )
            rows = cur.fetchall()
        docs: list[DocumentRecord] = []
        for row in rows:
            meta = row[6] if isinstance(row[6], dict) else json.loads(row[6] or "{}")
            docs.append(
                DocumentRecord(
                    id=str(row[0]),
                    tenant_id=row[1],
                    filename=row[2],
                    content_type=row[3],
                    n_chunks=int(row[4]),
                    byte_size=int(row[5] or 0),
                    metadata=meta,
                    created_at=row[7] or _utc_now(),
                )
            )
        return docs

    def delete_document(self, document_id: str, *, tenant_id: str) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                "DELETE FROM rag_documents WHERE id = %s AND tenant_id = %s",
                (document_id, tenant_id),
            )
            return cur.rowcount > 0

    def health(self) -> dict[str, Any]:
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM rag_documents")
                n_docs = int(cur.fetchone()[0])
                cur.execute("SELECT COUNT(*) FROM rag_chunks")
                n_chunks = int(cur.fetchone()[0])
            return {
                "ok": True,
                "backend": self.backend,
                "n_documents": n_docs,
                "n_chunks": n_chunks,
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "backend": self.backend, "error": str(exc)}


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return float(dot / (na * nb))


_store: Optional[KnowledgeStore] = None
_store_lock = threading.Lock()


def get_knowledge_store(
    settings: Optional[RagSettings] = None,
    *,
    force_memory: bool = False,
    reset: bool = False,
) -> KnowledgeStore:
    """
    Return a shared KnowledgeStore.

    Prefers Postgres+pgvector; falls back to in-memory when unavailable.
    """
    global _store
    with _store_lock:
        if reset:
            _store = None
        if _store is not None:
            return _store

        cfg = settings or get_rag_settings()
        if force_memory or cfg.force_memory:
            store: KnowledgeStore = InMemoryKnowledgeStore(
                embeddings=build_embeddings(cfg, force_hash=True)
            )
            store.ensure_schema()
            _store = store
            return _store

        try:
            pg = PostgresKnowledgeStore(cfg)
            pg.ensure_schema()
            _store = pg
            logger.info("RAG knowledge store: postgres+pgvector")
            return _store
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Postgres RAG unavailable (%s); using in-memory knowledge store",
                exc,
            )
            store = InMemoryKnowledgeStore(embeddings=build_embeddings(cfg, force_hash=True))
            store.ensure_schema()
            _store = store
            return _store


def reset_knowledge_store() -> None:
    global _store
    with _store_lock:
        _store = None
