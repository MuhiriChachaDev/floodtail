"""Health and readiness probes."""

from __future__ import annotations

from fastapi import APIRouter

from apps.api.settings import get_settings
from apps.api.store import get_store
from packages.llm.ollama_client import OllamaClient
from packages.ml.registry import ModelRegistry
from packages.security.audit_log import get_audit_chain

router = APIRouter()


def _registry_status(models_dir) -> dict:
    """Pinned hazard/vulnerability presence + integrity for readiness."""
    reg = ModelRegistry(models_dir)
    hazard_pinned = reg.get_pinned("hazard")
    vuln_pinned = reg.get_pinned("vulnerability")
    hazard_ok = bool(hazard_pinned) and reg.verify_integrity("hazard", hazard_pinned)
    vuln_ok = bool(vuln_pinned) and reg.verify_integrity("vulnerability", vuln_pinned)
    listed = reg.list_models()
    return {
        "present": models_dir.exists(),
        "hazard_pinned": hazard_pinned,
        "vulnerability_pinned": vuln_pinned,
        "hazard_integrity_ok": hazard_ok,
        "vulnerability_integrity_ok": vuln_ok,
        "registry_ready": hazard_ok and vuln_ok,
        "n_artifacts": len(listed),
    }


@router.get("/health")
def health() -> dict:
    """Liveness probe — settings, store, starter data, Ollama, model registry."""
    settings = get_settings()
    store = get_store()
    nairobi = settings.nairobi_data_dir
    required = [
        "exposure_nairobi_with_hazard.csv",
        "nairobi_hotspots_geocoded.csv",
    ]
    missing = [f for f in required if not (nairobi / f).exists()]
    profile = settings.assumptions_profile()
    ollama = OllamaClient(
        host=settings.ollama_host,
        model=settings.ollama_primary_model,
    ).health()
    registry = _registry_status(settings.models_dir)
    status = "ok"
    if missing or not ollama.available or not registry["registry_ready"]:
        status = "degraded"
    return {
        "status": status,
        "env": settings.env,
        "phase": "F-e2e-hardening",
        "streamlit": "removed",
        "frontend": "apps/web (Next.js — deploy on Vercel; API on Contabo)",
        "nairobi_data": str(nairobi),
        "nairobi_data_ok": len(missing) == 0,
        "missing_files": missing,
        "models_dir": str(settings.models_dir),
        "models_dir_ok": settings.models_dir.exists(),
        "registry": registry,
        "require_ml": settings.require_ml,
        "allow_prior_only": settings.allow_prior_only,
        "use_osm_default": settings.use_osm_default,
        "assumptions_version": profile.assumptions_version,
        "d_max_m": profile.d_max_m,
        "return_periods": profile.return_periods,
        "capital_policy": profile.capital.model_dump(),
        "ollama_host": settings.ollama_host,
        "ollama_model": settings.ollama_primary_model,
        "ollama_up": ollama.available,
        "ollama_detail": ollama.detail,
        "audit_chain_valid": get_audit_chain().verify(),
        "store": store.stats(),
    }
