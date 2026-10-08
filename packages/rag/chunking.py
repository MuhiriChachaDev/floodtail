"""Simple recursive character chunking (no LangChain dependency required)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    index: int
    content: str
    start_char: int
    end_char: int


_SEPARATORS = ("\n\n", "\n", ". ", " ", "")


def chunk_text(
    text: str,
    *,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[TextChunk]:
    """
    Split text into overlapping chunks preferring paragraph / sentence breaks.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    if chunk_size < 64:
        raise ValueError("chunk_size must be >= 64")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be in [0, chunk_size)")

    pieces = _split_recursive(cleaned, chunk_size)
    chunks: list[TextChunk] = []
    cursor = 0
    for i, piece in enumerate(pieces):
        start = cleaned.find(piece, cursor)
        if start < 0:
            start = cursor
        end = start + len(piece)
        chunks.append(TextChunk(index=i, content=piece.strip(), start_char=start, end_char=end))
        cursor = max(0, end - chunk_overlap)
    return [c for c in chunks if c.content]


def _split_recursive(text: str, chunk_size: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    for sep in _SEPARATORS:
        if sep == "":
            # Hard split
            out: list[str] = []
            for i in range(0, len(text), chunk_size):
                out.append(text[i : i + chunk_size])
            return out
        if sep not in text:
            continue
        parts = text.split(sep)
        merged: list[str] = []
        buf = ""
        for part in parts:
            candidate = part if not buf else f"{buf}{sep}{part}"
            if len(candidate) <= chunk_size:
                buf = candidate
            else:
                if buf:
                    merged.append(buf)
                if len(part) > chunk_size:
                    merged.extend(_split_recursive(part, chunk_size))
                    buf = ""
                else:
                    buf = part
        if buf:
            merged.append(buf)
        return merged
    return [text]
