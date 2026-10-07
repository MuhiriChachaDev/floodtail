"""Health and readiness probes."""

from __future__ import annotations

from fastapi import APIRouter

from apps.api.settings import get_settings
from apps.api.store import get_store

router = APIRouter()


@router.get("/health")
def health() -> dict:
    """Liveness probe — settings, store, starter data presence."""
    settings = get_settings()
    store = get_store()
    nairobi = settings.nairobi_data_dir
    required = [
        "exposure_nairobi_with_hazard.csv",
        "nairobi_hotspots_geocoded.csv",
    ]
    missing = [f for f in required if not (nairobi / f).exists()]
    profile = settings.assumptions_profile()
    return {
        "status": "ok" if not missing else "degraded",
        "env": settings.env,
        "phase": "C-ml",
        "streamlit": "removed",
        "frontend": "apps/web (empty Next.js scaffold)",
        "nairobi_data": str(nairobi),
        "nairobi_data_ok": len(missing) == 0,
        "missing_files": missing,
        "models_dir": str(settings.models_dir),
        "models_dir_ok": settings.models_dir.exists(),
        "assumptions_version": profile.assumptions_version,
        "d_max_m": profile.d_max_m,
        "return_periods": profile.return_periods,
        "capital_policy": profile.capital.model_dump(),
        "ollama_host": settings.ollama_host,
        "store": store.stats(),
    }
