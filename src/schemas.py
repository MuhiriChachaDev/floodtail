"""FLOODTAIL — Typed data contracts (Pydantic schemas).

Every FLOODTAIL pipeline stage communicates through these schemas.
No module should invent its own column names or data shapes — use these
contracts as the single source of truth.

Schemas defined here:
    PortfolioRecord     — one row of a reinsurance portfolio
    EventRecord         — one simulated catastrophe event
    HazardResult        — hazard intensity at a single exposure
    VulnerabilityResult — damage ratio for an exposure-event pair
    LossResult          — monetary loss for an exposure-event pair
    AnnualLossResult    — aggregate loss for one simulation year
    PolicyTailResult    — tail-risk allocation for a single policy
    PricingResult       — technical pricing output for a single policy
    RunContext          — reproducibility metadata for a model run
    AgentResult         — standardised result envelope for any agent
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

class PortfolioRecord(BaseModel):
    """A single exposure record in a reinsurance portfolio."""

    policy_id: str = Field(..., min_length=1, description="Unique policy identifier")
    latitude: float = Field(..., ge=-90, le=90, description="WGS-84 latitude")
    longitude: float = Field(..., ge=-180, le=180, description="WGS-84 longitude")
    insured_value: float = Field(..., gt=0, description="Total insured value (positive)")
    property_type: str = Field(..., min_length=1, description="Property classification")
    construction_class: Optional[str] = Field(default=None, description="Construction class")
    region: Optional[str] = Field(default=None, description="Geographic region label")


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------

class EventRecord(BaseModel):
    """A single simulated catastrophe event."""

    event_id: str = Field(..., min_length=1, description="Unique event identifier")
    event_type: Optional[str] = Field(default=None, description="Event category (e.g. fluvial)")
    scenario_tag: Optional[str] = Field(default=None, description="Scenario label")
    annual_frequency: float = Field(..., ge=0, description="Expected annual frequency")
    severity: Optional[float] = Field(default=None, description="Event severity metric")
    footprint_ref: Optional[str] = Field(default=None, description="Reference to hazard footprint")

    @field_validator("severity")
    @classmethod
    def severity_non_negative(cls, v: Optional[float]) -> Optional[float]:
        """Severity, when provided, must not be negative."""
        if v is not None and v < 0:
            raise ValueError("severity must be >= 0 when provided")
        return v


# ---------------------------------------------------------------------------
# Hazard
# ---------------------------------------------------------------------------

class HazardResult(BaseModel):
    """Hazard intensity at a specific exposure location for one event."""

    event_id: str = Field(..., min_length=1, description="Event identifier")
    policy_id: str = Field(..., min_length=1, description="Exposed policy identifier")
    depth_m: float = Field(..., ge=0, description="Flood depth in metres")
    flood_type: Optional[str] = Field(default=None, description="Flood mechanism type")


# ---------------------------------------------------------------------------
# Vulnerability
# ---------------------------------------------------------------------------

class VulnerabilityResult(BaseModel):
    """Damage ratio for an exposure hit by a specific event."""

    event_id: str = Field(..., min_length=1, description="Event identifier")
    policy_id: str = Field(..., min_length=1, description="Exposed policy identifier")
    damage_ratio: float = Field(
        ..., ge=0, le=1, description="Mean damage ratio [0, 1]"
    )


# ---------------------------------------------------------------------------
# Loss
# ---------------------------------------------------------------------------

class LossResult(BaseModel):
    """Ground-up loss for one exposure-event pair."""

    event_id: str = Field(..., min_length=1, description="Event identifier")
    policy_id: str = Field(..., min_length=1, description="Exposed policy identifier")
    insured_value: float = Field(..., gt=0, description="Total insured value")
    loss: float = Field(..., ge=0, description="Ground-up loss amount")


# ---------------------------------------------------------------------------
# Annual / Year-Loss
# ---------------------------------------------------------------------------

class AnnualLossResult(BaseModel):
    """Aggregate loss for one simulation year."""

    simulation_year: int = Field(..., ge=1, description="Simulation year number (≥ 1)")
    annual_loss: float = Field(..., ge=0, description="Total loss for the year")
    max_event_loss: float = Field(..., ge=0, description="Largest single-event loss")
    event_ids: list[str] = Field(default_factory=list, description="Events in this year")


# ---------------------------------------------------------------------------
# Tail
# ---------------------------------------------------------------------------

class PolicyTailResult(BaseModel):
    """Tail-risk contribution for a single policy."""

    policy_id: str = Field(..., min_length=1, description="Policy identifier")
    aal: float = Field(..., ge=0, description="Average annual loss")
    tail_contribution: float = Field(..., ge=0, description="Contribution to portfolio tail")


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------

class PricingResult(BaseModel):
    """Technical pricing output for a single policy."""

    policy_id: str = Field(..., min_length=1, description="Policy identifier")
    expected_loss: float = Field(..., ge=0, description="Expected loss")
    tail_charge: float = Field(..., ge=0, description="Tail risk charge")
    expense: float = Field(..., ge=0, description="Expense loading")
    technical_premium: float = Field(..., ge=0, description="Technical premium")


# ---------------------------------------------------------------------------
# Run Context
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def _new_run_id() -> str:
    """Generate a unique run identifier."""
    return str(uuid.uuid4())


class RunContext(BaseModel):
    """Reproducibility metadata attached to every model run."""

    run_id: str = Field(default_factory=_new_run_id, description="Unique run identifier")
    model_version: str = Field(..., description="Model version string")
    data_version: Optional[str] = Field(default=None, description="Data version tag")
    random_seed: int = Field(..., description="Random seed for reproducibility")
    simulation_years: int = Field(..., ge=1, description="Number of simulation years")
    scenario: Optional[str] = Field(default=None, description="Scenario label")
    created_at: datetime = Field(
        default_factory=_utcnow,
        description="Timezone-aware creation timestamp (UTC)",
    )


# ---------------------------------------------------------------------------
# Agent Result
# ---------------------------------------------------------------------------

# Allowed agent statuses — strict Literal union
AgentStatus = Literal[
    "PENDING",
    "RUNNING",
    "SUCCESS",
    "WARNING",
    "FAILED",
    "REVIEW_REQUIRED",
]


class AgentResult(BaseModel):
    """Standardised result envelope returned by any FLOODTAIL agent."""

    agent_name: str = Field(..., min_length=1, description="Name of the agent")
    status: AgentStatus = Field(..., description="Current status")
    run_id: Optional[str] = Field(default=None, description="Associated run identifier")
    message: Optional[str] = Field(default=None, description="Human-readable message")
    warnings: list[str] = Field(default_factory=list, description="Warning messages")
    data: Optional[Any] = Field(default=None, description="Arbitrary result payload")
