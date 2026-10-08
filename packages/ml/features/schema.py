"""Feature contract — location-agnostic, versioned."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

FEATURE_SCHEMA_VERSION = "flex-v1"

# Numeric features used by both hazard and vulnerability builders (subset applied per model)
HAZARD_NUMERIC_FEATURES = [
    "lat",
    "lon",
    "log_tiv",
    "log_floor_area",
    "dist_hotspot_km",
    "has_hotspot_layer",
    "dist_waterway_km",
    "has_osm_waterway",
]

VULN_NUMERIC_FEATURES = [
    "depth_m",
    "log_tiv",
    "log_floor_area",
    "dist_hotspot_km",
    "has_hotspot_layer",
]


class FeatureSchema(BaseModel):
    version: str = FEATURE_SCHEMA_VERSION
    model_type: str
    numeric_features: list[str] = Field(default_factory=list)
    categorical_features: list[str] = Field(default_factory=lambda: ["housing_class"])
    housing_classes: list[str] = Field(default_factory=list)
    target_columns: list[str] = Field(default_factory=list)
    extras: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
