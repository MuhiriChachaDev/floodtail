"""Grounded CAT core: exposure, depth, financial, EP, capital, accumulation."""

from packages.cat_core.assumptions import AssumptionsProfile, CapitalPolicy
from packages.cat_core.engine import EngineResult, run_cat, run_prior_only
from packages.cat_core.types import (
    AgentResult,
    CapitalBand,
    DataLabels,
    EPPoint,
    IngestStats,
    InsightPackage,
    MetricsPayload,
    Portfolio,
    Recommendation,
    RunConfig,
    RunRecord,
    StageStatus,
    TierLoss,
)

__all__ = [
    "AgentResult",
    "AssumptionsProfile",
    "CapitalBand",
    "CapitalPolicy",
    "DataLabels",
    "EngineResult",
    "EPPoint",
    "IngestStats",
    "InsightPackage",
    "MetricsPayload",
    "Portfolio",
    "Recommendation",
    "RunConfig",
    "RunRecord",
    "StageStatus",
    "TierLoss",
    "run_cat",
    "run_prior_only",
]
