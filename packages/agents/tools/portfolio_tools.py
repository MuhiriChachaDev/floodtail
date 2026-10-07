"""LangChain tools for portfolio ingest + schema mapping."""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from packages.cat_core.assumptions import AssumptionsProfile
from packages.cat_core.exceptions import ExposureDQError
from packages.cat_core.exposure import (
    builtin_nairobi_path,
    compute_ingest_stats,
    load_exposure_csv,
    validate_and_normalize,
)

# Canonical Nairobi CAT columns + common aliases from underwriter CSVs
_COLUMN_ALIASES: dict[str, str] = {
    "loc_id": "loc_id",
    "location_id": "loc_id",
    "id": "loc_id",
    "policy_id": "loc_id",
    "building_id": "loc_id",
    "lat": "lat",
    "latitude": "lat",
    "y": "lat",
    "lon": "lon",
    "lng": "lon",
    "long": "lon",
    "longitude": "lon",
    "x": "lon",
    "housing_class": "housing_class",
    "occupancy": "housing_class",
    "construction_class": "housing_class",
    "property_type": "housing_class",
    "building_type": "housing_class",
    "tiv_kes": "tiv_kes",
    "tiv": "tiv_kes",
    "insured_value": "tiv_kes",
    "sum_insured": "tiv_kes",
    "total_insured_value": "tiv_kes",
}


def schema_map(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str], list[str]]:
    """
    Map column aliases → canonical exposure schema.

    Returns (mapped_frame, mapping_used, warnings).
    """
    warnings: list[str] = []
    mapping: dict[str, str] = {}
    rename: dict[str, str] = {}
    lower_cols = {c.lower().strip(): c for c in frame.columns}
    for alias, canonical in _COLUMN_ALIASES.items():
        if canonical in frame.columns:
            mapping[canonical] = canonical
            continue
        if alias in lower_cols:
            src = lower_cols[alias]
            if src != canonical and canonical not in rename.values():
                rename[src] = canonical
                mapping[canonical] = src
    out = frame.rename(columns=rename)
    if rename:
        warnings.append(f"schema_map renamed columns: {rename}")
    return out, mapping, warnings


def ingest_portfolio(
    *,
    profile: AssumptionsProfile,
    source: str = "builtin_nairobi",
    data_dir: Optional[Any] = None,
    frame: Optional[pd.DataFrame] = None,
    location_label: str = "unknown",
) -> tuple[pd.DataFrame, dict[str, Any], list[str]]:
    """
    Load + schema-map + DQ normalize a portfolio.

    Returns (frame, ingest_stats_dict, warnings).
    """
    warnings: list[str] = []
    if frame is None:
        if source == "builtin_nairobi":
            if data_dir is None:
                raise ExposureDQError("data_dir required for builtin_nairobi")
            raw = load_exposure_csv(builtin_nairobi_path(data_dir))
            location_label = location_label or "Nairobi County"
            src = "builtin_nairobi"
        else:
            raise ExposureDQError("frame required when source is not builtin_nairobi")
    else:
        raw = frame
        src = source

    mapped, mapping, map_warns = schema_map(raw)
    warnings.extend(map_warns)
    cleaned, stats, dq_warns = validate_and_normalize(
        mapped,
        profile,
        location_label=location_label,
        source=src,
        force_synthetic=True,
    )
    warnings.extend(dq_warns)
    return cleaned, {**stats.model_dump(), "column_mapping": mapping}, warnings


def build_freetext_candidates(
    rows: list[dict[str, Any]],
    profile: AssumptionsProfile,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Validate candidate free-text exposure rows against schema.

    Raises ExposureDQError if any row fails required fields / DQ.
    """
    if not rows:
        raise ExposureDQError("Free-text exposure produced zero rows")
    df = pd.DataFrame(rows)
    mapped, _, warnings = schema_map(df)
    cleaned, _, dq_warns = validate_and_normalize(
        mapped,
        profile,
        location_label="freetext",
        source="freetext_llm",
        force_synthetic=True,
    )
    cleaned["synthetic"] = True
    cleaned["source"] = "freetext_llm"
    warnings.extend(dq_warns)
    return cleaned, warnings


try:
    from langchain_core.tools import tool

    @tool
    def schema_map_tool(columns_csv: str) -> str:
        """Describe how a comma-separated column list would map to canonical fields."""
        cols = [c.strip() for c in columns_csv.split(",") if c.strip()]
        fake = pd.DataFrame(columns=cols)
        _, mapping, warnings = schema_map(fake)
        return f"mapping={mapping}; warnings={warnings}"

except ImportError:  # pragma: no cover
    pass
