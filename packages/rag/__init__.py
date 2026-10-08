"""RAG ingest / retrieve for unstructured insurer documents (PDF, DOCX, text).

Uses Postgres + pgvector when available; falls back to in-memory for tests
and offline prototype. Embeddings prefer Ollama; hash embeddings are used
when Ollama is unavailable so the pipeline still runs.
"""

from packages.rag.ingest import IngestResult, ingest_bytes, ingest_file
from packages.rag.retrieve import RetrievedChunk, search_knowledge
from packages.rag.store import KnowledgeStore, get_knowledge_store

__all__ = [
    "IngestResult",
    "KnowledgeStore",
    "RetrievedChunk",
    "get_knowledge_store",
    "ingest_bytes",
    "ingest_file",
    "search_knowledge",
]
