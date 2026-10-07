"""XAI explanation routes — Phase E."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/runs/{run_id}/explanations/global")
def explanations_global(run_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={"status": "not_implemented", "phase": "A", "run_id": run_id, "next": "E"},
    )


@router.get("/runs/{run_id}/explanations/local/{loc_id}")
def explanations_local(run_id: str, loc_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={
            "status": "not_implemented",
            "phase": "A",
            "run_id": run_id,
            "loc_id": loc_id,
            "next": "E",
        },
    )
