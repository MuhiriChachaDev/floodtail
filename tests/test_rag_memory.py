"""RAG ingest/retrieve + long-term memory (in-memory backend)."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.settings import get_settings
from packages.memory.longterm import (
    InMemoryAgentMemory,
    get_agent_memory,
    reset_agent_memory,
)
from packages.rag.chunking import chunk_text
from packages.rag.config import RagSettings, configure_rag, reset_rag_settings
from packages.rag.embeddings import HashEmbeddings
from packages.rag.ingest import ingest_bytes
from packages.rag.retrieve import search_knowledge
from packages.rag.store import (
    InMemoryKnowledgeStore,
    get_knowledge_store,
    reset_knowledge_store,
)

client = TestClient(app)


def setup_function() -> None:
    os.environ["RAG_FORCE_MEMORY"] = "true"
    os.environ["RAG_EMBEDDING_DIM"] = "64"
    get_settings.cache_clear()
    reset_rag_settings()
    reset_knowledge_store()
    reset_agent_memory()
    configure_rag(RagSettings(force_memory=True, embedding_dim=64))
    get_knowledge_store(force_memory=True)
    get_agent_memory(force_memory=True)


def teardown_function() -> None:
    reset_knowledge_store()
    reset_agent_memory()
    reset_rag_settings()
    get_settings.cache_clear()
    os.environ.pop("RAG_FORCE_MEMORY", None)
    os.environ.pop("RAG_EMBEDDING_DIM", None)


def test_chunk_text_overlap() -> None:
    text = ("Nairobi pluvial flood exposure. " * 40).strip()
    chunks = chunk_text(text, chunk_size=120, chunk_overlap=20)
    assert len(chunks) >= 2
    assert all(c.content for c in chunks)


def test_hash_embeddings_deterministic() -> None:
    emb = HashEmbeddings(dim=64)
    a = emb.embed_query("treaty attachment 5 percent of TIV")
    b = emb.embed_query("treaty attachment 5 percent of TIV")
    c = emb.embed_query("completely unrelated gardening tips")
    assert a == b
    assert a != c
    assert len(a) == 64


def test_ingest_and_search_in_memory() -> None:
    store = InMemoryKnowledgeStore(embeddings=HashEmbeddings(dim=64))
    text = (
        "XL treaty attaches at 5% of portfolio TIV with a limit of 15% of TIV. "
        "Nairobi informal settlements have elevated pluvial flood susceptibility. "
        "Housing class informal uses higher damage ratios at the same depth."
    ).encode("utf-8")
    result = ingest_bytes(
        text,
        filename="treaty_notes.txt",
        tenant_id="default",
        content_type="text/plain",
        store=store,
        settings=RagSettings(force_memory=True, embedding_dim=64, chunk_size=200, chunk_overlap=40),
    )
    assert result.document.n_chunks >= 1
    assert result.backend == "memory"

    hits = search_knowledge(
        "What is the XL treaty attachment?",
        tenant_id="default",
        k=3,
        store=store,
        settings=RagSettings(force_memory=True, embedding_dim=64),
    )
    assert hits
    joined = " ".join(h.content.lower() for h in hits)
    assert "attachment" in joined or "tiv" in joined or "treaty" in joined


def test_longterm_memory_recall() -> None:
    mem = InMemoryAgentMemory(embeddings=HashEmbeddings(dim=64))
    mem.remember(
        "Underwriter prefers capital floor at RP100 for Nairobi book",
        tenant_id="default",
        session_id="run-1",
        memory_type="preference",
    )
    mem.remember(
        "Portfolio uses synthetic Nairobi starter kit exposures",
        tenant_id="default",
        session_id="run-1",
        memory_type="fact",
    )
    hits = mem.recall(
        "capital floor preference",
        tenant_id="default",
        session_id="run-1",
        k=2,
    )
    assert hits
    assert "capital" in hits[0].content.lower() or "RP100" in hits[0].content

    mem.add_message(
        tenant_id="default",
        session_id="run-1",
        role="user",
        content="What floor did we agree?",
    )
    msgs = mem.get_messages(tenant_id="default", session_id="run-1")
    assert len(msgs) == 1


def test_knowledge_api_upload_and_search() -> None:
    payload = (
        b"Treaty wording: attachment is five percent of total insured value. "
        b"Limit layer covers fifteen percent of TIV for Nairobi flood XL."
    )
    r = client.post(
        "/v1/knowledge/documents",
        files={"file": ("notes.txt", payload, "text/plain")},
        headers={"X-Floodtail-Role": "underwriter", "X-Floodtail-Tenant": "default"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["document"]["n_chunks"] >= 1
    doc_id = body["document"]["document_id"]

    listed = client.get(
        "/v1/knowledge/documents",
        headers={"X-Floodtail-Role": "underwriter", "X-Floodtail-Tenant": "default"},
    )
    assert listed.status_code == 200
    assert any(d["id"] == doc_id for d in listed.json()["documents"])

    search = client.post(
        "/v1/knowledge/search",
        json={"query": "treaty attachment percent TIV", "k": 3},
        headers={"X-Floodtail-Role": "underwriter", "X-Floodtail-Tenant": "default"},
    )
    assert search.status_code == 200
    assert search.json()["n_hits"] >= 1


def test_memory_api_remember_recall() -> None:
    r = client.post(
        "/v1/memory/remember",
        json={
            "content": "Client wants XL quote for Kibera hotspot concentration",
            "session_id": "sess-api-1",
            "memory_type": "fact",
        },
        headers={"X-Floodtail-Role": "underwriter", "X-Floodtail-Tenant": "default"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["memory_id"]

    recall = client.post(
        "/v1/memory/recall",
        json={"query": "Kibera XL quote", "session_id": "sess-api-1", "k": 3},
        headers={"X-Floodtail-Role": "underwriter", "X-Floodtail-Tenant": "default"},
    )
    assert recall.status_code == 200
    assert recall.json()["n_hits"] >= 1
