"""Narrative + free-text query routes — Phase D."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/runs/{run_id}/narrative")
def get_narrative(run_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={"status": "not_implemented", "phase": "A", "run_id": run_id, "next": "D"},
    )


@router.post("/runs/{run_id}/query")
def query_run(run_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={"status": "not_implemented", "phase": "A", "run_id": run_id, "next": "D"},
    )
