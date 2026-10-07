"""Shared CAT / run / insight types used across API, ML, and agents."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StageStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    OK = "OK"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    WARN = "WARN"


class Recommendation(str, Enum):
    ACCEPT = "ACCEPT"
    REVIEW = "REVIEW"
    ESCALATE = "ESCALATE"


class DataLabels(BaseModel):
    """Honesty labels attached to every metrics / insight payload."""

    synthetic_exposure: bool = True
    proxy_hazard: bool = True
    assumed_rp: bool = True
    d_max_m: float = 4.0
    location_flexible: bool = True
    notes: list[str] = Field(default_factory=list)


class IngestStats(BaseModel):
    """Underwriter-facing book summary from ingest."""

    n_insured_houses: int = 0
    total_tiv_kes: float = 0.0
    location_label: str = "unknown"
    bbox: Optional[tuple[float, float, float, float]] = None  # min_lat, min_lon, max_lat, max_lon
    housing_class_counts: dict[str, int] = Field(default_factory=dict)
    synthetic: bool = True
    source: str = ""


class Portfolio(BaseModel):
    """Stored portfolio metadata (rows live in store / frame separately)."""

    id: str
    tenant_id: str = "default"
    created_at: datetime = Field(default_factory=utc_now)
    name: str = "untitled"
    location_label: str = "unknown"
    source: str = ""
    synthetic: bool = True
    n_rows: int = 0
    ingest_stats: IngestStats = Field(default_factory=IngestStats)
    assumptions_version: str = "nairobi-pluvial-v1"
    data_labels: DataLabels = Field(default_factory=DataLabels)
    extra: dict[str, Any] = Field(default_factory=dict)


class RunConfig(BaseModel):
    """Parameters for a pipeline run."""

    portfolio_id: str
    hazard_model_version: Optional[str] = None
    vuln_model_version: Optional[str] = None
    use_ml: bool = False
    enable_freetext: bool = False
    freetext: Optional[str] = None
    require_human_gate_1: bool = False
    assumptions_version: Optional[str] = None
    d_max_m: Optional[float] = None
    tenant_id: str = "default"
    actor: str = "anonymous"


class TierLoss(BaseModel):
    tier: str
    return_period: int
    aep: float
    loss_kes: float
    mean_damage_ratio: Optional[float] = None


class EPPoint(BaseModel):
    return_period: float
    aep: float
    loss_kes: float


class CapitalBand(BaseModel):
    """Set-aside guidance: avoid under- and over-budgeting."""

    floor_kes: float
    central_kes: float
    ceiling_kes: float
    currency: str = "KES"
    method: str = "discrete_ep_aal"
    floor_basis: str = "rp100"
    central_basis: str = "aal"
    ceiling_basis: str = "rp250_capped_tiv"
    notes: list[str] = Field(default_factory=list)


class MetricsPayload(BaseModel):
    """Grounded run metrics — sole source of money numbers for agents."""

    run_id: str
    portfolio_id: str
    assumptions_version: str
    data_labels: DataLabels
    n_insured_houses: int
    total_tiv_kes: float
    location_label: str
    tier_losses: list[TierLoss] = Field(default_factory=list)
    ep_curve: list[EPPoint] = Field(default_factory=list)
    aal_kes: float = 0.0
    capital_band: Optional[CapitalBand] = None
    hazard_model_version: Optional[str] = None
    vuln_model_version: Optional[str] = None
    baseline_delta: dict[str, Any] = Field(default_factory=dict)
    accumulation_summary: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class InsightPackage(BaseModel):
    """Underwriter actionable insight — numbers must come from tool allowlist."""

    run_id: str
    recommendation: Recommendation = Recommendation.REVIEW
    insured_houses: int
    total_tiv_kes: float
    location_label: str
    set_aside: CapitalBand
    why: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    narrative: str = ""
    numbers_source: Literal["tool_allowlist", "template"] = "template"
    assumptions_version: str
    data_labels: DataLabels
    allowlist: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    """Structured result for a pipeline stage."""

    stage: str
    status: StageStatus
    message: str = ""
    warnings: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    critical: bool = False


class RunRecord(BaseModel):
    """Persisted run state."""

    id: str
    portfolio_id: str
    tenant_id: str = "default"
    status: Literal[
        "PENDING",
        "RUNNING",
        "COMPLETED",
        "FAILED",
        "REVIEW_REQUIRED",
    ] = "PENDING"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    config: RunConfig
    stages: list[AgentResult] = Field(default_factory=list)
    metrics: Optional[MetricsPayload] = None
    insight: Optional[InsightPackage] = None
    error: Optional[str] = None
