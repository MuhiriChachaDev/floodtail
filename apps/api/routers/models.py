"""Model train / list / pin routes — Phase C."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from apps.api.deps import SettingsDep
from packages.ml.pipeline import run_training_job
from packages.ml.registry import ModelRegistry

router = APIRouter()


class TrainRequest(BaseModel):
    tune: bool = True
    n_iter: int = Field(default=8, ge=1, le=40)
    seed: int = 42
    use_osm: bool = False
    exposure_path: Optional[str] = None
    hotspots_path: Optional[str] = None


def _registry(settings: SettingsDep) -> ModelRegistry:
    return ModelRegistry(settings.models_dir)


@router.get("/models")
def list_models(settings: SettingsDep) -> dict:
    reg = _registry(settings)
    return {"models": reg.list_models(), "models_dir": str(settings.models_dir)}


@router.post("/models/hazard/train")
def train_hazard(body: TrainRequest, settings: SettingsDep) -> dict:
    profile = settings.assumptions_profile()
    exposure = Path(body.exposure_path) if body.exposure_path else (
        settings.nairobi_data_dir / "exposure_nairobi_with_hazard.csv"
    )
    hotspots = Path(body.hotspots_path) if body.hotspots_path else (
        settings.nairobi_data_dir / settings.hotspots_filename
    )
    if not exposure.exists():
        raise HTTPException(status_code=400, detail=f"exposure not found: {exposure}")
    try:
        entry = run_training_job(
            "hazard",
            profile,
            _registry(settings),
            exposure_path=exposure,
            hotspots_path=hotspots if hotspots.exists() else None,
            use_osm=body.use_osm,
            tune=body.tune,
            n_iter=body.n_iter,
            seed=body.seed,
            overpass_url=settings.overpass_url,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "model_type": entry.model_type,
        "version": entry.version,
        "sha256": entry.sha256,
        "metrics": entry.metrics,
        "params": entry.params,
        "pinned": entry.pinned,
    }


@router.post("/models/vulnerability/train")
def train_vulnerability(body: TrainRequest, settings: SettingsDep) -> dict:
    profile = settings.assumptions_profile()
    try:
        entry = run_training_job(
            "vulnerability",
            profile,
            _registry(settings),
            tune=body.tune,
            n_iter=body.n_iter,
            seed=body.seed,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "model_type": entry.model_type,
        "version": entry.version,
        "sha256": entry.sha256,
        "metrics": entry.metrics,
        "params": entry.params,
        "pinned": entry.pinned,
    }
