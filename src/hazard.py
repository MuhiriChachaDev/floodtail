"""FLOODTAIL — Spatial Hazard Intersection and Flood Depth Engine.

Intersects catastrophe event footprints with geographic exposure locations to determine
water depth (depth_m) at exposed policy coordinates. Enforces strict zero-depth rules
for locations outside flood footprints.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

import numpy as np
import pandas as pd

from src.exceptions import HazardModelError
from src.logging_config import get_logger
from src.schemas import HazardResult

logger = get_logger("hazard")


@dataclass
class FootprintGeometry:
    """Geometric specification for a catastrophe flood footprint."""

    footprint_id: str
    center_lat: float
    center_lon: float
    radius_km: float
    base_depth_m: float
    shape_type: str = "radial_decay"  # 'radial_decay', 'polygon', 'box'
    polygon_coords: Optional[list[list[float]]] = None  # [[lat, lon], ...] if polygon

    def compute_depth_at(self, lat: float, lon: float, severity_factor: float = 1.0) -> float:
        """Compute flood depth at a given WGS-84 coordinate. Returns 0.0 if outside."""
        # Fast bounding box check first
        # 1 deg lat approx 111 km, 1 deg lon approx 111 * cos(lat) km
        deg_lat_dist = (lat - self.center_lat) * 111.0
        deg_lon_dist = (lon - self.center_lon) * 111.0 * math.cos(math.radians(self.center_lat))
        dist_km = math.sqrt(deg_lat_dist**2 + deg_lon_dist**2)

        if dist_km > self.radius_km:
            return 0.0

        if self.polygon_coords:
            if not self._point_in_polygon(lat, lon, self.polygon_coords):
                return 0.0

        # Radial decay from footprint epicenter
        decay = max(0.0, 1.0 - (dist_km / self.radius_km))
        depth = self.base_depth_m * severity_factor * decay
        return round(float(depth), 4)

    @staticmethod
    def _point_in_polygon(lat: float, lon: float, polygon: list[list[float]]) -> bool:
        """Standard ray-casting algorithm for point in polygon."""
        n = len(polygon)
        inside = False
        p1_lat, p1_lon = polygon[0]
        for i in range(n + 1):
            p2_lat, p2_lon = polygon[i % n]
            if lon > min(p1_lon, p2_lon):
                if lon <= max(p1_lon, p2_lon):
                    if lat <= max(p1_lat, p2_lat):
                        if p1_lon != p2_lon:
                            xinters = (lon - p1_lon) * (p2_lat - p1_lat) / (p2_lon - p1_lon) + p1_lat
                        if p1_lat == p2_lat or lat <= xinters:
                            inside = not inside
            p1_lat, p1_lon = p2_lat, p2_lon
        return inside


class HazardFootprintStore:
    """Repository of spatial flood footprints indexed by footprint_id or event_id."""

    def __init__(self, footprints: Optional[dict[str, FootprintGeometry]] = None) -> None:
        self.footprints: dict[str, FootprintGeometry] = footprints or {}

    def add_footprint(self, footprint: FootprintGeometry) -> None:
        self.footprints[footprint.footprint_id] = footprint

    def get_footprint(self, footprint_ref: str) -> Optional[FootprintGeometry]:
        return self.footprints.get(footprint_ref)

    @classmethod
    def from_json_file(cls, file_path: Union[str, Path]) -> HazardFootprintStore:
        """Load footprint geometry definitions from a JSON file."""
        path = Path(file_path)
        if not path.exists():
            raise HazardModelError(f"Footprints file not found: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            raise HazardModelError(f"Failed to read footprints JSON from '{path.name}': {e}") from e

        store = cls()
        for item in data:
            fp = FootprintGeometry(
                footprint_id=item["footprint_id"],
                center_lat=float(item["center_lat"]),
                center_lon=float(item["center_lon"]),
                radius_km=float(item.get("radius_km", 25.0)),
                base_depth_m=float(item.get("base_depth_m", 1.5)),
                shape_type=item.get("shape_type", "radial_decay"),
                polygon_coords=item.get("polygon_coords"),
            )
            store.add_footprint(fp)
        return store


@dataclass
class ExposureHazardSummary:
    """Summary of portfolio exposure and hazard intersection."""

    total_occurrences: int
    affected_occurrences: int
    total_impacted_policy_events: int
    unique_affected_policies: int
    mean_impacted_depth_m: float
    max_impacted_depth_m: float
    total_exposed_tiv: float


class SpatialHazardEngine:
    """Intersects event occurrences with exposure portfolio to generate physical hazard fields."""

    def __init__(
        self,
        footprint_store: HazardFootprintStore,
        hazard_source: str = "SYNTHETIC_HAZARD_FIELD",
    ) -> None:
        self.footprint_store = footprint_store
        self.hazard_source = hazard_source

    def evaluate_hazard(
        self,
        portfolio_df: pd.DataFrame,
        event_occurrences_df: pd.DataFrame,
        sparse: bool = True,
    ) -> tuple[pd.DataFrame, ExposureHazardSummary]:
        """Intersect simulated event occurrences against exposure portfolio.

        Args:
            portfolio_df: Clean normalized portfolio with columns [policy_id, latitude, longitude, insured_value]
            event_occurrences_df: Simulated event occurrences with columns [simulation_year, occurrence_id, event_id, severity, footprint_ref]
            sparse: If True, only pairs with depth_m > 0 are retained.

        Returns:
            Tuple of (hazard_results_df, ExposureHazardSummary)
        """
        logger.info(
            "Starting hazard intersection: %d policies × %d event occurrences",
            len(portfolio_df),
            len(event_occurrences_df),
        )

        if portfolio_df.empty or event_occurrences_df.empty:
            empty_df = pd.DataFrame(columns=[
                "simulation_year", "occurrence_id", "event_id", "policy_id",
                "depth_m", "flood_type", "hazard_source"
            ])
            summary = ExposureHazardSummary(
                total_occurrences=len(event_occurrences_df),
                affected_occurrences=0,
                total_impacted_policy_events=0,
                unique_affected_policies=0,
                mean_impacted_depth_m=0.0,
                max_impacted_depth_m=0.0,
                total_exposed_tiv=0.0,
            )
            return empty_df, summary

        # Extract numpy arrays for fast vectorized / spatial calculation
        pol_ids = portfolio_df["policy_id"].astype(str).values
        pol_lats = portfolio_df["latitude"].astype(float).values
        pol_lons = portfolio_df["longitude"].astype(float).values
        pol_tivs = portfolio_df["insured_value"].astype(float).values

        results: list[dict[str, Any]] = []
        affected_occurrences_set = set()
        affected_policy_set = set()
        exposed_tiv_sum = 0.0

        # Group occurrences by event_id / footprint_ref to avoid redundant footprint lookups
        for _, occ in event_occurrences_df.iterrows():
            sim_year = int(occ["simulation_year"])
            occ_id = int(occ["occurrence_id"])
            evt_id = str(occ["event_id"])
            fp_ref = str(occ.get("footprint_ref") or evt_id)
            severity = float(occ.get("severity", 1.0))
            flood_type = str(occ.get("event_type", "fluvial"))

            footprint = self.footprint_store.get_footprint(fp_ref)
            if not footprint:
                # If footprint is missing, log warning and assume zero depth
                logger.warning("Footprint '%s' not found for event '%s'; assigning depth 0", fp_ref, evt_id)
                continue

            # Fast spatial filter: Bounding box filter around footprint
            center_lat, center_lon, radius_km = footprint.center_lat, footprint.center_lon, footprint.radius_km
            lat_delta = radius_km / 111.0
            lon_delta = radius_km / (111.0 * max(0.1, math.cos(math.radians(center_lat))))

            in_bbox = (
                (pol_lats >= center_lat - lat_delta) & (pol_lats <= center_lat + lat_delta) &
                (pol_lons >= center_lon - lon_delta) & (pol_lons <= center_lon + lon_delta)
            )

            candidate_indices = np.where(in_bbox)[0]

            for idx in candidate_indices:
                p_lat = pol_lats[idx]
                p_lon = pol_lons[idx]
                depth = footprint.compute_depth_at(p_lat, p_lon, severity_factor=severity)

                if depth > 0.0:
                    pid = pol_ids[idx]
                    results.append({
                        "simulation_year": sim_year,
                        "occurrence_id": occ_id,
                        "event_id": evt_id,
                        "policy_id": pid,
                        "depth_m": depth,
                        "flood_type": flood_type,
                        "hazard_source": self.hazard_source,
                    })
                    affected_occurrences_set.add(occ_id)
                    affected_policy_set.add(pid)
                    exposed_tiv_sum += pol_tivs[idx]
                elif not sparse:
                    pid = pol_ids[idx]
                    results.append({
                        "simulation_year": sim_year,
                        "occurrence_id": occ_id,
                        "event_id": evt_id,
                        "policy_id": pid,
                        "depth_m": 0.0,
                        "flood_type": flood_type,
                        "hazard_source": self.hazard_source,
                    })

        hazard_df = pd.DataFrame(results) if results else pd.DataFrame(columns=[
            "simulation_year", "occurrence_id", "event_id", "policy_id",
            "depth_m", "flood_type", "hazard_source"
        ])

        depth_series = hazard_df["depth_m"] if not hazard_df.empty else pd.Series([0.0])

        summary = ExposureHazardSummary(
            total_occurrences=len(event_occurrences_df),
            affected_occurrences=len(affected_occurrences_set),
            total_impacted_policy_events=len(hazard_df[hazard_df["depth_m"] > 0]),
            unique_affected_policies=len(affected_policy_set),
            mean_impacted_depth_m=float(depth_series[depth_series > 0].mean()) if not depth_series[depth_series > 0].empty else 0.0,
            max_impacted_depth_m=float(depth_series.max()) if not hazard_df.empty else 0.0,
            total_exposed_tiv=float(exposed_tiv_sum),
        )

        logger.info(
            "Hazard evaluation complete: %d affected pairs across %d events. Mean depth: %.2fm, Max depth: %.2fm",
            summary.total_impacted_policy_events,
            summary.affected_occurrences,
            summary.mean_impacted_depth_m,
            summary.max_impacted_depth_m,
        )

        return hazard_df, summary
