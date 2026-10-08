"""Exposure loader, DQ gate, and ingest stats (location-agnostic)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Sequence

import pandas as pd

from packages.cat_core.assumptions import AssumptionsProfile
from packages.cat_core.exceptions import ExposureDQError
from packages.cat_core.types import DataLabels, IngestStats

REQUIRED_COLUMNS = ("loc_id", "lat", "lon", "housing_class", "tiv_kes")
HAZARD_SCORE_PREFIX = "hazard_score_"


def builtin_nairobi_path(data_dir: Path) -> Path:
    return data_dir / "exposure_nairobi_with_hazard.csv"


def load_exposure_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise ExposureDQError(f"Exposure file not found: {path}")
    df = pd.read_csv(path)
    if df.empty:
        raise ExposureDQError("Exposure file is empty")
    return df


def validate_and_normalize(
    df: pd.DataFrame,
    profile: AssumptionsProfile,
    *,
    location_label: str = "unknown",
    source: str = "upload",
    force_synthetic: bool = True,
) -> tuple[pd.DataFrame, IngestStats, list[str]]:
    """Validate schema/DQ and return cleaned frame + ingest stats + warnings."""
    warnings: list[str] = []
    out = df.copy()
    missing = [c for c in REQUIRED_COLUMNS if c not in out.columns]
    if missing:
        raise ExposureDQError(f"Missing required columns: {missing}")

    out["loc_id"] = out["loc_id"].astype(str)
    out["lat"] = pd.to_numeric(out["lat"], errors="coerce")
    out["lon"] = pd.to_numeric(out["lon"], errors="coerce")
    out["tiv_kes"] = pd.to_numeric(out["tiv_kes"], errors="coerce")
    out["housing_class"] = out["housing_class"].astype(str).str.strip()

    if out["lat"].isna().any() or out["lon"].isna().any():
        raise ExposureDQError("Non-finite latitude/longitude values present")
    if (out["tiv_kes"] <= 0).any() or out["tiv_kes"].isna().any():
        raise ExposureDQError("All tiv_kes values must be > 0")

    allowed = set(profile.housing_classes)
    bad = sorted(set(out["housing_class"]) - allowed)
    if bad:
        raise ExposureDQError(
            f"Invalid housing_class values {bad}; allowed={sorted(allowed)}"
        )

    if "synthetic" not in out.columns:
        out["synthetic"] = force_synthetic
        warnings.append("synthetic column missing — stamped from force_synthetic")
    else:
        out["synthetic"] = out["synthetic"].astype(bool)
        if force_synthetic:
            out["synthetic"] = True

    if "source" not in out.columns:
        out["source"] = source
    else:
        out["source"] = out["source"].fillna(source).astype(str)

    # Ensure hazard score columns exist for configured tiers (fill 0 if absent).
    # Zero-fill is intentional for schema completeness but understates risk —
    # callers should sample GeoTIFFs or attach scores before financial runs.
    missing_hazard: list[str] = []
    for tier in profile.tier_names:
        col = f"{HAZARD_SCORE_PREFIX}{tier}"
        if col not in out.columns:
            out[col] = 0.0
            missing_hazard.append(col)
            warnings.append(f"missing {col} — filled with 0.0")
        else:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0).clip(0.0, 1.0)
    if missing_hazard:
        warnings.append(
            "HAZARD_ZERO_FILL: missing susceptibility columns were set to 0.0. "
            "Losses will understate risk until scores are attached or GeoTIFF "
            "sampling (sample_hazard_rasters) is applied. "
            f"columns={missing_hazard}"
        )

    stats = compute_ingest_stats(out, location_label=location_label, source=source)
    return out, stats, warnings


def compute_ingest_stats(
    df: pd.DataFrame,
    *,
    location_label: str,
    source: str,
) -> IngestStats:
    bbox = (
        float(df["lat"].min()),
        float(df["lon"].min()),
        float(df["lat"].max()),
        float(df["lon"].max()),
    )
    class_counts = {str(k): int(v) for k, v in df["housing_class"].value_counts().items()}
    synthetic = bool(df["synthetic"].all()) if "synthetic" in df.columns else True
    return IngestStats(
        n_insured_houses=int(len(df)),
        total_tiv_kes=float(df["tiv_kes"].sum()),
        location_label=location_label,
        bbox=bbox,
        housing_class_counts=class_counts,
        synthetic=synthetic,
        source=source,
    )


def default_data_labels(
    profile: AssumptionsProfile,
    *,
    synthetic: bool = True,
    notes: Optional[Sequence[str]] = None,
) -> DataLabels:
    return DataLabels(
        synthetic_exposure=synthetic,
        proxy_hazard=True,
        assumed_rp=True,
        d_max_m=profile.d_max_m,
        location_flexible=True,
        notes=list(notes or []),
    )


def hazard_score_columns(tier_names: Iterable[str]) -> list[str]:
    return [f"{HAZARD_SCORE_PREFIX}{t}" for t in tier_names]
