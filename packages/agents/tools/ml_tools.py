"""LangChain tools wrapping ML hazard / vulnerability inference."""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from packages.cat_core.assumptions import AssumptionsProfile
from packages.ml.registry import ModelRegistry


def run_hazard_infer(
    frame: pd.DataFrame,
    profile: AssumptionsProfile,
    registry: ModelRegistry,
    *,
    version: Optional[str] = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    from packages.ml.hazard.infer import predict_hazard

    return predict_hazard(frame, profile, registry, version=version)


def run_vuln_infer(
    frame: pd.DataFrame,
    profile: AssumptionsProfile,
    registry: ModelRegistry,
    *,
    version: Optional[str] = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    from packages.ml.vulnerability.infer import predict_vulnerability_for_tiers

    return predict_vulnerability_for_tiers(frame, profile, registry, version=version)


try:
    from langchain_core.tools import tool

    @tool
    def describe_ml_tools() -> str:
        """List available ML inference tools (hazard + vulnerability)."""
        return "run_hazard_infer, run_vuln_infer — require pinned registry artifacts"

except ImportError:  # pragma: no cover
    pass
