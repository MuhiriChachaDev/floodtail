"""Knowledge / RAG document ingest + search routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from apps.api.deps import ContextDep, SettingsDep, enforce_permission
from packages.agents.tools.audit_tools import append_audit
from packages.agents.tools.rag_tools import tool_ingest_document, tool_search_knowledge
from packages.rag.config import configure_rag
from packages.rag.store import get_knowledge_store

router = APIRouter()


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    k: int = Field(default=5, ge=1, le=20)
    document_id: Optional[str] = None


def _sync_rag_settings(settings: SettingsDep) -> None:
    configure_rag(settings.rag_settings())


@router.post("/knowledge/documents")
async def upload_document(
    settings: SettingsDep,
    ctx: ContextDep,
    file: UploadFile = File(...),
    metadata_json: Optional[str] = Form(default=None),
) -> dict:
    """
    Ingest a PDF / DOCX / DOC / text file into the RAG knowledge store.

    Chunks + embeds the document for agent retrieval. Does not invent CAT math.
    """
    enforce_permission(ctx, "knowledge:write")
    _sync_rag_settings(settings)

    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty file")
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=400, detail=f"Upload exceeds {settings.max_upload_mb} MB"
        )

    meta: dict = {}
    if metadata_json:
        import json

        try:
            parsed = json.loads(metadata_json)
            if isinstance(parsed, dict):
                meta = parsed
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="metadata_json must be JSON object") from exc

    try:
        result = tool_ingest_document(
            data,
            filename=file.filename or "upload.bin",
            tenant_id=ctx.tenant_id,
            content_type=file.content_type,
            metadata=meta,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Missing parser dependency: {exc}",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Ingest failed: {exc}") from exc

    append_audit(
        "knowledge_ingest",
        {
            "document_id": result["document_id"],
            "filename": result["filename"],
            "n_chunks": result["n_chunks"],
            "backend": result["backend"],
            "actor": ctx.actor,
            "tenant_id": ctx.tenant_id,
        },
    )
    return {"document": result}


@router.get("/knowledge/documents")
def list_documents(settings: SettingsDep, ctx: ContextDep) -> dict:
    enforce_permission(ctx, "knowledge:read")
    _sync_rag_settings(settings)
    store = get_knowledge_store(settings.rag_settings())
    docs = store.list_documents(tenant_id=ctx.tenant_id)
    return {
        "backend": store.backend,
        "documents": [
            {
                "id": d.id,
                "filename": d.filename,
                "content_type": d.content_type,
                "n_chunks": d.n_chunks,
                "byte_size": d.byte_size,
                "metadata": d.metadata,
                "created_at": d.created_at.isoformat(),
            }
            for d in docs
        ],
    }


@router.delete("/knowledge/documents/{document_id}")
def delete_document(
    document_id: str,
    settings: SettingsDep,
    ctx: ContextDep,
) -> dict:
    enforce_permission(ctx, "knowledge:write")
    _sync_rag_settings(settings)
    store = get_knowledge_store(settings.rag_settings())
    ok = store.delete_document(document_id, tenant_id=ctx.tenant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="document not found")
    append_audit(
        "knowledge_delete",
        {"document_id": document_id, "tenant_id": ctx.tenant_id, "actor": ctx.actor},
    )
    return {"deleted": True, "document_id": document_id}


@router.post("/knowledge/search")
def search_documents(
    body: SearchRequest,
    settings: SettingsDep,
    ctx: ContextDep,
) -> dict:
    enforce_permission(ctx, "knowledge:read")
    _sync_rag_settings(settings)
    result = tool_search_knowledge(
        body.query,
        tenant_id=ctx.tenant_id,
        k=body.k,
        document_id=body.document_id,
    )
    return result


@router.get("/knowledge/health")
def knowledge_health(settings: SettingsDep, ctx: ContextDep) -> dict:
    enforce_permission(ctx, "knowledge:read")
    _sync_rag_settings(settings)
    store = get_knowledge_store(settings.rag_settings())
    return store.health()
