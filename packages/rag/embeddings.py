"""Embedding providers: Ollama primary, deterministic hash fallback for offline/tests."""

from __future__ import annotations

import hashlib
import logging
import math
import struct
from typing import Optional, Protocol, Sequence

import httpx

from packages.rag.config import RagSettings, get_rag_settings

logger = logging.getLogger(__name__)


class Embeddings(Protocol):
    dim: int

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class HashEmbeddings:
    """
    Deterministic bag-of-tokens hashing trick.

    Not semantic-quality; used when Ollama embeddings are unavailable so ingest
    and tests still work. Same text → same vector.
    """

    def __init__(self, dim: int = 768) -> None:
        if dim < 32:
            raise ValueError("embedding dim must be >= 32")
        self.dim = dim

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = _tokenize(text)
        if not tokens:
            tokens = ["_empty_"]
        for tok in tokens:
            digest = hashlib.sha256(tok.encode("utf-8")).digest()
            # Use 8-byte slices to pick index + signed contribution
            for i in range(0, min(len(digest), 24), 8):
                idx = struct.unpack_from(">I", digest, i)[0] % self.dim
                sign = 1.0 if digest[i + 4] % 2 == 0 else -1.0
                vec[idx] += sign
        return _l2_normalize(vec)


class OllamaEmbeddings:
    """Ollama /api/embeddings wrapper (e.g. nomic-embed-text)."""

    def __init__(
        self,
        *,
        host: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        dim: int = 768,
        timeout_s: float = 60.0,
    ) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.dim = dim
        self.timeout_s = timeout_s

    def available(self) -> bool:
        try:
            with httpx.Client(timeout=min(5.0, self.timeout_s)) as client:
                r = client.get(f"{self.host}/api/tags")
                r.raise_for_status()
                names = [m.get("name", "") for m in r.json().get("models", [])]
                return any(
                    self.model == n or n.startswith(self.model.split(":")[0]) for n in names
                )
        except Exception:  # noqa: BLE001
            return False

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        body = {"model": self.model, "prompt": text}
        with httpx.Client(timeout=self.timeout_s) as client:
            r = client.post(f"{self.host}/api/embeddings", json=body)
            r.raise_for_status()
            emb = r.json().get("embedding")
        if not isinstance(emb, list) or not emb:
            raise RuntimeError("Ollama returned empty embedding")
        vec = [float(x) for x in emb]
        if len(vec) != self.dim:
            # Pad / truncate to configured dim so pgvector column stays consistent
            if len(vec) < self.dim:
                vec = vec + [0.0] * (self.dim - len(vec))
            else:
                vec = vec[: self.dim]
            logger.warning(
                "Ollama embedding dim %s != configured %s; padded/truncated",
                len(emb),
                self.dim,
            )
        return _l2_normalize(vec)


class FallbackEmbeddings:
    """Try Ollama; on failure use HashEmbeddings and set degraded=True."""

    def __init__(self, primary: OllamaEmbeddings, fallback: HashEmbeddings) -> None:
        self.primary = primary
        self.fallback = fallback
        self.dim = primary.dim
        self.degraded = False
        self.last_error: Optional[str] = None

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        try:
            out = self.primary.embed_documents(texts)
            self.degraded = False
            self.last_error = None
            return out
        except Exception as exc:  # noqa: BLE001
            self.degraded = True
            self.last_error = str(exc)
            logger.warning("Ollama embeddings failed (%s); using hash fallback", exc)
            return self.fallback.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        try:
            out = self.primary.embed_query(text)
            self.degraded = False
            self.last_error = None
            return out
        except Exception as exc:  # noqa: BLE001
            self.degraded = True
            self.last_error = str(exc)
            logger.warning("Ollama embed_query failed (%s); using hash fallback", exc)
            return self.fallback.embed_query(text)


def build_embeddings(
    settings: Optional[RagSettings] = None,
    *,
    force_hash: bool = False,
) -> Embeddings:
    cfg = settings or get_rag_settings()
    hasher = HashEmbeddings(dim=cfg.embedding_dim)
    if force_hash:
        return hasher
    ollama = OllamaEmbeddings(
        host=cfg.ollama_host,
        model=cfg.embedding_model,
        dim=cfg.embedding_dim,
    )
    return FallbackEmbeddings(ollama, hasher)


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in text.split() if t.strip()]


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]
