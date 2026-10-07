"""Audit chain routes — Phase E."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/audit")
def get_audit() -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={
            "status": "not_implemented",
            "phase": "A",
            "next": "E",
            "detail": "SHA-256 audit chain lands in Phase E.",
        },
    )
