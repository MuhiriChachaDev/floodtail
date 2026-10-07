"""Health and readiness probes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

router = APIRouter()

_ROOT = Path(__file__).resolve().parents[3]
_NAIROBI = _ROOT / "Nairobi_Data"


@router.get("/health")
def health() -> dict:
    """Liveness probe — confirms API process and starter data presence."""
    required = [
        "exposure_nairobi_with_hazard.csv",
        "nairobi_hotspots_geocoded.csv",
    ]
    missing = [f for f in required if not (_NAIROBI / f).exists()]
    return {
        "status": "ok" if not missing else "degraded",
        "env": "scaffold",
        "nairobi_data": str(_NAIROBI),
        "nairobi_data_ok": len(missing) == 0,
        "missing_files": missing,
        "phase": "0-scaffold",
        "streamlit": "removed",
        "frontend": "apps/web (empty Next.js scaffold)",
    }
