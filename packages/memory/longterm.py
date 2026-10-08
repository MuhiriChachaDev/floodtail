"""Long-term semantic memory + chat history for the FloodTail agent."""

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
class MemoryRecord:
    id: str
    tenant_id: str
    session_id: str
    memory_type: str
    content: str
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)


@dataclass
class ChatMessage:
    id: str
    tenant_id: str
    session_id: str
    role: str
    content: str
    created_at: datetime = field(default_factory=_utc_now)


class AgentMemory:
    """Interface for long-term memory backends."""

    backend: str
    embeddings: Embeddings

    def ensure_schema(self) -> None: ...

    def remember(
        self,
        content: str,
        *,
        tenant_id: str,
        session_id: str,
        memory_type: str = "fact",
        metadata: Optional[dict[str, Any]] = None,
    ) -> MemoryRecord: ...

    def recall(
        self,
        query: str,
        *,
        tenant_id: str,
        session_id: Optional[str] = None,
        k: int = 5,
        memory_type: Optional[str] = None,
    ) -> list[MemoryRecord]: ...

    def add_message(
        self,
        *,
        tenant_id: str,
        session_id: str,
        role: str,
        content: str,
    ) -> ChatMessage: ...

    def get_messages(
        self,
        *,
        tenant_id: str,
        session_id: str,
        limit: int = 50,
    ) -> list[ChatMessage]: ...

    def clear_session(self, *, tenant_id: str, session_id: str) -> int: ...

    def health(self) -> dict[str, Any]: ...


class InMemoryAgentMemory(AgentMemory):
    backend = "memory"

    def __init__(self, embeddings: Optional[Embeddings] = None) -> None:
        self.embeddings = embeddings or build_embeddings(force_hash=True)
        self._lock = threading.RLock()
        self._memories: list[tuple[MemoryRecord, list[float]]] = []
        self._messages: list[ChatMessage] = []

    def ensure_schema(self) -> None:
        return None

    def remember(
        self,
        content: str,
        *,
        tenant_id: str,
        session_id: str,
        memory_type: str = "fact",
        metadata: Optional[dict[str, Any]] = None,
    ) -> MemoryRecord:
        text = (content or "").strip()
        if not text:
            raise ValueError("memory content is empty")
        emb = self.embeddings.embed_query(text)
        rec = MemoryRecord(
            id=str(uuid4()),
            tenant_id=tenant_id,
            session_id=session_id,
            memory_type=memory_type,
            content=text,
            metadata=dict(metadata or {}),
        )
        with self._lock:
            self._memories.append((rec, emb))
        return rec

    def recall(
        self,
        query: str,
        *,
        tenant_id: str,
        session_id: Optional[str] = None,
        k: int = 5,
        memory_type: Optional[str] = None,
    ) -> list[MemoryRecord]:
        q = (query or "").strip()
        if not q:
            return []
        q_emb = self.embeddings.embed_query(q)
        with self._lock:
            candidates = [
                (rec, emb)
                for rec, emb in self._memories
                if rec.tenant_id == tenant_id
                and (session_id is None or rec.session_id == session_id)
                and (memory_type is None or rec.memory_type == memory_type)
            ]
        scored: list[MemoryRecord] = []
        for rec, emb in candidates:
            score = _cosine(q_emb, emb)
            scored.append(
                MemoryRecord(
                    id=rec.id,
                    tenant_id=rec.tenant_id,
                    session_id=rec.session_id,
                    memory_type=rec.memory_type,
                    content=rec.content,
                    score=score,
                    metadata=dict(rec.metadata),
                    created_at=rec.created_at,
                )
            )
        scored.sort(key=lambda m: m.score, reverse=True)
        return scored[: max(1, k)]

    def add_message(
        self,
        *,
        tenant_id: str,
        session_id: str,
        role: str,
        content: str,
    ) -> ChatMessage:
        msg = ChatMessage(
            id=str(uuid4()),
            tenant_id=tenant_id,
            session_id=session_id,
            role=role,
            content=content,
        )
        with self._lock:
            self._messages.append(msg)
        return msg

    def get_messages(
        self,
        *,
        tenant_id: str,
        session_id: str,
        limit: int = 50,
    ) -> list[ChatMessage]:
        with self._lock:
            msgs = [
                m
                for m in self._messages
                if m.tenant_id == tenant_id and m.session_id == session_id
            ]
        return msgs[-max(1, limit) :]

    def clear_session(self, *, tenant_id: str, session_id: str) -> int:
        with self._lock:
            before_m = len(self._memories)
            before_c = len(self._messages)
            self._memories = [
                (r, e)
                for r, e in self._memories
                if not (r.tenant_id == tenant_id and r.session_id == session_id)
            ]
            self._messages = [
                m
                for m in self._messages
                if not (m.tenant_id == tenant_id and m.session_id == session_id)
            ]
            return (before_m - len(self._memories)) + (before_c - len(self._messages))

    def health(self) -> dict[str, Any]:
        with self._lock:
            return {
                "ok": True,
                "backend": self.backend,
                "n_memories": len(self._memories),
                "n_messages": len(self._messages),
            }


class PostgresAgentMemory(AgentMemory):
    """Postgres + pgvector long-term memory (LangChain-compatible surface)."""

    backend = "postgres"

    def __init__(
        self,
        settings: RagSettings,
        embeddings: Optional[Embeddings] = None,
    ) -> None:
        self.settings = settings
        self.embeddings = embeddings or build_embeddings(settings)
        self._conn = None
        try:
            import psycopg  # noqa: F401
            from pgvector.psycopg import register_vector  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "psycopg and pgvector required: pip install 'psycopg[binary]' pgvector"
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
                f"""
                CREATE TABLE IF NOT EXISTS agent_memories (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL DEFAULT 'fact',
                    content TEXT NOT NULL,
                    embedding vector({dim}),
                    metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_chat_messages (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS agent_memories_tenant_session_idx
                ON agent_memories (tenant_id, session_id)
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS agent_chat_tenant_session_idx
                ON agent_chat_messages (tenant_id, session_id, created_at)
                """
            )
            try:
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS agent_memories_embedding_hnsw
                    ON agent_memories USING hnsw (embedding vector_cosine_ops)
                    """
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not create memory HNSW index: %s", exc)

    def remember(
        self,
        content: str,
        *,
        tenant_id: str,
        session_id: str,
        memory_type: str = "fact",
        metadata: Optional[dict[str, Any]] = None,
    ) -> MemoryRecord:
        text = (content or "").strip()
        if not text:
            raise ValueError("memory content is empty")
        emb = self.embeddings.embed_query(text)
        mid = str(uuid4())
        meta = dict(metadata or {})
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_memories
                    (id, tenant_id, session_id, memory_type, content, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (mid, tenant_id, session_id, memory_type, text, list(emb), json.dumps(meta)),
            )
        return MemoryRecord(
            id=mid,
            tenant_id=tenant_id,
            session_id=session_id,
            memory_type=memory_type,
            content=text,
            metadata=meta,
        )

    def recall(
        self,
        query: str,
        *,
        tenant_id: str,
        session_id: Optional[str] = None,
        k: int = 5,
        memory_type: Optional[str] = None,
    ) -> list[MemoryRecord]:
        q = (query or "").strip()
        if not q:
            return []
        emb = self.embeddings.embed_query(q)
        sql = """
            SELECT id, tenant_id, session_id, memory_type, content, metadata, created_at,
                   1 - (embedding <=> %s::vector) AS score
            FROM agent_memories
            WHERE tenant_id = %s
        """
        params: list[Any] = [list(emb), tenant_id]
        if session_id is not None:
            sql += " AND session_id = %s"
            params.append(session_id)
        if memory_type is not None:
            sql += " AND memory_type = %s"
            params.append(memory_type)
        sql += " ORDER BY embedding <=> %s::vector LIMIT %s"
        params.extend([list(emb), max(1, k)])

        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        out: list[MemoryRecord] = []
        for row in rows:
            meta = row[5] if isinstance(row[5], dict) else json.loads(row[5] or "{}")
            out.append(
                MemoryRecord(
                    id=str(row[0]),
                    tenant_id=row[1],
                    session_id=row[2],
                    memory_type=row[3],
                    content=row[4],
                    metadata=meta,
                    created_at=row[6] or _utc_now(),
                    score=float(row[7] or 0.0),
                )
            )
        return out

    def add_message(
        self,
        *,
        tenant_id: str,
        session_id: str,
        role: str,
        content: str,
    ) -> ChatMessage:
        mid = str(uuid4())
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_chat_messages
                    (id, tenant_id, session_id, role, content)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (mid, tenant_id, session_id, role, content),
            )
        return ChatMessage(
            id=mid,
            tenant_id=tenant_id,
            session_id=session_id,
            role=role,
            content=content,
        )

    def get_messages(
        self,
        *,
        tenant_id: str,
        session_id: str,
        limit: int = 50,
    ) -> list[ChatMessage]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, tenant_id, session_id, role, content, created_at
                FROM agent_chat_messages
                WHERE tenant_id = %s AND session_id = %s
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (tenant_id, session_id, max(1, limit)),
            )
            rows = cur.fetchall()
        return [
            ChatMessage(
                id=str(r[0]),
                tenant_id=r[1],
                session_id=r[2],
                role=r[3],
                content=r[4],
                created_at=r[5] or _utc_now(),
            )
            for r in rows
        ]

    def clear_session(self, *, tenant_id: str, session_id: str) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                "DELETE FROM agent_memories WHERE tenant_id = %s AND session_id = %s",
                (tenant_id, session_id),
            )
            n1 = cur.rowcount
            cur.execute(
                "DELETE FROM agent_chat_messages WHERE tenant_id = %s AND session_id = %s",
                (tenant_id, session_id),
            )
            n2 = cur.rowcount
        return int(n1) + int(n2)

    def health(self) -> dict[str, Any]:
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM agent_memories")
                n_m = int(cur.fetchone()[0])
                cur.execute("SELECT COUNT(*) FROM agent_chat_messages")
                n_c = int(cur.fetchone()[0])
            return {
                "ok": True,
                "backend": self.backend,
                "n_memories": n_m,
                "n_messages": n_c,
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "backend": self.backend, "error": str(exc)}


# --- LangChain-facing helpers -------------------------------------------------


def langchain_chat_history(
    memory: AgentMemory,
    *,
    tenant_id: str,
    session_id: str,
):
    """
    Build a LangChain BaseChatMessageHistory adapter over AgentMemory.

    Requires langchain-core. Used by agent tools / query loops.
    """
    from langchain_core.chat_history import BaseChatMessageHistory
    from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

    class PostgresBackedChatHistory(BaseChatMessageHistory):
        def __init__(self) -> None:
            self.tenant_id = tenant_id
            self.session_id = session_id

        @property
        def messages(self) -> list[BaseMessage]:
            out: list[BaseMessage] = []
            for m in memory.get_messages(
                tenant_id=self.tenant_id, session_id=self.session_id
            ):
                if m.role == "assistant" or m.role == "ai":
                    out.append(AIMessage(content=m.content))
                elif m.role == "system":
                    out.append(SystemMessage(content=m.content))
                else:
                    out.append(HumanMessage(content=m.content))
            return out

        def add_message(self, message: BaseMessage) -> None:
            role = "user"
            if isinstance(message, AIMessage):
                role = "assistant"
            elif isinstance(message, SystemMessage):
                role = "system"
            memory.add_message(
                tenant_id=self.tenant_id,
                session_id=self.session_id,
                role=role,
                content=str(message.content),
            )

        def clear(self) -> None:
            # Clear chat only; keep semantic memories for the session
            if memory.backend == "postgres" and isinstance(memory, PostgresAgentMemory):
                with memory.conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM agent_chat_messages WHERE tenant_id = %s AND session_id = %s",
                        (self.tenant_id, self.session_id),
                    )
            elif isinstance(memory, InMemoryAgentMemory):
                with memory._lock:
                    memory._messages = [
                        m
                        for m in memory._messages
                        if not (
                            m.tenant_id == self.tenant_id
                            and m.session_id == self.session_id
                        )
                    ]

    return PostgresBackedChatHistory()


def remember(
    content: str,
    *,
    tenant_id: str,
    session_id: str,
    memory_type: str = "fact",
    metadata: Optional[dict[str, Any]] = None,
    store: Optional[AgentMemory] = None,
) -> MemoryRecord:
    mem = store or get_agent_memory()
    return mem.remember(
        content,
        tenant_id=tenant_id,
        session_id=session_id,
        memory_type=memory_type,
        metadata=metadata,
    )


def recall_memories(
    query: str,
    *,
    tenant_id: str,
    session_id: Optional[str] = None,
    k: int = 5,
    store: Optional[AgentMemory] = None,
) -> list[MemoryRecord]:
    mem = store or get_agent_memory()
    return mem.recall(query, tenant_id=tenant_id, session_id=session_id, k=k)


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return float(dot / (na * nb))


_memory: Optional[AgentMemory] = None
_memory_lock = threading.Lock()


def get_agent_memory(
    settings: Optional[RagSettings] = None,
    *,
    force_memory: bool = False,
    reset: bool = False,
) -> AgentMemory:
    global _memory
    with _memory_lock:
        if reset:
            _memory = None
        if _memory is not None:
            return _memory

        cfg = settings or get_rag_settings()
        if force_memory or cfg.force_memory:
            store: AgentMemory = InMemoryAgentMemory(
                embeddings=build_embeddings(cfg, force_hash=True)
            )
            store.ensure_schema()
            _memory = store
            return _memory

        try:
            pg = PostgresAgentMemory(cfg)
            pg.ensure_schema()
            _memory = pg
            logger.info("Agent long-term memory: postgres+pgvector")
            return _memory
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Postgres memory unavailable (%s); using in-memory agent memory",
                exc,
            )
            store = InMemoryAgentMemory(embeddings=build_embeddings(cfg, force_hash=True))
            store.ensure_schema()
            _memory = store
            return _memory


def reset_agent_memory() -> None:
    global _memory
    with _memory_lock:
        _memory = None
