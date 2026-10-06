"""FLOODTAIL — Schema mapping engine.

Maps varied user/organiser column names into the canonical FLOODTAIL
portfolio schema using exact match, known aliases, and fuzzy matching.
Low-confidence mappings are flagged for human review.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Any, Optional

import pandas as pd

from src.logging_config import get_logger

logger = get_logger("schema_mapper")


def _fuzzy_similarity(s1: str, s2: str) -> float:
    """Calculate normalized similarity between two strings [0.0, 1.0]."""
    try:
        from rapidfuzz import fuzz
        return fuzz.ratio(s1, s2) / 100.0
    except ImportError:
        return difflib.SequenceMatcher(None, s1, s2).ratio()


# ---------------------------------------------------------------------------
# Canonical target fields and known aliases
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = {"policy_id", "latitude", "longitude", "insured_value", "property_type"}
OPTIONAL_FIELDS = {"construction_class", "region"}
ALL_TARGET_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS

# Known aliases → canonical name
_ALIASES: dict[str, str] = {
    # policy_id
    "policy": "policy_id",
    "policy_number": "policy_id",
    "policy_no": "policy_id",
    "id": "policy_id",
    "pol_id": "policy_id",
    "policyid": "policy_id",
    "contract_id": "policy_id",
    "cert_no": "policy_id",
    # latitude
    "lat": "latitude",
    "y": "latitude",
    "y_coord": "latitude",
    "latitude_deg": "latitude",
    "gps_latitude": "latitude",
    # longitude
    "lon": "longitude",
    "lng": "longitude",
    "long": "longitude",
    "x": "longitude",
    "x_coord": "longitude",
    "longitude_deg": "longitude",
    "gps_longitude": "longitude",
    # insured_value
    "tiv": "insured_value",
    "total_insured_value": "insured_value",
    "sum_insured": "insured_value",
    "sum_assured": "insured_value",
    "insured_limit": "insured_value",
    "replacement_cost": "insured_value",
    "property_value": "insured_value",
    "total_val_insured": "insured_value",
    "val_insured": "insured_value",
    "limit": "insured_value",
    # property_type
    "property": "property_type",
    "occupancy": "property_type",
    "building_type": "property_type",
    "asset_type": "property_type",
    "prop_type": "property_type",
    "occupancy_type": "property_type",
    # construction_class
    "construction": "construction_class",
    "construction_type": "construction_class",
    "building_class": "construction_class",
    "structure_type": "construction_class",
    # region
    "county": "region",
    "area": "region",
    "zone": "region",
    "location_region": "region",
    "province": "region",
    "state": "region",
    "admin1": "region",
}


# ---------------------------------------------------------------------------
# Column name normalisation
# ---------------------------------------------------------------------------

def normalize_column_name(raw: str) -> str:
    """Normalize a raw column name for matching."""
    s = raw.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


# ---------------------------------------------------------------------------
# Single-column mapping
# ---------------------------------------------------------------------------

@dataclass
class ColumnMapping:
    """Result of mapping one source column to a target field."""

    source_column: str
    normalized: str
    target_field: Optional[str]
    mapping_method: str  # EXACT, ALIAS, FUZZY, NONE
    confidence: float
    status: str  # AUTO_ACCEPTED, REVIEW_REQUIRED, UNMAPPED

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_column": self.source_column,
            "normalized": self.normalized,
            "target_field": self.target_field,
            "mapping_method": self.mapping_method,
            "confidence": self.confidence,
            "status": self.status,
        }


def map_column(
    raw_name: str,
    *,
    auto_accept_threshold: float = 0.80,
    review_threshold: float = 0.60,
    already_mapped: Optional[set[str]] = None,
) -> ColumnMapping:
    """Map a single source column name to a canonical target field."""
    already_mapped = already_mapped or set()
    norm = normalize_column_name(raw_name)

    # 1. Exact match against canonical target fields
    if norm in ALL_TARGET_FIELDS and norm not in already_mapped:
        return ColumnMapping(
            source_column=raw_name,
            normalized=norm,
            target_field=norm,
            mapping_method="EXACT",
            confidence=1.0,
            status="AUTO_ACCEPTED",
        )

    # 2. Known alias lookup
    if norm in _ALIASES:
        target = _ALIASES[norm]
        if target not in already_mapped:
            return ColumnMapping(
                source_column=raw_name,
                normalized=norm,
                target_field=target,
                mapping_method="ALIAS",
                confidence=1.0,
                status="AUTO_ACCEPTED",
            )

    # 3. Fuzzy matching against all target names + aliases
    best_score = 0.0
    best_target: Optional[str] = None

    # Check against canonical field names
    for field_name in ALL_TARGET_FIELDS:
        if field_name in already_mapped:
            continue
        score = _fuzzy_similarity(norm, field_name)
        if score > best_score:
            best_score = score
            best_target = field_name

    # Check against alias keys (resolve to canonical)
    for alias, target in _ALIASES.items():
        if target in already_mapped:
            continue
        score = _fuzzy_similarity(norm, alias)
        if score > best_score:
            best_score = score
            best_target = target

    if best_target and best_score >= auto_accept_threshold:
        return ColumnMapping(
            source_column=raw_name,
            normalized=norm,
            target_field=best_target,
            mapping_method="FUZZY",
            confidence=round(best_score, 4),
            status="AUTO_ACCEPTED",
        )

    if best_target and best_score >= review_threshold:
        return ColumnMapping(
            source_column=raw_name,
            normalized=norm,
            target_field=best_target,
            mapping_method="FUZZY",
            confidence=round(best_score, 4),
            status="REVIEW_REQUIRED",
        )

    # Unmapped
    return ColumnMapping(
        source_column=raw_name,
        normalized=norm,
        target_field=None,
        mapping_method="NONE",
        confidence=0.0,
        status="UNMAPPED",
    )


# ---------------------------------------------------------------------------
# Mapping Plan / Result
# ---------------------------------------------------------------------------

@dataclass
class MappingPlan:
    """Full mapping specification for a dataset schema."""

    mappings: dict[str, ColumnMapping] = field(default_factory=dict)
    rename_dict: dict[str, str] = field(default_factory=dict)
    mapped_fields: set[str] = field(default_factory=set)
    unmapped_source_columns: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    is_valid: bool = False

    @property
    def is_complete(self) -> bool:
        return self.is_valid

    @property
    def review_required(self) -> list[ColumnMapping]:
        return [m for m in self.mappings.values() if m.status == "REVIEW_REQUIRED"]

    def to_dicts(self) -> list[dict[str, Any]]:
        return [m.to_dict() for m in self.mappings.values()]


class SchemaMapper:
    """Intelligent mapper translating arbitrary client schemas to canonical FLOODTAIL schema."""

    def __init__(
        self,
        auto_accept_threshold: float = 0.80,
        review_threshold: float = 0.60,
    ) -> None:
        self.auto_accept_threshold = auto_accept_threshold
        self.review_threshold = review_threshold

    def create_mapping_plan(self, source_columns: list[str]) -> MappingPlan:
        """Analyze source columns and produce a MappingPlan."""
        already_mapped: set[str] = set()
        mappings: dict[str, ColumnMapping] = {}
        rename_dict: dict[str, str] = {}
        unmapped: list[str] = []

        for col in source_columns:
            m = map_column(
                col,
                auto_accept_threshold=self.auto_accept_threshold,
                review_threshold=self.review_threshold,
                already_mapped=already_mapped,
            )
            mappings[col] = m
            if m.target_field and m.status in ("AUTO_ACCEPTED", "REVIEW_REQUIRED"):
                already_mapped.add(m.target_field)
                rename_dict[col] = m.target_field
            else:
                unmapped.append(col)

        missing = sorted(list(REQUIRED_FIELDS - already_mapped))
        is_valid = len(missing) == 0

        if is_valid:
            logger.info("Schema mapping complete — all required fields mapped")
        else:
            logger.warning("Schema mapping incomplete — missing required fields: %s", ", ".join(missing))

        return MappingPlan(
            mappings=mappings,
            rename_dict=rename_dict,
            mapped_fields=already_mapped,
            unmapped_source_columns=unmapped,
            missing_required=missing,
            is_valid=is_valid,
        )

    def apply_mapping(self, df: pd.DataFrame, plan: MappingPlan) -> pd.DataFrame:
        """Apply column rename plan to DataFrame."""
        return df.rename(columns=plan.rename_dict)


def map_schema(
    source_columns: list[str],
    *,
    auto_accept_threshold: float = 0.80,
    review_threshold: float = 0.60,
) -> MappingPlan:
    """Convenience function matching functional interface."""
    mapper = SchemaMapper(
        auto_accept_threshold=auto_accept_threshold,
        review_threshold=review_threshold,
    )
    return mapper.create_mapping_plan(source_columns)
