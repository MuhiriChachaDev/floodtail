"""ML pipeline facade: train jobs + predict helpers."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Literal, Optional

from packages.cat_core.assumptions import AssumptionsProfile
from packages.ml.hazard.infer import predict_hazard
from packages.ml.hazard.train import train_hazard_model
from packages.ml.registry import ModelRegistry, RegistryEntry
from packages.ml.vulnerability.infer import predict_vulnerability_for_tiers
from packages.ml.vulnerability.train import train_vulnerability_model

ModelType = Literal["hazard", "vulnerability"]


def run_training_job(
    model_type: ModelType,
    profile: AssumptionsProfile,
    registry: ModelRegistry,
    *,
    exposure_path: Optional[Path] = None,
    hotspots_path: Optional[Path] = None,
    use_osm: bool = False,
    tune: bool = True,
    n_iter: int = 8,
    seed: int = 42,
    overpass_url: str = "https://overpass-api.de/api/interpreter",
) -> RegistryEntry:
    if model_type == "hazard":
        if exposure_path is None:
            raise ValueError("exposure_path required for hazard training")
        return train_hazard_model(
            exposure_path,
            profile,
            registry,
            hotspots_path=hotspots_path,
            use_osm=use_osm,
            tune=tune,
            n_iter=n_iter,
            seed=seed,
            overpass_url=overpass_url,
        )
    if model_type == "vulnerability":
        return train_vulnerability_model(
            profile,
            registry,
            tune=tune,
            n_iter=n_iter,
            seed=seed,
        )
    raise ValueError(f"Unknown model_type: {model_type}")


def predict(
    model_type: ModelType,
    frame,
    profile: AssumptionsProfile,
    registry: ModelRegistry,
    *,
    version: Optional[str] = None,
):
    if model_type == "hazard":
        return predict_hazard(frame, profile, registry, version=version)
    if model_type == "vulnerability":
        return predict_vulnerability_for_tiers(frame, profile, registry, version=version)
    raise ValueError(f"Unknown model_type: {model_type}")


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m packages.ml.pipeline")
    sub = parser.add_subparsers(dest="model_type", required=True)
    for name in ("hazard", "vulnerability"):
        p = sub.add_parser(name)
        p.add_argument("action", choices=["train"])
        p.add_argument("--tune", action="store_true", default=True)
        p.add_argument("--no-tune", action="store_true")
        p.add_argument("--seed", type=int, default=42)
        p.add_argument("--n-iter", type=int, default=8)
        p.add_argument("--use-osm", action="store_true")
        p.add_argument("--exposure", type=str, default=None)
        p.add_argument("--hotspots", type=str, default=None)
        p.add_argument("--models-dir", type=str, default="models")
    args = parser.parse_args(argv)

    from apps.api.settings import get_settings

    settings = get_settings()
    profile = settings.assumptions_profile()
    registry = ModelRegistry(Path(args.models_dir))
    tune = not args.no_tune
    exposure = Path(args.exposure) if args.exposure else (
        settings.nairobi_data_dir / "exposure_nairobi_with_hazard.csv"
    )
    hotspots = Path(args.hotspots) if args.hotspots else (
        settings.nairobi_data_dir / "nairobi_hotspots_geocoded.csv"
    )
    entry = run_training_job(
        args.model_type,  # type: ignore[arg-type]
        profile,
        registry,
        exposure_path=exposure,
        hotspots_path=hotspots if hotspots.exists() else None,
        use_osm=bool(args.use_osm),
        tune=tune,
        n_iter=args.n_iter,
        seed=args.seed,
        overpass_url=settings.overpass_url,
    )
    print(f"registered {entry.model_type}/{entry.version} sha={entry.sha256[:12]} mae={entry.metrics.get('mae')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
