"""FLOODTAIL — Event Catalogue and Stochastic Event Generation Engine.

Handles canonical catastrophe event catalogues (Synthetic, Historical, Supplied, Stress),
and simulates annual stochastic catastrophe event occurrences over N simulation years
using a Poisson frequency process and frequency-weighted sampling.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional, Union

import numpy as np
import pandas as pd

from src.exceptions import EventSetError
from src.logging_config import get_logger
from src.schemas import EventRecord

logger = get_logger("events")

EventSourceType = Literal["SYNTHETIC", "HISTORICAL", "SUPPLIED", "STRESS"]


@dataclass
class EventOccurrence:
    """A single stochastic realization of a catastrophe event in a simulation year."""

    simulation_year: int
    occurrence_id: int
    event_id: str
    event_type: str
    scenario_tag: Optional[str] = None
    annual_frequency: float = 0.0
    severity: float = 1.0
    footprint_ref: str = ""
    source: str = "SYNTHETIC"


class EventCatalogue:
    """In-memory validated catalogue of catastrophe flood events."""

    def __init__(
        self,
        events_df: pd.DataFrame,
        catalogue_version: str = "demo-v1.0",
        source_type: EventSourceType = "SYNTHETIC",
        description: str = "DEMO SYNTHETIC EVENT CATALOGUE - NOT CALIBRATED HISTORICAL OBSERVATION",
    ) -> None:
        self.catalogue_version = catalogue_version
        self.source_type = source_type
        self.description = description
        self.df = self._validate_and_prepare(events_df)
        self.catalogue_hash = self._compute_hash()

    def _validate_and_prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure all mandatory event attributes exist and adhere to constraints."""
        if df.empty:
            raise EventSetError("Event catalogue is empty (0 events).")

        required_cols = ["event_id", "annual_frequency", "severity", "footprint_ref"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise EventSetError(f"Event catalogue missing required columns: {missing}")

        clean = df.copy()
        clean["event_id"] = clean["event_id"].astype(str).str.strip()
        clean["annual_frequency"] = pd.to_numeric(clean["annual_frequency"], errors="coerce")
        clean["severity"] = pd.to_numeric(clean["severity"], errors="coerce")
        clean["footprint_ref"] = clean["footprint_ref"].astype(str).str.strip()

        if "event_type" not in clean.columns:
            clean["event_type"] = "fluvial"
        else:
            clean["event_type"] = clean["event_type"].fillna("fluvial").astype(str)

        if "scenario_tag" not in clean.columns:
            clean["scenario_tag"] = "baseline"
        else:
            clean["scenario_tag"] = clean["scenario_tag"].fillna("baseline").astype(str)

        if "source" not in clean.columns:
            clean["source"] = self.source_type
        else:
            clean["source"] = clean["source"].fillna(self.source_type).astype(str)

        # Validation checks
        if clean["event_id"].duplicated().any():
            dups = clean["event_id"][clean["event_id"].duplicated()].tolist()
            raise EventSetError(f"Duplicate event_id values detected in catalogue: {dups}")

        if (clean["annual_frequency"] < 0).any() or clean["annual_frequency"].isna().any():
            raise EventSetError("Annual frequency must be non-negative and non-null for all events.")

        if (clean["severity"] < 0).any() or clean["severity"].isna().any():
            raise EventSetError("Severity must be non-negative and non-null for all events.")

        # Check Pydantic contract compliance
        for idx, row in clean.iterrows():
            try:
                EventRecord(
                    event_id=row["event_id"],
                    event_type=row["event_type"],
                    scenario_tag=row["scenario_tag"],
                    annual_frequency=float(row["annual_frequency"]),
                    severity=float(row["severity"]),
                    footprint_ref=row["footprint_ref"],
                )
            except Exception as e:
                raise EventSetError(f"Event row {idx} ({row.get('event_id')}) fails EventRecord schema: {e}") from e

        return clean

    def _compute_hash(self) -> str:
        """Compute SHA-256 fingerprint of the event catalogue."""
        serialized = self.df.to_json(orient="records", date_format="iso").encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    @property
    def total_annual_rate(self) -> float:
        """Sum of all event annual frequencies (Poisson lambda rate)."""
        return float(self.df["annual_frequency"].sum())

    @property
    def event_ids(self) -> list[str]:
        return self.df["event_id"].tolist()

    def get_event(self, event_id: str) -> Optional[dict[str, Any]]:
        row = self.df[self.df["event_id"] == str(event_id)]
        if row.empty:
            return None
        return row.iloc[0].to_dict()

    @classmethod
    def from_csv(
        cls,
        file_path: Union[str, Path],
        catalogue_version: str = "demo-v1.0",
        source_type: EventSourceType = "SYNTHETIC",
    ) -> EventCatalogue:
        """Load and validate event catalogue from CSV."""
        path = Path(file_path)
        if not path.exists():
            raise EventSetError(f"Event catalogue file not found: {path}")
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            raise EventSetError(f"Failed to parse event catalogue CSV '{path.name}': {exc}") from exc
        return cls(df, catalogue_version=catalogue_version, source_type=source_type)


class EventSimulator:
    """Stochastic Poisson event occurrence simulation engine."""

    def __init__(
        self,
        catalogue: EventCatalogue,
        simulation_years: int = 10000,
        seed: int = 482913,
        lambda_rate: Optional[float] = None,
    ) -> None:
        self.catalogue = catalogue
        if simulation_years < 1:
            raise EventSetError(f"simulation_years must be >= 1, got {simulation_years}")
        self.simulation_years = simulation_years
        self.seed = seed
        self.lambda_rate = lambda_rate if lambda_rate is not None else catalogue.total_annual_rate

        if self.lambda_rate < 0:
            raise EventSetError(f"Poisson lambda rate must be >= 0, got {self.lambda_rate}")

    def simulate(self) -> pd.DataFrame:
        """Execute Monte Carlo simulation and return DataFrame of event occurrences.

        Returns DataFrame columns:
            [simulation_year, occurrence_id, event_id, event_type, scenario_tag,
             annual_frequency, severity, footprint_ref, source]
        """
        logger.info(
            "Starting stochastic event simulation: %d years, seed=%d, lambda=%.4f, events=%d",
            self.simulation_years,
            self.seed,
            self.lambda_rate,
            len(self.catalogue.df),
        )

        rng = np.random.default_rng(self.seed)

        # Handle edge case: zero rate or empty simulation
        if self.lambda_rate == 0 or len(self.catalogue.df) == 0:
            logger.warning("Simulation rate is 0: generating 0 event occurrences.")
            return pd.DataFrame(columns=[
                "simulation_year", "occurrence_id", "event_id", "event_type",
                "scenario_tag", "annual_frequency", "severity", "footprint_ref", "source"
            ])

        # Poisson draws for annual event count across all years
        annual_counts = rng.poisson(lam=self.lambda_rate, size=self.simulation_years)
        total_occurrences = int(annual_counts.sum())

        # Event selection weights
        weights = self.catalogue.df["annual_frequency"].values
        total_w = weights.sum()
        if total_w > 0:
            probabilities = weights / total_w
        else:
            probabilities = np.ones(len(weights)) / len(weights)

        event_indices = np.arange(len(self.catalogue.df))

        # Sample event index for all occurrences in bulk for high performance
        sampled_indices = rng.choice(event_indices, size=total_occurrences, p=probabilities)

        # Build occurrence records
        occurrences: list[dict[str, Any]] = []
        occ_ptr = 0
        cat_records = self.catalogue.df.to_dict(orient="records")

        for year_idx in range(self.simulation_years):
            year_num = year_idx + 1
            k = annual_counts[year_idx]
            for occ_in_year in range(k):
                evt_idx = sampled_indices[occ_ptr]
                occ_ptr += 1
                cat_row = cat_records[evt_idx]

                occurrences.append({
                    "simulation_year": year_num,
                    "occurrence_id": len(occurrences) + 1,
                    "event_id": cat_row["event_id"],
                    "event_type": cat_row.get("event_type", "fluvial"),
                    "scenario_tag": cat_row.get("scenario_tag", "baseline"),
                    "annual_frequency": cat_row.get("annual_frequency", 0.0),
                    "severity": cat_row.get("severity", 1.0),
                    "footprint_ref": cat_row.get("footprint_ref", ""),
                    "source": cat_row.get("source", self.catalogue.source_type),
                })

        occ_df = pd.DataFrame(occurrences) if occurrences else pd.DataFrame(columns=[
            "simulation_year", "occurrence_id", "event_id", "event_type",
            "scenario_tag", "annual_frequency", "severity", "footprint_ref", "source"
        ])

        logger.info(
            "Simulation complete: %d simulated years produced %d total event occurrences (avg %.2f/yr)",
            self.simulation_years,
            len(occ_df),
            len(occ_df) / self.simulation_years if self.simulation_years > 0 else 0.0,
        )

        return occ_df
