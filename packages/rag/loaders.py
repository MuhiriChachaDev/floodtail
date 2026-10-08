"""Extract plain text from PDF, DOCX, legacy DOC (best-effort), and text files."""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = frozenset({".pdf", ".docx", ".doc", ".txt", ".md", ".csv", ".json"})


@dataclass(frozen=True)
class LoadedDocument:
    text: str
    filename: str
    content_type: str
    warnings: tuple[str, ...] = ()


def sniff_extension(filename: str, content_type: Optional[str] = None) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix in SUPPORTED_EXTENSIONS:
        return suffix
    ct = (content_type or "").lower()
    if "pdf" in ct:
        return ".pdf"
    if "wordprocessingml" in ct or "docx" in ct:
        return ".docx"
    if "msword" in ct:
        return ".doc"
    if "text/" in ct or "json" in ct or "csv" in ct:
        return ".txt"
    raise ValueError(
        f"Unsupported file type for {filename!r}. "
        f"Supported: {sorted(SUPPORTED_EXTENSIONS)}"
    )


def load_bytes(
    data: bytes,
    *,
    filename: str,
    content_type: Optional[str] = None,
) -> LoadedDocument:
    ext = sniff_extension(filename, content_type)
    warnings: list[str] = []

    if ext == ".pdf":
        text = _load_pdf(data)
    elif ext == ".docx":
        text = _load_docx(data)
    elif ext == ".doc":
        text, w = _load_doc_legacy(data)
        warnings.extend(w)
    else:
        text = data.decode("utf-8", errors="replace")

    text = _normalize_whitespace(text)
    if not text.strip():
        raise ValueError(f"No extractable text in {filename!r}")

    return LoadedDocument(
        text=text,
        filename=filename,
        content_type=content_type or _mime_for(ext),
        warnings=tuple(warnings),
    )


def load_file(path: Union[str, Path]) -> LoadedDocument:
    p = Path(path)
    return load_bytes(p.read_bytes(), filename=p.name)


def _mime_for(ext: str) -> str:
    return {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".csv": "text/csv",
        ".json": "application/json",
    }.get(ext, "application/octet-stream")


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _load_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise ImportError("pypdf is required for PDF ingest: pip install pypdf") from exc

    reader = PdfReader(io.BytesIO(data))
    pages: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            pages.append(page.extract_text() or "")
        except Exception as exc:  # noqa: BLE001
            logger.warning("PDF page %s extract failed: %s", i, exc)
            pages.append("")
    return "\n\n".join(pages)


def _load_docx(data: bytes) -> str:
    try:
        from docx import Document
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "python-docx is required for DOCX ingest: pip install python-docx"
        ) from exc

    doc = Document(io.BytesIO(data))
    parts: list[str] = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text and c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def _load_doc_legacy(data: bytes) -> tuple[str, list[str]]:
    """
    Best-effort legacy .doc extraction.

    Prefer converting to .docx upstream. Falls back to printable-string scrape
    from the OLE compound document.
    """
    warnings = [
        "Legacy .doc support is best-effort; prefer .docx or PDF for reliable ingest."
    ]
    # Prefer olefile WordDocument stream if available
    try:
        import olefile

        if olefile.isOleFile(io.BytesIO(data)):
            with olefile.OleFileIO(io.BytesIO(data)) as ole:
                if ole.exists("WordDocument"):
                    stream = ole.openstream("WordDocument").read()
                    text = _extract_printable(stream)
                    if len(text) >= 40:
                        return text, warnings
    except ImportError:
        warnings.append("olefile not installed; using raw printable scrape for .doc")
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"OLE extract failed: {exc}")

    text = _extract_printable(data)
    if len(text) < 40:
        raise ValueError(
            "Could not extract usable text from legacy .doc; convert to .docx or PDF"
        )
    return text, warnings


def _extract_printable(data: bytes) -> str:
    # Keep runs of printable ASCII / latin-1-ish text
    chars: list[str] = []
    for b in data:
        if 32 <= b < 127 or b in (9, 10, 13):
            chars.append(chr(b))
        else:
            chars.append(" ")
    raw = "".join(chars)
    # Collapse noise runs
    raw = re.sub(r"[^\S\n]{2,}", " ", raw)
    lines = [ln.strip() for ln in raw.splitlines() if len(ln.strip()) >= 4]
    return "\n".join(lines)
