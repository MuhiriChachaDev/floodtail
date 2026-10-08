#!/usr/bin/env python3
"""Train + pin hazard and vulnerability models for FLOODTAIL runs.

OSM enrichment is opt-in (--use-osm). Overpass is flaky; training never
fails when OSM is unavailable — features degrade to NaN/flag=0.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from apps.api.settings import get_settings
from packages.ml.pipeline import run_training_job
from packages.ml.registry import ModelRegistry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-dir", type=Path, default=None)
    parser.add_argument("--n-iter", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-tune", action="store_true")
    parser.add_argument(
        "--use-osm",
        action="store_true",
        help="Request OSM waterway features for hazard (degrades if Overpass is down)",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    models_dir = args.models_dir or settings.models_dir
    registry = ModelRegistry(models_dir)
    profile = settings.assumptions_profile()
    tune = not args.no_tune
    exposure = settings.nairobi_data_dir / "exposure_nairobi_with_hazard.csv"
    hotspots = settings.nairobi_data_dir / settings.hotspots_filename

    vuln = run_training_job(
        "vulnerability",
        profile,
        registry,
        tune=tune,
        n_iter=args.n_iter,
        seed=args.seed,
    )
    print(
        f"pinned vulnerability/{vuln.version} sha={vuln.sha256[:12]} "
        f"mae={vuln.metrics.get('mae')}"
    )

    haz = run_training_job(
        "hazard",
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
    print(
        f"pinned hazard/{haz.version} sha={haz.sha256[:12]} "
        f"mae={haz.metrics.get('mae')} use_osm={bool(args.use_osm)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
